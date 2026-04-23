from fastapi import APIRouter, Depends, HTTPException, status

from domain.session.repository import SessionRepository
from domain.session.schema import Session, SessionCreate, SessionStatePatch
from domain.session.service import (
    end_session,
    fetch_session,
    start_chat_session,
    update_session_state,
)
from providers.redis.dependencies import get_session_repository

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=Session,
    status_code=status.HTTP_201_CREATED,
)
async def open_chat_session(
    data: SessionCreate,
    repo: SessionRepository = Depends(get_session_repository),
):
    "Crea una nueva sesión de chat en Redis (con TTL) y devuelve el id que servirá como key para los demás endpoints."
    return await start_chat_session(repo, data)


@router.get("/{session_id}", response_model=Session)
async def get_chat_session(
    session_id: str,
    repo: SessionRepository = Depends(get_session_repository),
):
    "Obtiene una sesión activa por su id; responde 404 si expiró o no existe."
    session = await fetch_session(repo, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session


@router.patch("/{session_id}/state", response_model=Session)
async def patch_chat_session_state(
    session_id: str,
    data: SessionStatePatch,
    repo: SessionRepository = Depends(get_session_repository),
):
    "Fusiona claves en el estado de la sesión (shallow merge) y refresca su TTL."
    session = await update_session_state(repo, session_id, data.state)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_chat_session(
    session_id: str,
    repo: SessionRepository = Depends(get_session_repository),
):
    "Cierra y elimina la sesión de Redis."
    await end_session(repo, session_id)
