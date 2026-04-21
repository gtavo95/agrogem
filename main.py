from fastapi import FastAPI
from fastapi.requests import Request

from config import lifespan
from db.mongo import mongo_to_json

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"status": "ok"}


@app.get("/items")
async def list_items(request: Request):
    """Example endpoint: list documents from a generic `items` collection."""
    db = request.app.state.mongo
    cursor = db["app"]["items"].find({})
    docs = await cursor.to_list(length=100)
    return {"items": [mongo_to_json(d) for d in docs]}


@app.put("/items/{item_id}")
def update_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
