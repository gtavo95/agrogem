from typing import Protocol

from domain.session.schema import Session


class SessionRepository(Protocol):
    """Port: contract any session persistence adapter must satisfy."""

    async def create(self, session: Session) -> Session: ...

    async def get(self, session_id: str) -> Session | None: ...

    async def merge_state(
        self, session_id: str, state_patch: dict
    ) -> Session | None: ...

    async def delete(self, session_id: str) -> bool: ...
