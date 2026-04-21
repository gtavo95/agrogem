import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from auth.secrets import load_secrets
from db.mongo import close_mongo, create_mongo_client

load_dotenv()

# Secrets required by the app. Names map to environment variables and
# to GCP Secret Manager IDs as `{MODE}_{NAME}` (e.g. PROD_MONGODB_URI).
required_secrets = [
    "MONGODB_URI",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    mode = os.environ.get("MODE", "DEV")

    load_secrets(mode, project_id, required_secrets)

    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        raise RuntimeError(
            "FATAL: MONGODB_URI not found. Set it in .env or in GCP Secret Manager."
        )

    try:
        app.state.mongo = create_mongo_client(mongo_uri)
        print("✓ MongoDB connected")
    except Exception as e:
        raise RuntimeError(f"FATAL: MongoDB connection failed: {e}")

    yield

    if app.state.mongo:
        close_mongo(app.state.mongo)
        print("✓ MongoDB closed")
