from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Sequence

import pytest

from domain.chat.schema import ChatMessage, ChatMessageCreate, Conversation
from domain.elevation.schema import ElevationResponse
from domain.pest.schema import PestMatch
from domain.session.schema import Session
from domain.user.schema import User
from domain.weather.schema import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    WeatherResponse,
)


def make_weather(
    hourly_temps: Sequence[float | None] | None = None,
    hourly_rh: Sequence[int | None] | None = None,
    daily_precip: Sequence[float | None] | None = None,
    daily_tmax: Sequence[float | None] | None = None,
    daily_tmin: Sequence[float | None] | None = None,
    days: int = 7,
) -> WeatherResponse:
    hours = days * 24
    temps: list[float | None] = (
        list(hourly_temps) if hourly_temps is not None else [20.0] * hours
    )
    rh: list[int | None] = (
        list(hourly_rh) if hourly_rh is not None else [70] * hours
    )
    precip: list[float | None] = (
        list(daily_precip) if daily_precip is not None else [0.0] * days
    )
    tmax: list[float | None] = (
        list(daily_tmax) if daily_tmax is not None else [25.0] * days
    )
    tmin: list[float | None] = (
        list(daily_tmin) if daily_tmin is not None else [15.0] * days
    )
    daily_times = [f"2026-04-{i + 1:02d}" for i in range(days)]
    hourly_times = [f"2026-04-{(i // 24) + 1:02d}T{i % 24:02d}:00" for i in range(hours)]

    return WeatherResponse(
        latitude=0.0,
        longitude=0.0,
        timezone="UTC",
        current=CurrentWeather(
            time="2026-04-01T00:00",
            temperature_2m=20.0,
            relative_humidity_2m=70,
            precipitation=0.0,
            weather_code=0,
            wind_speed_10m=5.0,
        ),
        hourly=HourlyForecast(
            time=hourly_times,
            temperature_2m=temps,
            relative_humidity_2m=rh,
            precipitation_probability=[0] * hours,
        ),
        daily=DailyForecast(
            time=daily_times,
            temperature_2m_max=tmax,
            temperature_2m_min=tmin,
            precipitation_sum=precip,
            et0_fao_evapotranspiration=[4.0] * days,
            uv_index_max=[5.0] * days,
        ),
    )


@dataclass
class FakeWeatherProvider:
    response: WeatherResponse
    calls: int = 0

    async def get_forecast(self, lat: float, lon: float) -> WeatherResponse:
        self.calls += 1
        return self.response


@dataclass
class FakeWeatherCache:
    store: dict[tuple[float, float], WeatherResponse] = field(default_factory=dict)

    async def get(self, lat: float, lon: float) -> WeatherResponse | None:
        return self.store.get((lat, lon))

    async def set(self, lat: float, lon: float, weather: WeatherResponse) -> None:
        self.store[(lat, lon)] = weather


@dataclass
class FakeElevationProvider:
    elevation_m: float | None = 2800.0

    async def get(self, lat: float, lon: float) -> ElevationResponse | None:
        if self.elevation_m is None:
            return None
        return ElevationResponse(lat=lat, lon=lon, elevation_m=self.elevation_m)


@dataclass
class FakeElevationCache:
    store: dict[tuple[float, float], ElevationResponse] = field(default_factory=dict)

    async def get(self, lat: float, lon: float) -> ElevationResponse | None:
        return self.store.get((lat, lon))

    async def set(
        self, lat: float, lon: float, result: ElevationResponse
    ) -> None:
        self.store[(lat, lon)] = result


@dataclass
class FakeUserRepository:
    users: dict[str, User] = field(default_factory=dict)

    async def find_by_phone(self, phone: str) -> User | None:
        return self.users.get(phone)

    async def insert(self, user: User) -> User:
        self.users[user.phone] = user
        return user


@dataclass
class FakePestEmbedder:
    vector: list[float] = field(default_factory=lambda: [0.1, 0.2, 0.3])

    async def embed_image(self, image_bytes: bytes, mime_type: str) -> list[float]:
        return list(self.vector)


@dataclass
class FakePestStorage:
    data: dict[str, bytes] = field(default_factory=dict)
    upload_url: str = "https://fake.storage/upload"

    def generate_upload_url(self, object_path: str, content_type: str) -> str:
        return f"{self.upload_url}?path={object_path}"

    async def read_bytes(self, object_path: str) -> bytes:
        return self.data.get(object_path, b"\x00\x01\x02")


@dataclass
class FakePestRepository:
    matches: list[PestMatch] = field(default_factory=list)
    received_k: int | None = None

    async def search_similar(
        self, query_embedding: list[float], k: int
    ) -> list[PestMatch]:
        self.received_k = k
        return list(self.matches[:k])


@pytest.fixture
def weather_sunny() -> WeatherResponse:
    return make_weather()


@pytest.fixture
def fake_weather_cache() -> FakeWeatherCache:
    return FakeWeatherCache()


@pytest.fixture
def fake_elevation_cache() -> FakeElevationCache:
    return FakeElevationCache()


# Default TTL mirrors providers/redis/session_repository.py:9 (24h).
FAKE_SESSION_TTL_SECONDS = 60 * 60 * 24


