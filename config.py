import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from auth.secrets import load_secrets
from providers.gcs.config import create_gcs_bucket
from providers.gemini.config import create_gemini_client
from providers.mongo.config import close_mongo, create_mongo_client
from providers.redis.config import (
    aclose as redis_aclose,
    get_async_client as create_redis_client,
    ping as redis_ping,
)

load_dotenv()

# Secrets required by the app. Names map to environment variables and
# to GCP Secret Manager IDs as `{MODE}_{NAME}` (e.g. PROD_MONGODB_URI).
required_secrets = [
    "MONGODB_URI",
    "REDIS_URI",
    "GEMINI_API_KEY",
    "GCS_BUCKET",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    mode = os.environ.get("MODE", "PROD")

    load_secrets(mode, project_id, required_secrets)

    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        raise RuntimeError(
            "FATAL: MONGODB_URI not found. Set it in .env or in GCP Secret Manager."
        )

    redis_url = os.environ.get("REDIS_URI")
    if not redis_url:
        raise RuntimeError(
            "FATAL: REDIS_URI not found. Set it in .env or in GCP Secret Manager."
        )

    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise RuntimeError(
            "FATAL: GEMINI_API_KEY not found. Set it in .env or in GCP Secret Manager."
        )
    gcs_bucket = os.environ.get("GCS_BUCKET")
    if not gcs_bucket:
        raise RuntimeError(
            "FATAL: GCS_BUCKET not found. Set it in .env or in GCP Secret Manager."
        )

    try:
        app.state.mongo = create_mongo_client(mongo_uri)
        print("✓ MongoDB connected")
    except Exception as e:
        raise RuntimeError(f"FATAL: MongoDB connection failed: {e}")

    try:
        app.state.redis = create_redis_client(redis_url)
        await redis_ping(app.state.redis)
        print("✓ Redis connected")
    except Exception as e:
        raise RuntimeError(f"FATAL: Redis connection failed: {e}")

    try:
        app.state.gemini = create_gemini_client(gemini_api_key)
        print("✓ Gemini client ready")
    except Exception as e:
        raise RuntimeError(f"FATAL: Gemini client init failed: {e}")

    try:
        app.state.gcs_bucket = create_gcs_bucket(gcs_bucket)
        print(f"✓ GCS bucket '{gcs_bucket}' ready")
    except Exception as e:
        raise RuntimeError(f"FATAL: GCS bucket init failed: {e}")

    yield

    if app.state.redis:
        await redis_aclose(app.state.redis)
        print("✓ Redis closed")
    if app.state.mongo:
        close_mongo(app.state.mongo)
        print("✓ MongoDB closed")
