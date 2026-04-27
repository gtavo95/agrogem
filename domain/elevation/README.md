# `/elevation` — Altitude (m a.s.l.)

Tier 🟢 1 · Source: [Open-Meteo Elevation](https://open-meteo.com/en/docs/elevation-api) · Redis cache 365 days · No API key.

← [Back to main README](../../README.md)

## Endpoint

```
GET /elevation?lat=<float>&lon=<float>
```

## Input

| Parameter | Type  | Required | Range          | Description | Example   |
| --------- | ----- | -------- | -------------- | ----------- | --------- |
| `lat`     | float | yes      | `[-90, 90]`    | Latitude    | `14.5586` |
| `lon`     | float | yes      | `[-180, 180]`  | Longitude   | `-90.7295`|

### Request

```bash
curl "http://localhost:8000/elevation?lat=14.5586&lon=-90.7295"
```

```http
GET http://localhost:8000/elevation?lat=14.5586&lon=-90.7295
Accept: application/json
```

## Output

### 200 OK

```json
{
  "lat": 14.5586,
  "lon": -90.7295,
  "elevation_m": 1530.0,
  "interpretation": "Altitud 1530 m s.n.m (tierra templada / piso cafetero)."
}
```

### Fields

| Field            | Type       | Description                                                      |
| ---------------- | ---------- | ---------------------------------------------------------------- |
| `lat`, `lon`     | float      | Echoed coordinates                                               |
| `elevation_m`    | float (m)  | Altitude above sea level                                         |
| `interpretation` | string     | Spanish summary with altitudinal-belt classification             |

### Altitudinal belts

| Range (m) | Belt                                |
| --------- | ----------------------------------- |
| `< 800`   | tierra caliente / costa             |
| `< 1800`  | tierra templada / piso cafetero     |
| `< 2800`  | tierra fría / sierra                |
| `< 3500`  | tierra muy fría / altiplano         |
| `≥ 3500`  | páramo / puna alta                  |

### Errors

| Status | Cause                                  |
| ------ | -------------------------------------- |
| 404    | No data for those coordinates          |
| 422    | `lat`/`lon` out of range               |
| 502    | Open-Meteo down or timed out           |

## Tool definition (function calling)

```json
{
  "name": "elevation",
  "description": "Altitud (m.s.n.m) desde Open-Meteo Elevation. Cacheado 365 días (la altitud no cambia).",
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

## Implementation

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py)
- Schema: [`schema.py`](schema.py)
- HTTP provider: [`providers/openmeteo/elevation_provider.py`](../../providers/openmeteo/elevation_provider.py)
- Redis cache: [`providers/redis/elevation_cache.py`](../../providers/redis/elevation_cache.py)
