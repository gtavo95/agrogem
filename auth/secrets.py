import os
from google.cloud import secretmanager


def get_secret(secret_id: str, project_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def load_secrets(mode: str, project_id: str, secrets: list[str]) -> None:
    """
    Load secrets from GCP Secret Manager into environment variables.

    The GCP secret ID is built as `{MODE}_{NAME}` (e.g. PROD_MONGODB_URI).
    Secrets already present in the environment are skipped.
    """
    if mode not in ("DEV", "PROD"):
        raise ValueError("Invalid mode. Must be either DEV or PROD")

    print(f"--- Loading Secrets for Project: {project_id} (Mode: {mode}) ---")

    for secret_name in secrets:
        if secret_name in os.environ:
            print(f"✓ {secret_name} found in environment")
            continue

        gcp_secret_id = f"{mode}_{secret_name}"
        try:
            os.environ[secret_name] = get_secret(gcp_secret_id, project_id)
            print(f"✓ {secret_name} loaded from Secret Manager ({gcp_secret_id})")
        except Exception as e:
            print(
                f"⚠ {secret_name} failed to load from Secret Manager ({gcp_secret_id}): {e}"
            )
