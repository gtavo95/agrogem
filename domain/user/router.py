from fastapi import APIRouter, Depends, HTTPException, status

from domain.session.repository import SessionRepository
from domain.session.schema import SessionCreate
from domain.session.service import start_chat_session
from domain.user.repository import UserRepository
from domain.user.schema import (
    LoginResponse,
    UserLogin,
    UserPublic,
    UserRegister,
)
from domain.user.service import (
    InvalidCredentials,
    PhoneAlreadyRegistered,
    authenticate_user,
    register_user,
)
from providers.mongo.dependencies import get_user_repository
from providers.redis.dependencies import get_session_repository

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
async def sign_up_new_user(
    data: UserRegister,
    repo: UserRepository = Depends(get_user_repository),
):
    "Registra un nuevo usuario en MongoDB; responde 409 si el teléfono ya existe."
    try:
        return await register_user(repo, data)
    except PhoneAlreadyRegistered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone already registered",
        )


@router.post("/login", response_model=LoginResponse)
async def log_in_user(
    data: UserLogin,
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    "Verifica credenciales y abre una sesión en Redis; devuelve el session_id para usar en /chat."
    try:
        user = await authenticate_user(user_repo, data)
    except InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or password",
        )
    session = await start_chat_session(session_repo, SessionCreate(user_id=user.phone))
    return LoginResponse(
        session_id=session.id,
        user=UserPublic(id=user.id, phone=user.phone, created_at=user.created_at),
    )
