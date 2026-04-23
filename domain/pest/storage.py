from typing import Protocol


class StorageError(Exception):
    """Raised when the object storage provider fails."""


class PestStorage(Protocol):
    """Port: contract for object storage of pest images.

    Implementations must provide a short-lived upload URL the client can PUT to,
    and a way to read the bytes back server-side for embedding.
    """

    def generate_upload_url(self, object_path: str, content_type: str) -> str: ...

    async def read_bytes(self, object_path: str) -> bytes: ...
