from fastapi import APIRouter, Depends, HTTPException, status

from domain.chat.repository import ChatRepository
from domain.chat.schema import Conversation, SendMessageRequest
from domain.chat.service import (
    append_message_to_conversation,
    list_user_conversations,
)
from domain.session.repository import SessionRepository
from domain.session.service import fetch_session
from providers.mongo.dependencies import get_chat_repository
from providers.redis.dependencies import get_session_repository

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/messages",
    response_model=Conversation,
    status_code=status.HTTP_201_CREATED,
)
async def send_message_to_conversation(
    data: SendMessageRequest,
    chat_repo: ChatRepository = Depends(get_chat_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    "Envía un mensaje en el contexto de una sesión activa; el teléfono del usuario (resuelto desde la sesión) identifica la conversación en MongoDB."
    session = await fetch_session(session_repo, data.session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired",
        )
    return await append_message_to_conversation(
        chat_repo, session.user_id, data.message
    )


@router.get("/conversations", response_model=list[Conversation])
async def list_conversations_for_user(
    user_phone: str | None = None,
    repo: ChatRepository = Depends(get_chat_repository),
):
    "Lista las conversaciones almacenadas, opcionalmente filtradas por teléfono del usuario."
    return await list_user_conversations(repo, user_phone)
