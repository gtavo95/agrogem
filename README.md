# Agrogem API

Backend para una app móvil. FastAPI + MongoDB + Redis, con autenticación simple basada en teléfono + password y sesiones de chat con TTL.

## Stack

- **FastAPI** (async)
- **MongoDB** vía [motor](https://motor.readthedocs.io/) — persistencia de usuarios y conversaciones
- **Redis** vía [redis-py](https://redis.readthedocs.io/) — sesiones de chat con TTL y cache de clima
- **bcrypt** para hashing de passwords
- **GCP Secret Manager** para secretos en prod (con fallback a `.env` en dev)
- **Docker** para deploy (Cloud Run)

## Arquitectura

El proyecto sigue **ports & adapters** (hexagonal):

- **`domain/<x>/`** es el core de negocio. No importa nada de `providers/`.
  - `schema.py`: entidades y DTOs (Pydantic).
  - `repository.py`: el **puerto** — un `Protocol` que define el contrato de persistencia.
  - `service.py`: lógica de aplicación. Recibe el puerto por parámetro, nunca conoce al adapter.
  - `router.py`: adapter de entrada (FastAPI). Compone el caso de uso inyectando el repo vía `Depends`.
- **`providers/<infra>/`** son los **adapters** de infraestructura. Cada uno implementa uno o más puertos del dominio.
  - `config.py`: cliente + helpers de conexión.
  - `dependencies.py`: factories `get_*_repository` que FastAPI inyecta en los routers.
  - `*_repository.py`: implementación concreta del puerto.

Regla de dependencia: **`domain/` no importa `providers/`**; `providers/` sí importa `domain/` para implementar sus puertos.

## Estructura

```
.
├── auth/
│   └── secrets.py                  # GCP Secret Manager loader
├── domain/                         # Core de negocio (hexagonal: adentro)
│   ├── user/
│   │   ├── schema.py               # Entidad User + DTOs
│   │   ├── repository.py           # Puerto: UserRepository (Protocol)
│   │   ├── service.py              # Casos de uso (register, authenticate)
│   │   └── router.py               # Adapter HTTP
│   ├── session/                    # Sesiones de chat con TTL
│   ├── chat/                       # Conversaciones y mensajes
│   ├── weather/                    # Clima (con puertos provider + cache)
│   ├── gbif/                       # Ocurrencias de especies (GBIF)
│   ├── geocoding/                  # Direcciones ↔ coordenadas (con puertos provider + cache)
│   ├── soil/                       # Perfil de suelo (SoilGrids, con puertos provider + cache)
│   ├── elevation/                  # Altitud (Open-Meteo, con puertos provider + cache)
│   ├── climate/                    # Histórico climático (NASA POWER, con puertos provider + cache)
│   └── disease_risk/               # Tool derivado: riesgo de enfermedad (reusa WeatherProvider)
├── providers/                      # Adapters de infraestructura (hexagonal: afuera)
│   ├── mongo/
│   │   ├── config.py               # Cliente Motor + get_mongo dependency
│   │   ├── dependencies.py         # get_chat_repository, get_user_repository
│   │   ├── chat_repository.py      # MongoChatRepository (implementa ChatRepository)
│   │   └── user_repository.py      # MongoUserRepository (implementa UserRepository)
│   ├── redis/
│   │   ├── config.py               # Cliente async + get_redis dependency
│   │   ├── dependencies.py         # get_session_repository
│   │   ├── session_repository.py   # RedisSessionRepository (implementa SessionRepository)
│   │   ├── weather_cache.py        # RedisWeatherCache (implementa WeatherCache)
│   │   ├── geocoding_cache.py      # RedisGeocodingCache (implementa GeocodingCache)
│   │   ├── soil_cache.py           # RedisSoilCache (implementa SoilCache)
│   │   ├── elevation_cache.py      # RedisElevationCache (implementa ElevationCache)
│   │   └── climate_cache.py        # RedisClimateHistoryCache (implementa ClimateHistoryCache)
│   ├── openmeteo/
│   │   ├── weather_provider.py     # Adapter HTTP para WeatherProvider
│   │   └── elevation_provider.py   # Adapter HTTP para ElevationProvider
│   ├── nominatim/
│   │   └── geocoding_provider.py   # Adapter HTTP (OSM) para GeocodingProvider
│   ├── soilgrids/
│   │   └── soil_provider.py        # Adapter HTTP (ISRIC) para SoilProvider
│   └── nasapower/
│       └── climate_provider.py     # Adapter HTTP (NASA POWER) para ClimateHistoryProvider
├── .http/                          # Requests de ejemplo (un archivo por dominio)
├── config.py                       # Lifespan: carga secretos, abre/cierra clientes
├── main.py                         # App FastAPI + registro de routers
├── Dockerfile
└── requirements.txt
```

### Agregar un dominio nuevo

1. Crea `domain/<nombre>/` con `schema.py`, `repository.py` (el puerto), `service.py`, `router.py`.
2. Implementa el puerto como adapter en `providers/<infra>/<nombre>_repository.py`.
3. Expone la factory en `providers/<infra>/dependencies.py` y úsala en el router con `Depends`.
4. Incluye el router en `main.py`.
5. Añade `.http/<nombre>.http`.

### Cambiar el adapter (p.ej. Redis → Memcached)

1. Crea `providers/memcached/session_repository.py` que implemente `SessionRepository`.
2. Expón `get_session_repository` en `providers/memcached/dependencies.py`.
3. Cambia el import en los routers. El `domain/` no se toca.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edita .env: GOOGLE_CLOUD_PROJECT, MODE (DEV|PROD), y opcionalmente MONGODB_URI, REDIS_URI
```

Si usas GCP Secret Manager:

```bash
gcloud auth application-default login
```

## Correr en local

```bash
fastapi dev main.py
```

- API: http://127.0.0.1:8000
- Docs interactivas: http://127.0.0.1:8000/docs

## Endpoints

| Método | Ruta                       | Descripción                                                      |
| ------ | -------------------------- | ---------------------------------------------------------------- |
| POST   | `/users/register`          | Crea un usuario nuevo                                            |
| POST   | `/sessions`                | Abre una sesión de chat (Redis, TTL 24h)                         |
| GET    | `/sessions/{id}`           | Obtiene una sesión activa                                        |
| PATCH  | `/sessions/{id}/state`     | Fusiona claves en el estado de la sesión                         |
| DELETE | `/sessions/{id}`           | Cierra y elimina la sesión                                       |
| POST   | `/chat/messages`           | Envía un mensaje en una sesión activa (persistido en Mongo)      |
| GET    | `/chat/conversations`      | Lista conversaciones, opcional `?user_phone=`                    |
| GET    | `/weather?lat=&lon=`       | Clima actual + pronóstico 7d (Open-Meteo, cache Redis 15min)     |
| GET    | `/gbif/species`            | Ocurrencias de una especie en un país (GBIF, cache Redis 24h)    |
| GET    | `/geocode?q=&country=`     | Forward geocoding: texto → lat/lon (Nominatim, cache Redis 30d)  |
| GET    | `/geocode/reverse?lat=&lon=` | Reverse geocoding: lat/lon → municipio/estado/país (Nominatim) |
| GET    | `/soil?lat=&lon=`          | Perfil de suelo 0-30 cm (ISRIC SoilGrids, cache Redis 90d)       |
| POST   | `/pest/upload-url`         | Signed URL (v4, ~15 min) para subir la foto del usuario a GCS    |
| POST   | `/pest/identify`           | kNN ponderado sobre `pest_embeddings` (Atlas `$vectorSearch`)    |
| GET    | `/elevation?lat=&lon=`     | Altitud en m.s.n.m (Open-Meteo Elevation, cache Redis 365d)      |
| GET    | `/climate/history?lat=&lon=&start=&end=&granularity=` | Histórico climático desde 1981 (NASA POWER AG, cache Redis 7d) |
| GET    | `/disease-risk?lat=&lon=&disease=` | Índice de riesgo 7d para `coffee_rust` / `late_blight` / `corn_rust` (derivado de `/weather`) |

Ejemplos de uso en `.http/`. Si usas VS Code, instala la extensión **REST Client** para ejecutarlos directo desde el editor.

### Weather (`/weather`)

Proxy a [Open-Meteo](https://open-meteo.com/) con cache en Redis (TTL 15 min por coordenada, key `weather:{lat}:{lon}`). No requiere API key.

**Query params**

| Param | Tipo  | Rango         |
| ----- | ----- | ------------- |
| `lat` | float | `[-90, 90]`   |
| `lon` | float | `[-180, 180]` |

**Respuesta** incluye, en una sola llamada:

- `current`: temperatura, humedad relativa, precipitación, viento, weather code
- `hourly` (7 días): temperatura, humedad relativa, probabilidad de precipitación
- `daily` (7 días): T° max/min, precipitación total, **ET₀ (evapotranspiración FAO)**, **UV max**

**Arquitectura hexagonal** — los puertos viven en `domain/weather/` y los adapters en `providers/`:

```
domain/weather/
├── schema.py          # Modelos Pydantic
├── provider.py        # Port: WeatherProvider (contrato de fuente externa)
├── cache.py           # Port: WeatherCache (contrato de cache)
├── service.py         # fetch_weather(provider, cache, lat, lon) — lógica pura
└── router.py          # DI: conecta adapters concretos a los ports

providers/openmeteo/
└── weather_provider.py   # Adapter HTTP (httpx) para WeatherProvider

providers/redis/
└── weather_cache.py      # Adapter Redis para WeatherCache
```

Para cambiar de proveedor (p.ej. NASA POWER), solo añade un nuevo adapter en `providers/` y ajusta `get_weather_provider()` en `domain/weather/router.py`. El dominio queda intacto.

### Geocoding (`/geocode`, `/geocode/reverse`)

Proxy a [Nominatim](https://nominatim.org/) (OpenStreetMap) con cache en Redis (TTL 30 días). Pensado como **tool del agente**: el LLM traduce "mi parcela en Chimaltenango" a coordenadas antes de llamar a `/weather`, `/gbif`, etc.

**`GET /geocode`** — forward (texto → coords, top-1)

| Param     | Tipo   | Requerido | Descripción                                           |
| --------- | ------ | --------- | ----------------------------------------------------- |
| `q`       | string | sí        | Texto libre. Ej: `"Chimaltenango"`, `"Zapopan, Jal."` |
| `country` | string | no        | Filtro ISO alpha-2. Ej: `"GT"`, `"MX"`                |

Respuestas: `200` con `{ lat, lon, display_name, country_code, state, municipality, type }`, `404` si no hay match, `502` si Nominatim falla.

**`GET /geocode/reverse?lat=&lon=`** — reverse (coords → lugar). Rango: `lat ∈ [-90,90]`, `lon ∈ [-180,180]`. Misma forma de respuesta que forward.

**Notas operativas:**

- Nominatim público limita a ~1 req/s y exige `User-Agent` identificable (`agrogem/1.0`). El cache agresivo (30 días, keys `geocode:fwd:{country|ANY}:{query}` y `geocode:rev:{lat}:{lon}`) absorbe la mayoría del tráfico.
- Para volumen alto en producción: self-hostear Nominatim (imagen Docker oficial) o cambiar al adapter de Mapbox / LocationIQ / Google — solo se agrega un nuevo archivo en `providers/` y se ajusta `get_geocoding_provider()`.

### Soil (`/soil`)

Proxy a [ISRIC SoilGrids v2.0](https://www.isric.org/explore/soilgrids) con cache en Redis (TTL 90 días, suelo no cambia). Sin API key.

**`GET /soil?lat=&lon=`** devuelve 3 horizontes de la zona radicular (`0-5`, `5-15`, `15-30` cm), cada uno con:

| Campo               | Unidad    | Descripción                                  |
| ------------------- | --------- | -------------------------------------------- |
| `ph`                | pH        | pH en H₂O                                    |
| `soc_g_per_kg`      | g/kg      | Carbono orgánico del suelo (materia orgánica) |
| `nitrogen_g_per_kg` | g/kg      | Nitrógeno total                              |
| `clay_pct`          | %         | Arcilla                                      |
| `sand_pct`          | %         | Arena                                        |
| `silt_pct`          | %         | Limo                                         |
| `cec_mmol_per_kg`   | mmol(c)/kg | Capacidad de intercambio catiónico          |
| `texture_class`     | string    | Clase textural USDA (derivada de sand/silt/clay) |

Además, a nivel raíz: `dominant_texture` (textura del horizonte 0-5 cm) e `interpretation` — un resumen en lenguaje natural pensado para que el agente lo consuma directo (p.ej. *"Horizonte superficial (0-5 cm): ligeramente ácido (pH 6.2); materia orgánica moderada (SOC 12.4 g/kg); textura clay loam."*).

Respuestas: `200` con el perfil, `404` si no hay cobertura (océano, cuerpos de agua, latitudes extremas), `502` en falla upstream.

### Pest (`/pest`)

Clasificador kNN multimodal pensado para ser consumido como **tool** por el agente de Gemma en el móvil. La predicción on-device se complementa con los vecinos más cercanos en una biblioteca etiquetada (`agrogem.pest_embeddings`, 17 plagas, 768-dim).

**Flujo:**

1. `POST /pest/upload-url` — el backend responde `{ object_path, signed_url, content_type, expires_in_seconds }`.
2. Cliente hace `PUT` binario a `signed_url` con el `content_type` indicado. La imagen queda en `queries/<uuid>.jpg`.
3. `POST /pest/identify` con `{ object_path }` — el backend descarga la imagen de GCS, genera su embedding con `gemini-embedding-2` (output 768), y ejecuta `$vectorSearch` en Atlas. Agrega top-K por **voto ponderado por similitud** y devuelve:

```json
{
  "top_match": { "pest_name": "Spodoptera_litura", "similarity": 0.87, "weighted_score": 3.2, "confidence": "high" },
  "alternatives": [ { "pest_name": "...", "similarity": 0.81, "image_id": "pest_00123" }, ... ],
  "votes": { "Spodoptera_litura": 3.2, "Helicoverpa_armigera": 0.8 }
}
```

`top_match` puede venir `null` si el ratio `winner_weight / total_weight` no supera el piso mínimo — es preferible decirle al agente "no tengo evidencia" que forzar una clase.

**Arquitectura hexagonal** — tres puertos independientes:

```
domain/pest/
├── schema.py        # Pydantic models
├── embedder.py      # Port: PestEmbedder (async embed_image)
├── storage.py       # Port: PestStorage (generate_upload_url, read_bytes)
├── repository.py    # Port: PestRepository (search_similar)
├── service.py       # Orquestación: read → embed → search → weighted vote
└── router.py        # Adapters montados vía Depends

providers/gemini/    # embed_content con gemini-embedding-2 (API key)
providers/gcs/       # signed URL v4 + download_as_bytes
providers/mongo/pest_repository.py  # Atlas $vectorSearch
```

**Infra que hay que crear una sola vez:**

- **Atlas vector index** (crear vía UI o `mongosh`). Nombre exacto: `pest_vector_index`. Definición:

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

- **Lifecycle rule del bucket** para auto-borrar `queries/` a 1 día (mínimo granular de GCS):

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

- **Permisos para signed URLs**: la service account del backend necesita `roles/iam.serviceAccountTokenCreator` sobre sí misma para firmar sin private key (requerido en Cloud Run).

**Scripts auxiliares:**

```bash
# 1) Migrar los image_bytes existentes de Mongo → GCS prefijo reference/
.venv/bin/python -m scripts.migrate_bytes_to_gcs

# 2) Evaluar kNN en leave-one-out antes de exponer el tool
.venv/bin/python -m scripts.calibrate_knn --k 5
```

`calibrate_knn` reporta accuracy global + por clase + histograma de similitudes (correctas vs incorrectas) + threshold sugerido para `MIN_CONFIDENCE_RATIO` en `domain/pest/service.py`.

### Elevation (`/elevation`)

Proxy a [Open-Meteo Elevation](https://open-meteo.com/en/docs/elevation-api) con cache Redis de 365 días (la altitud no cambia). Sin API key.

**`GET /elevation?lat=&lon=`** → `{ lat, lon, elevation_m: float }`. Útil para: idoneidad de cultivo por piso altitudinal, riesgo de heladas, ajuste de ET₀ en recomendaciones de riego.

Respuestas: `200` con altitud, `404` si no hay dato, `502` si el proveedor falla.

### Climate history (`/climate/history`)

Proxy a [NASA POWER](https://power.larc.nasa.gov/) (community `AG` — agroclimatología). Datos globales desde 1981. Cache Redis 7 días por `(lat, lon, start, end, granularity)`.

**Query params:**

| Param         | Tipo   | Requerido | Descripción                                                    |
| ------------- | ------ | --------- | -------------------------------------------------------------- |
| `lat`, `lon`  | float  | sí        | Rango estándar                                                 |
| `start`, `end`| string | sí        | `YYYY-MM-DD`                                                   |
| `granularity` | string | no        | `monthly` (default, ergonómico para LLM) o `daily` (máx. 366d) |

**Variables devueltas** (por punto de la serie): `t2m` (T° media), `t2m_max`, `t2m_min`, `precipitation_mm`, `rh_pct` (humedad relativa), `solar_mj_m2` (radiación solar de onda corta). Valores `null` cuando POWER no tiene dato (sentinela `-999` ya filtrado).

Pensado para que el agente responda preguntas como *"¿cuánto llovió en mi parcela los últimos 5 años vs. el promedio?"* o *"¿este año es más cálido que lo normal?"*.

### Disease risk (`/disease-risk`)

**Tool derivado** — sin API externa nueva. Combina el forecast de `/weather` (próximos 7 días, incluye ahora `relative_humidity_2m` horaria) con reglas agronómicas específicas por enfermedad.

**`GET /disease-risk?lat=&lon=&disease=`** — `disease` ∈ `coffee_rust | late_blight | corn_rust`. Respuesta:

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

**Reglas de scoring** (0.0-1.0, mapeado a `low <0.3 / moderate <0.5 / high <0.75 / very_high`):

| Enfermedad      | T° óptima (+0.4)  | RH media (+0.3) | Días lluviosos (+0.3) |
| --------------- | ----------------- | --------------- | --------------------- |
| `coffee_rust`   | 21-25 °C          | ≥ 80%           | ≥ 3                   |
| `late_blight`   | 10-25 °C          | ≥ 85%           | ≥ 4                   |
| `corn_rust`     | 20-26 °C          | ≥ 75%           | ≥ 3                   |

**No tiene cache propio** — reusa el del `/weather` (15 min). La composición es a nivel de dominio: `domain/disease_risk/service.py` recibe `WeatherProvider` + `WeatherCache` y llama a `domain.weather.service.fetch_weather`. Para añadir una enfermedad nueva, basta con agregar una entrada a `_DISEASE_RULES` en `domain/disease_risk/service.py` y ampliar el `Literal` de `DiseaseName` en el schema.

## Secretos

Los nombres listados en `config.py` → `required_secrets` se buscan en GCP Secret Manager como `{MODE}_{NAME}` (p.ej. `PROD_MONGODB_URI`, `PROD_REDIS_URI`). Si la variable ya está en el entorno (vía `.env`), la búsqueda se salta.

Secretos requeridos:

- `MONGODB_URI`
- `REDIS_URI`
- `GEMINI_API_KEY` — para `gemini-embedding-2` vía Gemini API (ai.google.dev)
- `GCS_BUCKET` — nombre del bucket para `reference/`, `queries/`, `community/`

## Docker

```bash
docker build -t agrogem .
docker run --rm -p 8080:8080 --env-file .env agrogem
```

## Persistencia

- **MongoDB** — DB `agrogem`. Colecciones: `users`, `conversations`, `pest_embeddings` (768-dim, 17 plagas).
- **Redis** — keys `chat:session:{uuid}` (TTL 24h), `weather:{lat}:{lon}` (15 min), `geocode:{fwd|rev}:...` (30d), `soil:{lat}:{lon}` (90d), `elevation:{lat}:{lon}` (365d), `climate:hist:{granularity}:{lat}:{lon}:{start}:{end}` (7d).
- **GCS** — bucket `$GCS_BUCKET` con prefijos `reference/` (ground truth permanente), `queries/` (TTL 1d vía lifecycle), `community/` (reservado).

## Data sources & attribution

Este proyecto consume datos abiertos de terceros. Si lo desplegás o redistribuís, respetá las licencias/atribuciones de cada fuente:

- **[Open-Meteo](https://open-meteo.com/)** — Weather & Elevation APIs. Uso gratuito (non-commercial / con atribución). Licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **[Nominatim](https://nominatim.org/)** / **OpenStreetMap** — Geocoding. Datos © OpenStreetMap contributors, licencia [ODbL](https://opendatacommons.org/licenses/odbl/). El cliente manda `User-Agent: agrogem/1.0` y respeta el [usage policy](https://operations.osmfoundation.org/policies/nominatim/) (≤1 req/s).
- **[ISRIC SoilGrids](https://www.isric.org/explore/soilgrids)** — Perfil de suelo. Licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Cita: Poggio et al., *SOIL*, 2021.
- **[NASA POWER](https://power.larc.nasa.gov/)** — Histórico climático. Dominio público, atribución recomendada.
- **[GBIF](https://www.gbif.org/)** — Ocurrencias de especies. Datos bajo [CC BY / CC BY-NC / CC0](https://www.gbif.org/terms) según el dataset; citar el GBIF download DOI cuando aplique.
- **[Google Gemini API](https://ai.google.dev/)** — Embeddings para kNN de plagas. Sujeto a los [términos de Gemini API](https://ai.google.dev/terms).

## Reporting security issues

Si encontrás una vulnerabilidad, por favor **no** abras un issue público. Reportala por email al mantenedor (ver autor en git history) y esperá confirmación antes de divulgarla.

## License

[MIT](LICENSE) © 2026 Gustavo Gordillo
