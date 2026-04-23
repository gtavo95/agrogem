from fastapi import Depends

from domain.session.repository import SessionRepository
from providers.redis.config import get_redis
from providers.redis.session_repository import RedisSessionRepository


def get_session_repository(redis=Depends(get_redis)) -> SessionRepository:
    return RedisSessionRepository(redis)
