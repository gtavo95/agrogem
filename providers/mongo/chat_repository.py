from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument

from domain.chat.schema import ChatMessage, Conversation


class MongoChatRepository:
    """MongoDB adapter for the ChatRepository port."""

    def __init__(self, mongo: AsyncIOMotorClient):
        self._conversations = mongo["agrogem"]["conversations"]

    async def add_message(
        self,
        user_phone: str,
        message: ChatMessage,
    ) -> Conversation:
        now = datetime.now(timezone.utc)
        doc = await self._conversations.find_one_and_update(
            {"_id": user_phone},
            {
                "$setOnInsert": {
                    "_id": user_phone,
                    "created_at": now,
                },
                "$push": {"messages": message.model_dump(mode="json")},
                "$set": {"updated_at": now},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return _to_conversation(doc)

    async def list_conversations(
        self, user_phone: str | None = None
    ) -> list[Conversation]:
        query = {"_id": user_phone} if user_phone else {}
        cursor = self._conversations.find(query).sort("updated_at", -1)
        return [_to_conversation(doc) async for doc in cursor]


def _to_conversation(doc: dict) -> Conversation:
    return Conversation(
        id=str(doc["_id"]),
        messages=doc.get("messages", []),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )
