"""Migrate `image_bytes` from Mongo pest_embeddings into GCS.

For each doc in `agrogem.pest_embeddings` that has `image_bytes` but no
`gcs_path`, upload the bytes to `reference/{image_id}.jpg` in the configured
bucket, then update the doc with `gcs_path` and unset `image_bytes`.

Idempotent: docs already having `gcs_path` are skipped.

Run:
    .venv/bin/python -m scripts.migrate_bytes_to_gcs
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from google.cloud.storage import Client as GcsClient
from pymongo import MongoClient

from auth.secrets import load_secrets


REFERENCE_PREFIX = "reference/"
DEFAULT_CONTENT_TYPE = "image/jpeg"


def main() -> int:
    load_dotenv()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    mode = os.environ.get("MODE", "DEV")
    load_secrets(mode, project_id, ["MONGODB_URI", "GCS_BUCKET"])

    mongo_uri = os.environ["MONGODB_URI"]
    bucket_name = os.environ["GCS_BUCKET"]

    mongo = MongoClient(mongo_uri)
    collection = mongo["agrogem"]["pest_embeddings"]
    gcs = GcsClient()
    bucket = gcs.bucket(bucket_name)

    query = {"image_bytes": {"$exists": True}, "gcs_path": {"$exists": False}}
    total = collection.count_documents(query)
    print(f"Docs to migrate: {total}")
    if total == 0:
        return 0

    migrated = 0
    failed = 0
    cursor = collection.find(query, {"_id": 1, "image_id": 1, "image_bytes": 1})

    for doc in cursor:
        image_id = doc.get("image_id") or str(doc["_id"])
        object_path = f"{REFERENCE_PREFIX}{image_id}.jpg"
        try:
            blob = bucket.blob(object_path)
            blob.upload_from_string(doc["image_bytes"], content_type=DEFAULT_CONTENT_TYPE)
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"gcs_path": object_path}, "$unset": {"image_bytes": ""}},
            )
            migrated += 1
            if migrated % 50 == 0:
                print(f"  migrated {migrated}/{total}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {image_id}: {e}")

    print(f"Done. migrated={migrated} failed={failed} total={total}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
