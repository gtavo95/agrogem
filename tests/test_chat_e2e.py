from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domain.chat.router import router as chat_router
from domain.session.router import router as session_router
from providers.mongo.dependencies import get_chat_repository
from providers.redis.dependencies import get_session_repository
from tests.conftest import (
    FAKE_SESSION_TTL_SECONDS,
    FakeChatRepository,
    FakeSessionRepository,
    ManualClock,
    make_fake_conversation,
    make_fake_users,
)


def _build_app(
    session_repo: FakeSessionRepository,
    chat_repo: FakeChatRepository,
) -> FastAPI:
    app = FastAPI()
    app.include_router(session_router)
    app.include_router(chat_router)
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    app.dependency_overrides[get_chat_repository] = lambda: chat_repo
    return app


def _open_session(client: TestClient, user_phone: str, state: dict | None = None) -> str:
    payload = {"user_id": user_phone, "state": state or {}}
    resp = client.post("/sessions", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# -----------------------------------------------------------------------------
# A. Session lifecycle + TTL
# -----------------------------------------------------------------------------


def test_session_create_persists_to_store():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    with TestClient(app) as client:
        resp = client.post(
            "/sessions",
            json={"user_id": "+529991234567", "state": {"crop": "coffee"}},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["user_id"] == "+529991234567"
    assert body["state"] == {"crop": "coffee"}
    assert body["id"] in session_repo._store


def test_session_get_returns_active():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567", state={"region": "Antioquia"})
        resp = client.get(f"/sessions/{sid}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == sid
    assert body["user_id"] == "+529991234567"
    assert body["state"] == {"region": "Antioquia"}


def test_session_patch_state_merges_and_refreshes_ttl():
    clock = ManualClock(start=1000.0)
    session_repo = FakeSessionRepository(time_provider=clock)
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567", state={"region": "Antioquia"})
        ttl_after_create = session_repo.expires_at(sid)
        assert ttl_after_create is not None

        clock.tick(3600)  # 1h passes
        resp = client.patch(
            f"/sessions/{sid}/state", json={"state": {"crop": "coffee"}}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == {"region": "Antioquia", "crop": "coffee"}
    # TTL refreshed forward by exactly the elapsed time
    assert session_repo.expires_at(sid) == ttl_after_create + 3600


def test_session_delete_removes_from_store():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567")
        delete_resp = client.delete(f"/sessions/{sid}")
        get_resp = client.get(f"/sessions/{sid}")

    assert delete_resp.status_code == 204
    assert sid not in session_repo._store
    assert get_resp.status_code == 404


def test_session_get_after_ttl_expires_returns_404():
    clock = ManualClock(start=0.0)
    session_repo = FakeSessionRepository(time_provider=clock)
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567")
        clock.tick(FAKE_SESSION_TTL_SECONDS + 1)
        resp = client.get(f"/sessions/{sid}")

    assert resp.status_code == 404
    assert sid not in session_repo._store


# -----------------------------------------------------------------------------
# B. Conversation — append messages to Mongo
# -----------------------------------------------------------------------------


def test_send_first_message_creates_conversation_doc():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    user_phone = "+529991234567"
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
    body = resp.json()
    assert body["id"] == user_phone
    assert len(body["messages"]) == 1
    msg = body["messages"][0]
    assert msg["role"] == "user"
    assert msg["content"] == "Hola"
    assert msg["created_at"].endswith("+00:00") or msg["created_at"].endswith("Z")

    doc = chat_repo._store[user_phone]
    assert doc["created_at"] == doc["updated_at"]
    assert len(doc["messages"]) == 1


def test_send_multiple_messages_appends_in_order():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    user_phone = "+529991234567"
    fake_msgs = make_fake_conversation(n_messages=10, seed=42)

    with TestClient(app) as client:
        sid = _open_session(client, user_phone)
        first_created_at = None
        last_updated_at = None
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
            # created_at sticks ($setOnInsert), updated_at advances ($set)
            assert body["created_at"] == first_created_at
            if last_updated_at is not None:
                assert body["updated_at"] >= last_updated_at
            last_updated_at = body["updated_at"]

    doc = chat_repo._store[user_phone]
    assert len(doc["messages"]) == 10
    for stored, expected in zip(doc["messages"], fake_msgs):
        assert stored["role"] == expected.role
        assert stored["content"] == expected.content


def test_send_message_with_invalid_role_returns_422():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567")
        resp = client.post(
            "/chat/messages",
            json={
                "session_id": sid,
                "message": {"role": "bot", "content": "Hola"},
            },
        )

    assert resp.status_code == 422


def test_send_message_with_empty_content_returns_422():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    with TestClient(app) as client:
        sid = _open_session(client, "+529991234567")
        resp = client.post(
            "/chat/messages",
            json={
                "session_id": sid,
                "message": {"role": "user", "content": ""},
            },
        )

    assert resp.status_code == 422


def test_send_message_with_unknown_session_returns_404():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    with TestClient(app) as client:
        resp = client.post(
            "/chat/messages",
            json={
                "session_id": "00000000-0000-0000-0000-000000000000",
                "message": {"role": "user", "content": "Hola"},
            },
        )

    assert resp.status_code == 404
    assert "Session not found" in resp.json()["detail"]


# -----------------------------------------------------------------------------
# C. Multiple users — listing and ordering
# -----------------------------------------------------------------------------


def test_multiple_users_have_isolated_conversations():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    users = make_fake_users(n=5, seed=7)

    with TestClient(app) as client:
        for idx, phone in enumerate(users):
            sid = _open_session(client, phone)
            for m in make_fake_conversation(n_messages=4, seed=idx):
                resp = client.post(
                    "/chat/messages",
                    json={
                        "session_id": sid,
                        "message": {"role": m.role, "content": m.content},
                    },
                )
                assert resp.status_code == 201

    assert set(chat_repo._store.keys()) == set(users)
    for phone in users:
        assert len(chat_repo._store[phone]["messages"]) == 4


def test_list_conversations_filters_by_user_phone():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

    users = make_fake_users(n=3, seed=11)
    target = users[1]

    with TestClient(app) as client:
        for phone in users:
            sid = _open_session(client, phone)
            client.post(
                "/chat/messages",
                json={
                    "session_id": sid,
                    "message": {"role": "user", "content": f"hola desde {phone}"},
                },
            )

        resp = client.get("/chat/conversations", params={"user_phone": target})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == target


def test_list_conversations_without_filter_orders_by_updated_at_desc():
    session_repo = FakeSessionRepository()
    chat_repo = FakeChatRepository()
    app = _build_app(session_repo, chat_repo)

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

    assert resp.status_code == 200
    body = resp.json()
    returned_ids = [c["id"] for c in body]
    # Most recent insert appears first (reverse of insertion order)
    assert returned_ids == list(reversed(users))
    # And updated_at is monotonically non-increasing
    timestamps = [c["updated_at"] for c in body]
    assert timestamps == sorted(timestamps, reverse=True)
