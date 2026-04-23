from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    user_id: str = Field(min_length=1, description="User phone (también identifica la conversación).")
    state: dict = Field(default_factory=dict)


class Session(BaseModel):
    id: str
    user_id: str
    state: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SessionStatePatch(BaseModel):
    state: dict = Field(description="Pares clave/valor a fusionar en el estado actual de la sesión.")
