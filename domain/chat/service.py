from datetime import datetime, timezone

from domain.chat.repository import ChatRepository
from domain.chat.schema import (
    ChatMessage,
    ChatMessageCreate,
    Conversation,
)


async def append_message_to_conversation(
    repo: ChatRepository,
    user_phone: str,
    data: ChatMessageCreate,
) -> Conversation:
    message = ChatMessage(
        role=data.role,
        content=data.content,
        created_at=datetime.now(timezone.utc),
    )
    return await repo.add_message(user_phone, message)


async def list_user_conversations(
    repo: ChatRepository, user_phone: str | None = None
) -> list[Conversation]:
    return await repo.list_conversations(user_phone)
