from motor.motor_asyncio import AsyncIOMotorClient

from domain.user.schema import User


class MongoUserRepository:
    """MongoDB adapter for the UserRepository port."""

    def __init__(self, mongo: AsyncIOMotorClient):
        self._users = mongo["agrogem"]["users"]

    async def find_by_phone(self, phone: str) -> User | None:
        doc = await self._users.find_one({"phone": phone})
        if doc is None:
            return None
        return _to_user(doc)

    async def insert(self, user: User) -> User:
        await self._users.insert_one(
            {
                "_id": user.id,
                "phone": user.phone,
                "password_hash": user.password_hash,
                "created_at": user.created_at,
            }
        )
        return user


def _to_user(doc: dict) -> User:
    return User(
        id=str(doc["_id"]),
        phone=doc["phone"],
        password_hash=doc["password_hash"],
        created_at=doc["created_at"],
    )
