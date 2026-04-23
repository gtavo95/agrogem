from typing import Protocol

from domain.pest.schema import PestMatch


class PestRepository(Protocol):
    """Port: contract for pest-embedding similarity search."""

    async def search_similar(
        self, query_embedding: list[float], k: int
    ) -> list[PestMatch]: ...
