from typing import Any

from bson import ObjectId
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient


def create_mongo_client(uri: str) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(uri)


def close_mongo(client: AsyncIOMotorClient) -> None:
    client.close()


def get_mongo(request: Request) -> AsyncIOMotorClient:
    """Dependency to retrieve the MongoDB client from app state."""
    return request.app.state.mongo


def mongo_to_json(doc: dict[str, Any]) -> dict[str, Any]:
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, dict):
            doc[k] = mongo_to_json(v)
        elif isinstance(v, list):
            doc[k] = [
                (
                    str(x)
                    if isinstance(x, ObjectId)
                    else mongo_to_json(x)
                    if isinstance(x, dict)
                    else x
                )
                for x in v
            ]
    return doc
