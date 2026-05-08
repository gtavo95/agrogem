from datetime import timedelta
from typing import Any

import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.cloud.storage import Bucket
from google.oauth2 import service_account

from domain.pest.storage import StorageError


class GcsPestStorage:
    """GCS adapter for the PestStorage port."""

    def __init__(self, bucket: Bucket, upload_url_ttl_minutes: int = 15):
        self._bucket = bucket
        self._upload_url_ttl = timedelta(minutes=upload_url_ttl_minutes)
        self._credentials: Any = None
        self._auth_request: GoogleAuthRequest | None = None

    def _signing_kwargs(self) -> dict[str, Any]:
        # On Cloud Run / GCE the ADC are compute-engine credentials that only
        # carry a short-lived token (no private key), so they cannot sign URLs
        # locally. We refresh them and pass service_account_email + access_token
        # so the storage client delegates signing to the IAM signBlob API.
        # Requires the runtime SA to have roles/iam.serviceAccountTokenCreator
        # on itself.
        if self._credentials is None:
            self._credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self._auth_request = GoogleAuthRequest()

        creds = self._credentials
        if isinstance(creds, service_account.Credentials):
            return {}

        if not creds.valid:
            creds.refresh(self._auth_request)

        return {
            "service_account_email": creds.service_account_email,
            "access_token": creds.token,
        }

    def generate_upload_url(self, object_path: str, content_type: str) -> str:
        try:
            blob = self._bucket.blob(object_path)
            return blob.generate_signed_url(
                version="v4",
                expiration=self._upload_url_ttl,
                method="PUT",
                content_type=content_type,
                **self._signing_kwargs(),
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
