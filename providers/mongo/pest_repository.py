from motor.motor_asyncio import AsyncIOMotorClient

from domain.pest.schema import PestMatch


DEFAULT_NUM_CANDIDATES_PER_K = 20


class MongoPestRepository:
    """MongoDB Atlas adapter for PestRepository using $vectorSearch.

    Requires an Atlas vector index named `VECTOR_INDEX` on the `embedding` field
    of `agrogem.pest_embeddings` (cosine, 768 dims).
    """

    VECTOR_INDEX = "pest_vector_index"

    def __init__(self, mongo: AsyncIOMotorClient):
        self._collection = mongo["agrogem"]["pest_embeddings"]

    async def search_similar(
        self, query_embedding: list[float], k: int
    ) -> list[PestMatch]:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.VECTOR_INDEX,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": max(k * DEFAULT_NUM_CANDIDATES_PER_K, k),
                    "limit": k,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "pest_name": 1,
                    "image_id": 1,
                    "similarity": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        cursor = self._collection.aggregate(pipeline)
        return [
            PestMatch(
                pest_name=doc["pest_name"],
                similarity=float(doc["similarity"]),
                image_id=doc.get("image_id"),
            )
            async for doc in cursor
        ]
