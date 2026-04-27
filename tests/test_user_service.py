from __future__ import annotations

import time

import pytest

from domain.user.schema import UserLogin, UserRegister
from domain.user.service import (
    InvalidCredentials,
    PhoneAlreadyRegistered,
    authenticate_user,
    register_user,
)
from tests.conftest import FakeUserRepository


async def test_register_user_creates_and_hashes_password():
    repo = FakeUserRepository()
    data = UserRegister(phone="+529991234567", password="supersecret1")

    public = await register_user(repo, data)

    assert public.phone == "+529991234567"
    assert public.id
    assert public.created_at is not None
    stored = repo.users["+529991234567"]
    # Hash must not be the plaintext
    assert stored.password_hash != b"supersecret1"
    assert stored.password_hash.startswith(b"$2")  # bcrypt prefix


async def test_register_user_rejects_duplicate_phone():
    repo = FakeUserRepository()
    data = UserRegister(phone="+529991234567", password="supersecret1")
    await register_user(repo, data)

    with pytest.raises(PhoneAlreadyRegistered):
        await register_user(repo, data)


async def test_authenticate_user_happy_path():
    repo = FakeUserRepository()
    await register_user(repo, UserRegister(phone="+529991234567", password="supersecret1"))

    user = await authenticate_user(
        repo, UserLogin(phone="+529991234567", password="supersecret1")
    )

    assert user.phone == "+529991234567"


async def test_authenticate_user_rejects_wrong_password():
    repo = FakeUserRepository()
    await register_user(repo, UserRegister(phone="+529991234567", password="supersecret1"))

    with pytest.raises(InvalidCredentials):
        await authenticate_user(
            repo, UserLogin(phone="+529991234567", password="wrongpassword1")
        )


async def test_authenticate_user_rejects_unknown_phone():
    repo = FakeUserRepository()

    with pytest.raises(InvalidCredentials):
        await authenticate_user(
            repo, UserLogin(phone="+529990000000", password="supersecret1")
        )


async def test_authenticate_timing_does_not_leak_user_existence():
    """When the phone is not found, the code still runs bcrypt.checkpw against a
    dummy hash so the response time is comparable to a wrong-password attempt.
    This is a best-effort timing-leak guard."""
    repo = FakeUserRepository()
    await register_user(repo, UserRegister(phone="+529991234567", password="supersecret1"))

    # Wrong password for an existing user
    t0 = time.perf_counter()
    try:
        await authenticate_user(
            repo, UserLogin(phone="+529991234567", password="wrongpassword1")
        )
    except InvalidCredentials:
        pass
    existing_duration = time.perf_counter() - t0

    # Any password for a non-existing user
    t0 = time.perf_counter()
    try:
        await authenticate_user(
            repo, UserLogin(phone="+529990000000", password="anything12345")
        )
    except InvalidCredentials:
        pass
    missing_duration = time.perf_counter() - t0

    # Within 3x of each other — bcrypt dominates both paths.
    ratio = max(existing_duration, missing_duration) / max(
        min(existing_duration, missing_duration), 1e-6
    )
    assert ratio < 3.0, (
        f"Suspiciously divergent timing: existing={existing_duration:.3f}s "
        f"missing={missing_duration:.3f}s (ratio={ratio:.2f})"
    )
