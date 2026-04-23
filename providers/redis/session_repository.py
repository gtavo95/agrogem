from datetime import datetime, timezone

from redis.asyncio import Redis

from domain.session.schema import Session


SESSION_KEY_PREFIX = "chat:session:"
SESSION_TTL_SECONDS = 60 * 60 * 24


def _session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


class RedisSessionRepository:
    """Redis adapter for the SessionRepository port."""

    def __init__(self, redis: Redis, ttl_seconds: int = SESSION_TTL_SECONDS):
        self._redis = redis
        self._ttl = ttl_seconds

    async def create(self, session: Session) -> Session:
        await self._redis.set(
            _session_key(session.id),
            session.model_dump_json(),
            ex=self._ttl,
        )
        return session

    async def get(self, session_id: str) -> Session | None:
        raw = await self._redis.get(_session_key(session_id))
        if not raw:
            return None
        return Session.model_validate_json(raw)

    async def merge_state(
        self, session_id: str, state_patch: dict
    ) -> Session | None:
        session = await self.get(session_id)
        if session is None:
            return None
        session.state = {**session.state, **state_patch}
        session.updated_at = datetime.now(timezone.utc)
        await self._redis.set(
            _session_key(session.id),
            session.model_dump_json(),
            ex=self._ttl,
        )
        return session

    async def delete(self, session_id: str) -> bool:
        deleted = await self._redis.delete(_session_key(session_id))
        return deleted > 0
