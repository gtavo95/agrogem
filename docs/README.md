# Agrogem API

Backend for a mobile app. FastAPI + MongoDB + Redis, with simple phone + password authentication and chat sessions with TTL.

## Stack

- **FastAPI** (async)
- **MongoDB** via [motor](https://motor.readthedocs.io/) — persistence for users and conversations
- **Redis** via [redis-py](https://redis.readthedocs.io/) — chat sessions with TTL and weather cache
- **bcrypt** for password hashing
- **GCP Secret Manager** for secrets in prod (with `.env` fallback in dev)
- **Docker** for deployment (Cloud Run)

## Architecture

The project follows **ports & adapters** (hexagonal):

- **`domain/<x>/`** is the business core. It does not import anything from `providers/`.
  - `schema.py`: entities and DTOs (Pydantic).
  - `repository.py`: the **port** — a `Protocol` defining the persistence contract.
  - `service.py`: application logic. Receives the port as a parameter; never knows about the adapter.
  - `router.py`: input adapter (FastAPI). Wires the use case by injecting the repo via `Depends`.
- **`providers/<infra>/`** are the infrastructure **adapters**. Each one implements one or more domain ports.
  - `config.py`: client + connection helpers.
  - `dependencies.py`: `get_*_repository` factories that FastAPI injects into the routers.
  - `*_repository.py`: concrete implementation of the port.

Dependency rule: **`domain/` does not import `providers/`**; `providers/` does import `domain/` to implement its ports.

## Layout

```
.
├── auth/
│   └── secrets.py                  # GCP Secret Manager loader
├── domain/                         # Business core (hexagonal: inside)
│   ├── user/
│   │   ├── schema.py               # User entity + DTOs
│   │   ├── repository.py           # Port: UserRepository (Protocol)
│   │   ├── service.py              # Use cases (register, authenticate)
│   │   └── router.py               # HTTP adapter
│   ├── session/                    # Chat sessions with TTL
│   ├── chat/                       # Conversations and messages
│   ├── weather/                    # Weather (with provider + cache ports)
│   ├── gbif/                       # Species occurrences (GBIF)
│   ├── geocoding/                  # Addresses ↔ coordinates (with provider + cache ports)
│   ├── soil/                       # Soil profile (SoilGrids, with provider + cache ports)
│   ├── elevation/                  # Altitude (Open-Meteo, with provider + cache ports)
│   ├── climate/                    # Climate history (NASA POWER, with provider + cache ports)
│   └── disease_risk/               # Derived tool: disease risk (reuses WeatherProvider)
├── providers/                      # Infrastructure adapters (hexagonal: outside)
│   ├── mongo/
│   │   ├── config.py               # Motor client + get_mongo dependency
│   │   ├── dependencies.py         # get_chat_repository, get_user_repository
│   │   ├── chat_repository.py      # MongoChatRepository (implements ChatRepository)
│   │   └── user_repository.py     # MongoUserRepository (implements UserRepository)
│   ├── redis/
│   │   ├── config.py               # Async client + get_redis dependency
│   │   ├── dependencies.py         # get_session_repository
│   │   ├── session_repository.py   # RedisSessionRepository (implements SessionRepository)
│   │   ├── weather_cache.py        # RedisWeatherCache (implements WeatherCache)
│   │   ├── geocoding_cache.py      # RedisGeocodingCache (implements GeocodingCache)
│   │   ├── soil_cache.py           # RedisSoilCache (implements SoilCache)
│   │   ├── elevation_cache.py      # RedisElevationCache (implements ElevationCache)
│   │   └── climate_cache.py        # RedisClimateHistoryCache (implements ClimateHistoryCache)
│   ├── openmeteo/
│   │   ├── weather_provider.py     # HTTP adapter for WeatherProvider
│   │   └── elevation_provider.py   # HTTP adapter for ElevationProvider
│   ├── nominatim/
│   │   └── geocoding_provider.py   # HTTP adapter (OSM) for GeocodingProvider
│   ├── soilgrids/
│   │   └── soil_provider.py        # HTTP adapter (ISRIC) for SoilProvider
│   └── nasapower/
│       └── climate_provider.py     # HTTP adapter (NASA POWER) for ClimateHistoryProvider
├── .http/                          # Sample requests (one file per domain)
├── config.py                       # Lifespan: load secrets, open/close clients
├── main.py                         # FastAPI app + router registration
├── Dockerfile
└── requirements.txt
```

### Adding a new domain

1. Create `domain/<name>/` with `schema.py`, `repository.py` (the port), `service.py`, `router.py`.
2. Implement the port as an adapter in `providers/<infra>/<name>_repository.py`.
3. Expose the factory in `providers/<infra>/dependencies.py` and use it in the router with `Depends`.
4. Include the router in `main.py`.
5. Add `.http/<name>.http`.

### Swapping the adapter (e.g. Redis → Memcached)

1. Create `providers/memcached/session_repository.py` that implements `SessionRepository`.
2. Expose `get_session_repository` in `providers/memcached/dependencies.py`.
3. Change the import in the routers. `domain/` is untouched.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: GOOGLE_CLOUD_PROJECT, MODE (DEV|PROD), and optionally MONGODB_URI, REDIS_URI
```

If you use GCP Secret Manager:

```bash
gcloud auth application-default login
```

## Run locally

```bash
fastapi dev main.py
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs

## Endpoints

| Method | Route                       | Description                                                       |
| ------ | --------------------------- | ----------------------------------------------------------------- |
| POST   | `/users/register`           | Create a new user                                                 |
| POST   | `/sessions`                 | Open a chat session (Redis, TTL 24h)                              |
| GET    | `/sessions/{id}`            | Get an active session                                             |
| PATCH  | `/sessions/{id}/state`      | Merge keys into the session state                                 |
| DELETE | `/sessions/{id}`            | Close and delete the session                                      |
| POST   | `/chat/messages`            | Send a message in an active session (persisted in Mongo)          |
| GET    | `/chat/conversations`       | List conversations, optional `?user_phone=`                       |
| GET    | `/weather?lat=&lon=`        | Current weather + 7d forecast (Open-Meteo, Redis 15min cache)     |
| GET    | `/gbif/species`             | Occurrences of a species in a country (GBIF, Redis 24h cache)     |
| GET    | `/geocode?q=&country=`      | Forward geocoding: text → lat/lon (Nominatim, Redis 30d cache)    |
| GET    | `/geocode/reverse?lat=&lon=`| Reverse geocoding: lat/lon → municipality/state/country           |
| GET    | `/soil?lat=&lon=`           | Soil profile 0-30 cm (ISRIC SoilGrids, Redis 90d cache)           |
| POST   | `/pest/upload-url`          | Signed URL (v4, ~15 min) to upload the user's photo to GCS        |
| POST   | `/pest/identify`            | Weighted kNN over `pest_embeddings` (Atlas `$vectorSearch`)       |
| GET    | `/elevation?lat=&lon=`      | Altitude in m a.s.l. (Open-Meteo Elevation, Redis 365d cache)     |
| GET    | `/climate/history?lat=&lon=&start=&end=&granularity=` | Climate history since 1981 (NASA POWER AG, Redis 7d cache) |
| GET    | `/disease-risk?lat=&lon=&disease=` | 7d disease risk index (~50 diseases, derived from `/weather`) |
| GET    | `/pest-risk?lat=&lon=&pest=` | 7d pest risk index (derived from `/weather`)                    |
| GET    | `/frost-risk?lat=&lon=`     | 7d frost risk index (derived from `/weather` + `/elevation`)      |
| GET    | `/irrigation-risk?lat=&lon=&crop=` | 7d water-stress risk + irrigation recommendation in mm     |
| GET    | `/harvest-window?lat=&lon=&crop=` | 7d optimal harvest-window index                             |

Sample requests in `.http/`. If you use VS Code, install the **REST Client** extension to run them straight from the editor.

### Weather (`/weather`)

Proxy to [Open-Meteo](https://open-meteo.com/) with Redis cache (TTL 15 min per coordinate, key `weather:{lat}:{lon}`). No API key required.

**Query params**

| Param | Type  | Range         |
| ----- | ----- | ------------- |
| `lat` | float | `[-90, 90]`   |
| `lon` | float | `[-180, 180]` |

**Response** includes, in a single call:

- `current`: temperature, relative humidity, precipitation, wind, weather code
- `hourly` (7 days): temperature, relative humidity, precipitation probability
- `daily` (7 days): T° max/min, total precipitation, **ET₀ (FAO evapotranspiration)**, **max UV**

**Hexagonal architecture** — ports live in `domain/weather/` and adapters in `providers/`:

```
domain/weather/
├── schema.py          # Pydantic models
├── provider.py        # Port: WeatherProvider (external-source contract)
├── cache.py           # Port: WeatherCache (cache contract)
├── service.py         # fetch_weather(provider, cache, lat, lon) — pure logic
└── router.py          # DI: wires concrete adapters to the ports

providers/openmeteo/
└── weather_provider.py   # HTTP adapter (httpx) for WeatherProvider

providers/redis/
└── weather_cache.py      # Redis adapter for WeatherCache
```

To switch providers (e.g. to NASA POWER), just add a new adapter under `providers/` and tweak `get_weather_provider()` in `domain/weather/router.py`. The domain stays untouched.

### Geocoding (`/geocode`, `/geocode/reverse`)

Proxy to [Nominatim](https://nominatim.org/) (OpenStreetMap) with Redis cache (TTL 30 days). Designed as the **agent's tool**: the LLM translates "my plot in Chimaltenango" into coordinates before calling `/weather`, `/gbif`, etc.

**`GET /geocode`** — forward (text → coords, top-1)

| Param     | Type   | Required | Description                                            |
| --------- | ------ | -------- | ------------------------------------------------------ |
| `q`       | string | yes      | Free-form text. E.g. `"Chimaltenango"`, `"Zapopan, Jal."` |
| `country` | string | no       | ISO alpha-2 filter. E.g. `"GT"`, `"MX"`                |

Responses: `200` with `{ lat, lon, display_name, country_code, state, municipality, type }`, `404` if no match, `502` if Nominatim fails.

**`GET /geocode/reverse?lat=&lon=`** — reverse (coords → place). Range: `lat ∈ [-90,90]`, `lon ∈ [-180,180]`. Same response shape as forward.

**Operational notes:**

- Public Nominatim limits to ~1 req/s and requires an identifying `User-Agent` (`agrogem/1.0`). The aggressive cache (30 days, keys `geocode:fwd:{country|ANY}:{query}` and `geocode:rev:{lat}:{lon}`) absorbs most of the traffic.
- For high production volume: self-host Nominatim (official Docker image) or swap to the Mapbox / LocationIQ / Google adapter — just add a new file under `providers/` and tweak `get_geocoding_provider()`.

### Soil (`/soil`)

Proxy to [ISRIC SoilGrids v2.0](https://www.isric.org/explore/soilgrids) with Redis cache (TTL 90 days, soil doesn't change). No API key.

**`GET /soil?lat=&lon=`** returns 3 horizons of the root zone (`0-5`, `5-15`, `15-30` cm), each with:

| Field               | Unit       | Description                                  |
| ------------------- | ---------- | -------------------------------------------- |
| `ph`                | pH         | pH in H₂O                                    |
| `soc_g_per_kg`      | g/kg       | Soil organic carbon (organic matter)         |
| `nitrogen_g_per_kg` | g/kg       | Total nitrogen                               |
| `clay_pct`          | %          | Clay                                         |
| `sand_pct`          | %          | Sand                                         |
| `silt_pct`          | %          | Silt                                         |
| `cec_mmol_per_kg`   | mmol(c)/kg | Cation exchange capacity                     |
| `texture_class`     | string     | USDA texture class (derived from sand/silt/clay) |

Plus, at the root level: `dominant_texture` (texture of the 0-5 cm horizon) and `interpretation` — a natural-language summary intended to be consumed by the agent directly (e.g. *"Horizonte superficial (0-5 cm): ligeramente ácido (pH 6.2); materia orgánica moderada (SOC 12.4 g/kg); textura clay loam."*).

Responses: `200` with the profile, `404` if no coverage (ocean, water bodies, extreme latitudes), `502` on upstream failure.

### Pest (`/pest`)

Multimodal kNN classifier intended to be consumed as a **tool** by the on-device Gemma agent. The on-device prediction is augmented with the nearest neighbors in a labeled library (`agrogem.pest_embeddings`, 17 pests, 768-dim).

**Flow:**

1. `POST /pest/upload-url` — backend responds with `{ object_path, signed_url, content_type, expires_in_seconds }`.
2. Client `PUT`s the binary to `signed_url` with the indicated `content_type`. The image lands in `queries/<uuid>.jpg`.
3. `POST /pest/identify` with `{ object_path }` — backend downloads the image from GCS, generates its embedding with `gemini-embedding-2` (output 768), and runs `$vectorSearch` on Atlas. It aggregates top-K via **similarity-weighted vote** and returns:

```json
{
  "top_match": { "pest_name": "Spodoptera_litura", "similarity": 0.87, "weighted_score": 3.2, "confidence": "high" },
  "alternatives": [ { "pest_name": "...", "similarity": 0.81, "image_id": "pest_00123" }, ... ],
  "votes": { "Spodoptera_litura": 3.2, "Helicoverpa_armigera": 0.8 }
}
```

`top_match` may come back `null` if the `winner_weight / total_weight` ratio doesn't clear the minimum floor — it's better to tell the agent "I have no evidence" than to force a class.

**Hexagonal architecture** — three independent ports:

```
domain/pest/
├── schema.py        # Pydantic models
├── embedder.py      # Port: PestEmbedder (async embed_image)
├── storage.py       # Port: PestStorage (generate_upload_url, read_bytes)
├── repository.py    # Port: PestRepository (search_similar)
├── service.py       # Orchestration: read → embed → search → weighted vote
└── router.py        # Adapters mounted via Depends

providers/gemini/    # embed_content with gemini-embedding-2 (API key)
providers/gcs/       # signed URL v4 + download_as_bytes
providers/mongo/pest_repository.py  # Atlas $vectorSearch
```

**One-time infra to set up:**

- **Atlas vector index** (create via UI or `mongosh`). Exact name: `pest_vector_index`. Definition:

  ```json
  {
    "fields": [
      {
        "type": "vector",
        "path": "embedding",
        "numDimensions": 768,
        "similarity": "cosine"
      },
      {
        "type": "filter",
        "path": "pest_name"
      }
    ]
  }
  ```

- **Bucket lifecycle rule** to auto-delete `queries/` after 1 day (GCS' minimum granularity):

  ```bash
  cat > /tmp/lifecycle.json <<'EOF'
  {
    "lifecycle": {
      "rule": [
        {
          "action": { "type": "Delete" },
          "condition": { "age": 1, "matchesPrefix": ["queries/"] }
        }
      ]
    }
  }
  EOF
  gcloud storage buckets update gs://$GCS_BUCKET --lifecycle-file=/tmp/lifecycle.json
  ```

- **Permissions for signed URLs**: the backend service account needs `roles/iam.serviceAccountTokenCreator` on itself to sign without a private key (required on Cloud Run).

**Helper scripts:**

```bash
# 1) Migrate existing Mongo image_bytes → GCS reference/ prefix
.venv/bin/python -m scripts.migrate_bytes_to_gcs

# 2) Evaluate kNN in leave-one-out before exposing the tool
.venv/bin/python -m scripts.calibrate_knn --k 5
```

`calibrate_knn` reports global accuracy + per-class accuracy + similarity histogram (correct vs. incorrect) + a suggested threshold for `MIN_CONFIDENCE_RATIO` in `domain/pest/service.py`.

### Elevation (`/elevation`)

Proxy to [Open-Meteo Elevation](https://open-meteo.com/en/docs/elevation-api) with a 365-day Redis cache (altitude doesn't change). No API key.

**`GET /elevation?lat=&lon=`** → `{ lat, lon, elevation_m: float, interpretation }`. Useful for: crop suitability by altitudinal belt, frost risk, ET₀ adjustment in irrigation recommendations.

Responses: `200` with altitude, `404` if no data, `502` on provider failure.

### Climate history (`/climate/history`)

Proxy to [NASA POWER](https://power.larc.nasa.gov/) (community `AG` — agroclimatology). Global data since 1981. Redis cache 7 days per `(lat, lon, start, end, granularity)`.

**Query params:**

| Param         | Type   | Required | Description                                                       |
| ------------- | ------ | -------- | ----------------------------------------------------------------- |
| `lat`, `lon`  | float  | yes      | Standard range                                                    |
| `start`, `end`| string | yes      | `YYYY-MM-DD`                                                      |
| `granularity` | string | no       | `monthly` (default, LLM-friendly) or `daily` (max. 366d per call) |

**Returned variables** (per series point): `t2m` (mean T°), `t2m_max`, `t2m_min`, `precipitation_mm`, `rh_pct` (relative humidity), `solar_mj_m2` (shortwave solar radiation). Values are `null` when POWER has no data (the `-999` sentinel is already filtered).

Designed so the agent can answer questions like *"how much did it rain on my plot the last 5 years vs. the average?"* or *"is this year warmer than usual?"*.

### Disease risk (`/disease-risk`)

**Derived tool** — no new external API. Combines the `/weather` forecast (next 7 days, including hourly `relative_humidity_2m`) with disease-specific agronomic rules.

**`GET /disease-risk?lat=&lon=&disease=`** — `disease` ∈ ~50 values (`coffee_rust`, `late_blight`, `corn_rust`, …; full list in `domain/disease_risk/schema.py`). Response:

```json
{
  "disease": "coffee_rust",
  "lat": 14.56, "lon": -90.73,
  "risk_score": 0.7,
  "risk_level": "high",
  "factors": {
    "window_days": 7,
    "avg_temp_c": 22.4,
    "avg_humidity_pct": 84,
    "rainy_days": 4,
    "rule_notes": ["T° media 22.4°C en rango óptimo [21-25°C]", "humedad relativa 84% ≥ 80%", "4 días lluviosos (umbral 3)"]
  },
  "interpretation": "Riesgo alto de roya del café (Hemileia vastatrix) en los próximos 7 días. Factores: T° media 22.4°C en rango óptimo [21-25°C]; humedad relativa 84% ≥ 80%; 4 días lluviosos (umbral 3)."
}
```

**Scoring rules** (0.0-1.0, mapped to `low <0.3 / moderate <0.5 / high <0.75 / very_high`). Sample for the most common diseases:

| Disease         | Optimal T° (+0.4) | Mean RH (+0.3)  | Rainy days (+0.3)     |
| --------------- | ----------------- | --------------- | --------------------- |
| `coffee_rust`   | 21-25 °C          | ≥ 80%           | ≥ 3                   |
| `late_blight`   | 10-25 °C          | ≥ 85%           | ≥ 4                   |
| `corn_rust`     | 20-26 °C          | ≥ 75%           | ≥ 3                   |

**No own cache** — reuses `/weather`'s (15 min). Composition is at the domain level: `domain/disease_risk/service.py` receives `WeatherProvider` + `WeatherCache` and calls `domain.weather.service.fetch_weather`. To add a new disease, just add an entry to `_DISEASE_RULES` in `domain/disease_risk/service.py` and extend the `Literal` `DiseaseName` in the schema.

## Secrets

The names listed in `config.py` → `required_secrets` are looked up in GCP Secret Manager as `{MODE}_{NAME}` (e.g. `PROD_MONGODB_URI`, `PROD_REDIS_URI`). If the variable is already in the environment (via `.env`), the lookup is skipped.

Required secrets:

- `MONGODB_URI`
- `REDIS_URI`
- `GEMINI_API_KEY` — for `gemini-embedding-2` via the Gemini API (ai.google.dev)
- `GCS_BUCKET` — bucket name for `reference/`, `queries/`, `community/`

## Docker

```bash
docker build -t agrogem .
docker run --rm -p 8080:8080 --env-file .env agrogem
```

## Persistence

- **MongoDB** — DB `agrogem`. Collections: `users`, `conversations`, `pest_embeddings` (768-dim, 17 pests).
- **Redis** — keys `chat:session:{uuid}` (TTL 24h), `weather:{lat}:{lon}` (15 min), `geocode:{fwd|rev}:...` (30d), `soil:{lat}:{lon}` (90d), `elevation:{lat}:{lon}` (365d), `climate:hist:{granularity}:{lat}:{lon}:{start}:{end}` (7d).
- **GCS** — bucket `$GCS_BUCKET` with prefixes `reference/` (permanent ground truth), `queries/` (TTL 1d via lifecycle), `community/` (reserved).

## Data sources & attribution

This project consumes third-party open data. If you deploy or redistribute, respect each source's license/attribution:

- **[Open-Meteo](https://open-meteo.com/)** — Weather & Elevation APIs. Free use (non-commercial / with attribution). License [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **[Nominatim](https://nominatim.org/)** / **OpenStreetMap** — Geocoding. Data © OpenStreetMap contributors, [ODbL](https://opendatacommons.org/licenses/odbl/) license. The client sends `User-Agent: agrogem/1.0` and respects the [usage policy](https://operations.osmfoundation.org/policies/nominatim/) (≤1 req/s).
- **[ISRIC SoilGrids](https://www.isric.org/explore/soilgrids)** — Soil profile. License [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Citation: Poggio et al., *SOIL*, 2021.
- **[NASA POWER](https://power.larc.nasa.gov/)** — Climate history. Public domain, attribution recommended.
- **[GBIF](https://www.gbif.org/)** — Species occurrences. Data under [CC BY / CC BY-NC / CC0](https://www.gbif.org/terms) depending on the dataset; cite the GBIF download DOI when applicable.
- **[Google Gemini API](https://ai.google.dev/)** — Embeddings for the pest kNN. Subject to the [Gemini API terms](https://ai.google.dev/terms).

## Reporting security issues

If you find a vulnerability, please **do not** open a public issue. Report it by email to the maintainer (see author in git history) and wait for confirmation before disclosing it.

## License

[MIT](../LICENSE) © 2026 Gustavo Gordillo
