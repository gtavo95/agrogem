from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Any


def create_mongo_client(uri: str) -> AsyncIOMotorClient:
    """Creates a new MongoDB connection."""
    client = AsyncIOMotorClient(uri)
    # Potentially add ping logic here to verify connection immediately
    return client


def close_mongo(client: AsyncIOMotorClient):
    """Closes the MongoDB connection."""
    client.close()


def get_mongo(request: Request):
    """Dependency to retrieve the MongoDB client from app state."""
    return request.app.state.mongo


def mongo_to_json(doc: dict[str, Any]) -> dict[str, Any]:
    # convierte ObjectId (y cualquier nested) a tipos JSON
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
