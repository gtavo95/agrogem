from fastapi import Depends

from domain.chat.repository import ChatRepository
from domain.pest.repository import PestRepository
from domain.user.repository import UserRepository
from providers.mongo.chat_repository import MongoChatRepository
from providers.mongo.config import get_mongo
from providers.mongo.pest_repository import MongoPestRepository
from providers.mongo.user_repository import MongoUserRepository


def get_chat_repository(mongo=Depends(get_mongo)) -> ChatRepository:
    return MongoChatRepository(mongo)


def get_user_repository(mongo=Depends(get_mongo)) -> UserRepository:
    return MongoUserRepository(mongo)


def get_pest_repository(mongo=Depends(get_mongo)) -> PestRepository:
    return MongoPestRepository(mongo)
