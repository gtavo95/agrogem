from datetime import timedelta

from google.cloud.storage import Bucket

from domain.pest.storage import StorageError


class GcsPestStorage:
    """GCS adapter for the PestStorage port."""

    def __init__(self, bucket: Bucket, upload_url_ttl_minutes: int = 15):
        self._bucket = bucket
        self._upload_url_ttl = timedelta(minutes=upload_url_ttl_minutes)

    def generate_upload_url(self, object_path: str, content_type: str) -> str:
        try:
            blob = self._bucket.blob(object_path)
            return blob.generate_signed_url(
                version="v4",
                expiration=self._upload_url_ttl,
                method="PUT",
                content_type=content_type,
            )
        except Exception as e:
            raise StorageError(f"Failed to generate signed URL: {e}") from e

    async def read_bytes(self, object_path: str) -> bytes:
        blob = self._bucket.blob(object_path)
        try:
            data = blob.download_as_bytes()
        except Exception as e:
            raise StorageError(f"Failed to read {object_path}: {e}") from e
        return data
