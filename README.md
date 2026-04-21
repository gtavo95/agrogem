# FastAPI + MongoDB + GCP Secret Manager Template

A minimal FastAPI template with:

- **MongoDB** via [motor](https://motor.readthedocs.io/) (async driver)
- **GCP Secret Manager** integration for loading secrets at startup
- **Docker** support for deployment (e.g. Cloud Run)
- `.env` fallback for local development

## Project structure

```
.
├── auth/
│   └── secrets.py       # GCP Secret Manager loader
├── db/
│   └── mongo.py         # Mongo client + helpers
├── config.py            # App lifespan: loads secrets, opens/closes Mongo
├── main.py              # FastAPI app + example endpoints
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Setup

1. **Clone and create a virtual environment**

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set:
   - `GOOGLE_CLOUD_PROJECT` — your GCP project ID
   - `MODE` — `DEV` or `PROD` (used as a prefix for secret names)
   - Optionally set `MONGODB_URI` directly to skip Secret Manager

3. **Authenticate with GCP** (only needed if using Secret Manager)

   ```bash
   gcloud auth application-default login
   ```

4. **Run locally**

   ```bash
   fastapi dev main.py
   ```

   Visit http://127.0.0.1:8000/docs for the interactive API docs.

## Secret Manager convention

Secrets listed in `config.py` → `required_secrets` are looked up in GCP
Secret Manager as `{MODE}_{NAME}`. Examples:

| Env var       | Mode   | GCP Secret ID       |
| ------------- | ------ | ------------------- |
| `MONGODB_URI` | `DEV`  | `DEV_MONGODB_URI`   |
| `MONGODB_URI` | `PROD` | `PROD_MONGODB_URI`  |

If the env var is already set (e.g. via `.env`), the Secret Manager lookup
is skipped.

## Docker

```bash
docker build -t fastapi-template .
docker run --rm -p 8080:8080 --env-file .env fastapi-template
```

## Extending the template

- Add new secrets: append to `required_secrets` in `config.py`.
- Add new collections: access via `request.app.state.mongo["db"]["collection"]`.
- Add new routes: create a new module and include its router in `main.py`.

## License

MIT
