from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MessageRole = Literal["user", "assistant", "system"]


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    created_at: datetime


class ChatMessageCreate(BaseModel):
    role: MessageRole
    content: str = Field(min_length=1)


class Conversation(BaseModel):
    id: str = Field(description="Teléfono del usuario; identifica la conversación.")
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SendMessageRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: ChatMessageCreate
