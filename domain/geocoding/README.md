# `/geocode` and `/geocode/reverse` — Geocoding

Tier 🟢 2 (forward) · 🟢 1 (reverse) · Source: [Nominatim](https://nominatim.org/) (OpenStreetMap) · Redis cache 30 days.

← [Back to main README](../../README.md)

Designed as the **agent's first tool**: the LLM translates *"my farm in Tecpán"* into coordinates before calling `/weather`, `/soil`, etc.

---

## `GET /geocode` — Forward (text → coords)

### Input

| Parameter | Type   | Required | Description                                 | Example                |
| --------- | ------ | -------- | ------------------------------------------- | ---------------------- |
| `q`       | string | yes      | Free-form text, min. 1 character            | `"Chimaltenango"`      |
| `country` | string | no       | ISO alpha-2 filter (reduces ambiguity)      | `"GT"`                 |

### Request

```bash
curl "http://localhost:8000/geocode?q=Chimaltenango&country=GT"
```

```http
GET http://localhost:8000/geocode?q=Chimaltenango&country=GT
Accept: application/json
```

### Output 200

```json
{
  "lat": 14.6611,
  "lon": -90.8210,
  "display_name": "Chimaltenango, Guatemala",
  "country_code": "gt",
  "state": "Chimaltenango",
  "municipality": "Chimaltenango",
  "type": "administrative",
  "interpretation": "Ubicación encontrada: Chimaltenango, Guatemala (14.6611, -90.8210)."
}
```

### Errors

| Status | Cause                                |
| ------ | ------------------------------------ |
| 404    | No match                             |
| 422    | Empty `q` or invalid `country`       |
| 502    | Nominatim down or timed out          |

---

## `GET /geocode/reverse` — Reverse (coords → place)

### Input

| Parameter | Type  | Required | Range          | Description | Example   |
| --------- | ----- | -------- | -------------- | ----------- | --------- |
| `lat`     | float | yes      | `[-90, 90]`    | Latitude    | `14.5586` |
| `lon`     | float | yes      | `[-180, 180]`  | Longitude   | `-90.7295`|

### Request

```bash
curl "http://localhost:8000/geocode/reverse?lat=14.5586&lon=-90.7295"
```

```http
GET http://localhost:8000/geocode/reverse?lat=14.5586&lon=-90.7295
Accept: application/json
```

### Output 200

```json
{
  "lat": 14.5586,
  "lon": -90.7295,
  "display_name": "Antigua Guatemala, Sacatepéquez, Guatemala",
  "country_code": "gt",
  "state": "Sacatepéquez",
  "municipality": "Antigua Guatemala",
  "type": "city",
  "interpretation": "Esa coordenada corresponde a Antigua Guatemala, Sacatepéquez, Guatemala."
}
```

### Errors

| Status | Cause                                  |
| ------ | -------------------------------------- |
| 404    | No result for those coordinates        |
| 422    | `lat`/`lon` out of range               |
| 502    | Nominatim down or timed out            |

---

## Fields (both endpoints)

| Field            | Type         | Description                                  |
| ---------------- | ------------ | -------------------------------------------- |
| `lat`, `lon`     | float        | Coordinates (returned or resolved)           |
| `display_name`   | string       | Full place label                             |
| `country_code`   | string\|null | Lowercase ISO alpha-2                        |
| `state`          | string\|null | Department / state / province                |
| `municipality`   | string\|null | Municipality / city                          |
| `type`           | string\|null | OSM type (administrative, village, city…)    |
| `interpretation` | string       | Spanish summary ready for Gemma              |

## Tool definitions (function calling)

```json
{
  "name": "geocode",
  "description": "Convierte texto libre en lat/lon (top-1). Cacheado 30 días por query normalizada + país.",
  "parameters": {
    "type": "object",
    "properties": {
      "q":       { "type": "string", "minLength": 1, "description": "Texto libre del lugar" },
      "country": { "type": "string", "minLength": 2, "maxLength": 2, "description": "ISO alpha-2 opcional" }
    },
    "required": ["q"]
  }
}
```

```json
{
  "name": "geocode_reverse",
  "description": "Convierte lat/lon en nombre de lugar (país, estado, municipio). Cacheado 30 días por coordenada.",
  "parameters": {
    "type": "object",
    "properties": {
      "lat": { "type": "number", "minimum": -90,  "maximum": 90,  "description": "Latitud" },
      "lon": { "type": "number", "minimum": -180, "maximum": 180, "description": "Longitud" }
    },
    "required": ["lat", "lon"]
  }
}
```

## Operational notes

- Public Nominatim limits to ~1 req/s and requires an identifying `User-Agent` (`agrogem/1.0`).
- The aggressive cache (30 days, keys `geocode:fwd:{country|ANY}:{query}` and `geocode:rev:{lat}:{lon}`) absorbs most traffic.
- For high volume: self-host Nominatim or swap the adapter to Mapbox / LocationIQ / Google.

## Implementation

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py)
- Schema: [`schema.py`](schema.py)
- HTTP provider: [`providers/nominatim/geocoding_provider.py`](../../providers/nominatim/geocoding_provider.py)
- Redis cache: [`providers/redis/geocoding_cache.py`](../../providers/redis/geocoding_cache.py)
