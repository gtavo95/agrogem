"""Integration tests against real Redis and MongoDB via testcontainers.

Run with:
    pytest tests/test_chat_integration.py -v -m integration

Requires Docker to be running. If Docker is not available or the
`testcontainers` package is not installed, the entire module is skipped.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import AsyncIterator

import pytest

# Skip the whole module if testcontainers isn't installed (CI without Docker).
testcontainers_mongodb = pytest.importorskip("testcontainers.mongodb")
testcontainers_redis = pytest.importorskip("testcontainers.redis")

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

from domain.chat.router import router as chat_router
from domain.session.router import router as session_router
from providers.mongo.chat_repository import MongoChatRepository
from providers.mongo.dependencies import get_chat_repository
from providers.redis.dependencies import get_session_repository
from providers.redis.session_repository import RedisSessionRepository
from tests.conftest import make_fake_conversation, make_fake_users

MongoDbContainer = testcontainers_mongodb.MongoDbContainer
RedisContainer = testcontainers_redis.RedisContainer

pytestmark = pytest.mark.integration


# -----------------------------------------------------------------------------
# Container fixtures (session-scoped: one container for the whole test run)
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mongo_container():
    try:
        with MongoDbContainer("mongo:7") as container:
            yield container
    except Exception as e:
        pytest.skip(f"Docker/Mongo unavailable: {e}")


@pytest.fixture(scope="session")
def redis_container():
    try:
        with RedisContainer("redis:7-alpine") as container:
            yield container
    except Exception as e:
        pytest.skip(f"Docker/Redis unavailable: {e}")


# -----------------------------------------------------------------------------
# Per-test client fixtures (clean state via drop / flushdb)
# -----------------------------------------------------------------------------


@pytest.fixture
async def mongo_client(mongo_container) -> AsyncIterator[AsyncIOMotorClient]:
    client = AsyncIOMotorClient(mongo_container.get_connection_url())
    try:
        yield client
    finally:
        await client.drop_database("agrogem")
        client.close()


@pytest.fixture
async def redis_client(redis_container) -> AsyncIterator[aioredis.Redis]:
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    client = aioredis.from_url(f"redis://{host}:{port}", decode_responses=True)
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


def _build_app(
    redis_client: aioredis.Redis,
    mongo_client: AsyncIOMotorClient,
    session_ttl_seconds: int = 60 * 60 * 24,
) -> FastAPI:
    app = FastAPI()
    app.include_router(session_router)
    app.include_router(chat_router)
    app.dependency_overrides[get_session_repository] = lambda: RedisSessionRepository(
        redis_client, ttl_seconds=session_ttl_seconds
    )
    app.dependency_overrides[get_chat_repository] = lambda: MongoChatRepository(
        mongo_client
    )
    return app


def _open_session(client: TestClient, user_phone: str, state: dict | None = None) -> str:
    resp = client.post(
        "/sessions", json={"user_id": user_phone, "state": state or {}}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# -----------------------------------------------------------------------------
# A. Real Redis — TTL semantics + lifecycle
# -----------------------------------------------------------------------------


async def test_real_redis_session_get_returns_what_was_created(
    redis_client, mongo_client
):
    app = _build_app(redis_client, mongo_client)
    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567", state={"crop": "coffee"})
        resp = client.get(f"/sessions/{sid}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == sid
    assert body["user_id"] == "+529991234567"
    assert body["state"] == {"crop": "coffee"}


async def test_real_redis_sets_ttl_around_24h(redis_client, mongo_client):
    app = _build_app(redis_client, mongo_client)
    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567")

    # Verify the TTL set by RedisSessionRepository is approximately 24h.
    ttl = await redis_client.ttl(f"chat:session:{sid}")
    assert 60 * 60 * 23 <= ttl <= 60 * 60 * 24


async def test_real_redis_key_expires_when_ttl_elapses(redis_client, mongo_client):
    # Use 1-second TTL so we can actually wait for expiration.
    app = _build_app(redis_client, mongo_client, session_ttl_seconds=1)
    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567")
        # Sanity: session is reachable immediately
        assert client.get(f"/sessions/{sid}").status_code == 200

        await asyncio.sleep(1.5)

        resp = client.get(f"/sessions/{sid}")

    assert resp.status_code == 404


async def test_real_redis_patch_state_refreshes_ttl(redis_client, mongo_client):
    app = _build_app(redis_client, mongo_client, session_ttl_seconds=10)
    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567")
        ttl_before = await redis_client.ttl(f"chat:session:{sid}")

        await asyncio.sleep(2)
        ttl_aged = await redis_client.ttl(f"chat:session:{sid}")
        assert ttl_aged < ttl_before  # TTL has decreased

        client.patch(f"/sessions/{sid}/state", json={"state": {"crop": "coffee"}})
        ttl_refreshed = await redis_client.ttl(f"chat:session:{sid}")

    assert ttl_refreshed > ttl_aged


async def test_real_redis_delete_removes_key(redis_client, mongo_client):
    app = _build_app(redis_client, mongo_client)
    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567")
        assert await redis_client.exists(f"chat:session:{sid}") == 1

        client.delete(f"/sessions/{sid}")

    assert await redis_client.exists(f"chat:session:{sid}") == 0


# -----------------------------------------------------------------------------
# B. Real Mongo — upsert / $push / $setOnInsert / $set
# -----------------------------------------------------------------------------


async def test_real_mongo_first_message_creates_document(redis_client, mongo_client):
    app = _build_app(redis_client, mongo_client)
    user_phone = f"+5299912{uuid.uuid4().int % 100000:05d}"

    with TestClient(app) as client:
        sid = _open_session(client, user_phone)
        resp = client.post(
            "/chat/messages",
            json={
                "session_id": sid,
                "message": {"role": "user", "content": "Hola"},
            },
        )

    assert resp.status_code == 201
    raw = await mongo_client["agrogem"]["conversations"].find_one({"_id": user_phone})
    assert raw is not None
    assert raw["_id"] == user_phone
    assert len(raw["messages"]) == 1
    assert raw["messages"][0]["role"] == "user"
    assert raw["messages"][0]["content"] == "Hola"
    assert raw["created_at"] == raw["updated_at"]


async def test_real_mongo_appends_messages_in_order_and_preserves_created_at(
    redis_client, mongo_client
):
    app = _build_app(redis_client, mongo_client)
    user_phone = f"+5299912{uuid.uuid4().int % 100000:05d}"
    fake_msgs = make_fake_conversation(n_messages=10, seed=42)

    with TestClient(app) as client:
        sid = _open_session(client, user_phone)
        first_created_at = None
        for m in fake_msgs:
            resp = client.post(
                "/chat/messages",
                json={
                    "session_id": sid,
                    "message": {"role": m.role, "content": m.content},
                },
            )
            assert resp.status_code == 201
            body = resp.json()
            if first_created_at is None:
                first_created_at = body["created_at"]
            # $setOnInsert: created_at frozen on first message
            assert body["created_at"] == first_created_at

    raw = await mongo_client["agrogem"]["conversations"].find_one({"_id": user_phone})
    assert raw is not None
    assert len(raw["messages"]) == 10
    for stored, expected in zip(raw["messages"], fake_msgs):
        assert stored["role"] == expected.role
        assert stored["content"] == expected.content
    assert raw["updated_at"] >= raw["created_at"]


async def test_real_mongo_lists_multiple_users_ordered_by_updated_at_desc(
    redis_client, mongo_client
):
    app = _build_app(redis_client, mongo_client)
    users = make_fake_users(n=3, seed=23)

    with TestClient(app) as client:
        for phone in users:
            sid = _open_session(client, phone)
            resp = client.post(
                "/chat/messages",
                json={
                    "session_id": sid,
                    "message": {"role": "user", "content": "msg"},
                },
            )
            assert resp.status_code == 201

        resp = client.get("/chat/conversations")

    body = resp.json()
    returned_ids = [c["id"] for c in body if c["id"] in users]
    assert returned_ids == list(reversed(users))


async def test_real_mongo_filter_by_user_phone_returns_only_that_conversation(
    redis_client, mongo_client
):
    app = _build_app(redis_client, mongo_client)
    users = make_fake_users(n=3, seed=11)
    target = users[1]

    with TestClient(app) as client:
        for phone in users:
            sid = _open_session(client, phone)
            client.post(
                "/chat/messages",
                json={
                    "session_id": sid,
                    "message": {"role": "user", "content": f"hola {phone}"},
                },
            )

        resp = client.get("/chat/conversations", params={"user_phone": target})

    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == target


# -----------------------------------------------------------------------------
# C. Cross-store: message append fails cleanly when session is missing
# -----------------------------------------------------------------------------


async def test_unknown_session_returns_404_without_writing_to_mongo(
    redis_client, mongo_client
):
    app = _build_app(redis_client, mongo_client)
    user_phone = f"+5299912{uuid.uuid4().int % 100000:05d}"

    with TestClient(app) as client:
        resp = client.post(
            "/chat/messages",
            json={
                "session_id": str(uuid.uuid4()),
                "message": {"role": "user", "content": "Hola"},
            },
        )

    assert resp.status_code == 404
    raw = await mongo_client["agrogem"]["conversations"].find_one({"_id": user_phone})
    assert raw is None
