import uuid
from datetime import datetime, timezone

from domain.session.repository import SessionRepository
from domain.session.schema import Session, SessionCreate


async def start_chat_session(
    repo: SessionRepository, data: SessionCreate
) -> Session:
    now = datetime.now(timezone.utc)
    session = Session(
        id=str(uuid.uuid4()),
        user_id=data.user_id,
        state=data.state,
        created_at=now,
        updated_at=now,
    )
    return await repo.create(session)


async def fetch_session(
    repo: SessionRepository, session_id: str
) -> Session | None:
    return await repo.get(session_id)


async def update_session_state(
    repo: SessionRepository, session_id: str, state_patch: dict
) -> Session | None:
    return await repo.merge_state(session_id, state_patch)


async def end_session(repo: SessionRepository, session_id: str) -> bool:
    return await repo.delete(session_id)