class ManualClock:
    """Monotonic-style clock controllable from tests; advance with `tick()`."""

    def __init__(self, start: float = 0.0):
        self._now = start

    def __call__(self) -> float:
        return self._now

    def tick(self, seconds: float) -> None:
        self._now += seconds


@dataclass
class FakeSessionRepository:
    """In-memory port impl that mirrors RedisSessionRepository semantics:
    24h TTL, refresh on merge_state, return None on expired get."""

    ttl_seconds: int = FAKE_SESSION_TTL_SECONDS
    time_provider: Callable[[], float] = field(default_factory=ManualClock)
    _store: dict[str, tuple[Session, float]] = field(default_factory=dict)

    async def create(self, session: Session) -> Session:
        expires_at = self.time_provider() + self.ttl_seconds
        self._store[session.id] = (session, expires_at)
        return session

    async def get(self, session_id: str) -> Session | None:
        entry = self._store.get(session_id)
        if entry is None:
            return None
        session, expires_at = entry
        if self.time_provider() > expires_at:
            del self._store[session_id]
            return None
        return session

    async def merge_state(
        self, session_id: str, state_patch: dict
    ) -> Session | None:
        session = await self.get(session_id)
        if session is None:
            return None
        session.state = {**session.state, **state_patch}
        session.updated_at = datetime.now(timezone.utc)
        expires_at = self.time_provider() + self.ttl_seconds
        self._store[session.id] = (session, expires_at)
        return session

    async def delete(self, session_id: str) -> bool:
        return self._store.pop(session_id, None) is not None

    def expires_at(self, session_id: str) -> float | None:
        entry = self._store.get(session_id)
        return entry[1] if entry else None


@dataclass
class FakeChatRepository:
    """In-memory port impl that mirrors MongoChatRepository semantics:
    upsert by user_phone, $push messages in order, $setOnInsert created_at,
    $set updated_at, list ordered by updated_at desc."""

    _store: dict[str, dict] = field(default_factory=dict)

    async def add_message(
        self, user_phone: str, message: ChatMessage
    ) -> Conversation:
        now = datetime.now(timezone.utc)
        doc = self._store.get(user_phone)
        if doc is None:
            doc = {
                "_id": user_phone,
                "created_at": now,
                "messages": [],
                "updated_at": now,
            }
            self._store[user_phone] = doc
        doc["messages"].append(message.model_dump(mode="json"))
        doc["updated_at"] = now
        return Conversation(
            id=str(doc["_id"]),
            messages=doc["messages"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )

    async def list_conversations(
        self, user_phone: str | None = None
    ) -> list[Conversation]:
        if user_phone is not None:
            doc = self._store.get(user_phone)
            docs = [doc] if doc else []
        else:
            docs = list(self._store.values())
        docs.sort(key=lambda d: d["updated_at"], reverse=True)
        return [
            Conversation(
                id=str(d["_id"]),
                messages=d["messages"],
                created_at=d["created_at"],
                updated_at=d["updated_at"],
            )
            for d in docs
        ]


_USER_PROMPTS = [
    "Hola, necesito ayuda con mi cultivo de café.",
    "¿Hay riesgo de helada esta semana en mi parcela?",
    "El maíz se ve amarillo, ¿puede ser falta de agua?",
    "¿Cuándo es la mejor ventana para cosechar mi tomate?",
    "Vi unos insectos pequeños en las hojas, ¿qué plaga puede ser?",
    "¿Debo regar hoy o esperar a mañana?",
    "Las hojas tienen manchas marrones, ¿es roya?",
    "¿Qué fertilizante recomiendas para esta etapa?",
]

_ASSISTANT_REPLIES = [
    "Claro, cuéntame más sobre la zona y la etapa fenológica del cultivo.",
    "Según el pronóstico, la temperatura mínima estará por encima del umbral de helada.",
    "Puede ser estrés hídrico; revisemos la humedad del suelo y el último riego.",
    "La ventana óptima es entre los próximos 3 y 5 días según el clima.",
    "Por la descripción podría tratarse de pulgones; te recomiendo confirmar con una foto.",
    "Hoy la evapotranspiración es alta, conviene regar al atardecer.",
    "Las manchas marrones con halo amarillo son típicas de roya; conviene aplicar tratamiento preventivo.",
    "Para esta etapa te recomiendo un fertilizante con mayor contenido de potasio.",
]


def make_fake_conversation(
    n_messages: int = 6, seed: int = 0
) -> list[ChatMessageCreate]:
    """Genera una lista determinista de mensajes alternando user/assistant
    con contenido agro-realista. Útil para evals reproducibles."""
    rng = random.Random(seed)
    messages: list[ChatMessageCreate] = []
    for i in range(n_messages):
        if i % 2 == 0:
            content = rng.choice(_USER_PROMPTS)
            messages.append(ChatMessageCreate(role="user", content=content))
        else:
            content = rng.choice(_ASSISTANT_REPLIES)
            messages.append(ChatMessageCreate(role="assistant", content=content))
    return messages


def make_fake_users(n: int = 3, seed: int = 0) -> list[str]:
    """Genera N teléfonos válidos `+529991xxxxxx` deterministas."""
    rng = random.Random(seed)
    return [f"+529991{rng.randint(0, 999999):06d}" for _ in range(n)]
