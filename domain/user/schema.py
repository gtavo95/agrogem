from datetime import datetime

from pydantic import BaseModel, Field


PHONE_PATTERN = r"^\+?[0-9]{7,15}$"


class UserRegister(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN, examples=["+529991234567"])
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN, examples=["+529991234567"])
    password: str = Field(min_length=8, max_length=128)


class User(BaseModel):
    id: str
    phone: str
    password_hash: bytes
    created_at: datetime


class UserPublic(BaseModel):
    id: str
    phone: str
    created_at: datetime


class LoginResponse(BaseModel):
    session_id: str
    user: UserPublic
