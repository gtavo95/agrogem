from fastapi import Request
from google.cloud.storage import Bucket, Client


def create_gcs_bucket(bucket_name: str) -> Bucket:
    client = Client()
    return client.bucket(bucket_name)


def get_gcs_bucket(request: Request) -> Bucket:
    """Dependency to retrieve the GCS bucket from app state."""
    return request.app.state.gcs_bucket
