import uuid
from datetime import datetime, timezone

import bcrypt

from domain.user.repository import UserRepository
from domain.user.schema import User, UserLogin, UserPublic, UserRegister


class PhoneAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    pass


def _hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


# Pre-computed hash used when the phone is not registered, so bcrypt.checkpw
# still runs and login latency does not leak whether a user exists.
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"dummy-password-for-constant-time-compare", bcrypt.gensalt()
)


async def register_user(repo: UserRepository, data: UserRegister) -> UserPublic:
    if await repo.find_by_phone(data.phone) is not None:
        raise PhoneAlreadyRegistered

    user = User(
        id=str(uuid.uuid4()),
        phone=data.phone,
        password_hash=_hash_password(data.password),
        created_at=datetime.now(timezone.utc),
    )
    await repo.insert(user)
    return UserPublic(id=user.id, phone=user.phone, created_at=user.created_at)


async def authenticate_user(repo: UserRepository, data: UserLogin) -> User:
    user = await repo.find_by_phone(data.phone)
    expected_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    is_valid = bcrypt.checkpw(data.password.encode("utf-8"), expected_hash)
    if user is None or not is_valid:
        raise InvalidCredentials
    return user
