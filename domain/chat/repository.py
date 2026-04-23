from typing import Protocol

from domain.chat.schema import ChatMessage, Conversation


class ChatRepository(Protocol):
    """Port: contract any chat persistence adapter must satisfy."""

    async def add_message(
        self,
        user_phone: str,
        message: ChatMessage,
    ) -> Conversation: ...

    async def list_conversations(
        self, user_phone: str | None = None
    ) -> list[Conversation]: ...
