from typing import Protocol

from domain.user.schema import User


class UserRepository(Protocol):
    """Port: contract any user persistence adapter must satisfy."""

    async def find_by_phone(self, phone: str) -> User | None: ...

    async def insert(self, user: User) -> User: ...
