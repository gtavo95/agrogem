# `/weather` — Current weather + 7-day forecast

Tier 🟢 1 · Source: [Open-Meteo](https://open-meteo.com/) · Redis cache 15 min · No API key.

← [Back to main README](../../README.md)

## Endpoint

```
GET /weather?lat=<float>&lon=<float>
```

## Input

| Parameter | Type  | Required | Range          | Description | Example  |
| --------- | ----- | -------- | -------------- | ----------- | -------- |
| `lat`     | float | yes      | `[-90, 90]`    | Latitude    | `14.76`  |
| `lon`     | float | yes      | `[-180, 180]`  | Longitude   | `-90.99` |

### Request

```bash
curl "http://localhost:8000/weather?lat=14.5586&lon=-90.7295"
```

```http
GET http://localhost:8000/weather?lat=14.5586&lon=-90.7295
Accept: application/json
```

## Output

### 200 OK

```json
{
  "latitude": 14.5586,
  "longitude": -90.7295,
  "timezone": "America/Guatemala",
  "current": {
    "time": "2026-04-27T14:00",
    "temperature_2m": 22.4,
    "relative_humidity_2m": 68,
    "precipitation": 0.0,
    "weather_code": 2,
    "wind_speed_10m": 11.5
  },
  "hourly": {
    "time": ["2026-04-27T00:00", "2026-04-27T01:00", "..."],
    "temperature_2m": [16.1, 15.8, null, "..."],
    "relative_humidity_2m": [82, 84, null, "..."],
    "precipitation_probability": [10, 12, null, "..."]
  },
  "daily": {
    "time": ["2026-04-27", "2026-04-28", "2026-04-29", "2026-04-30", "2026-05-01", "2026-05-02", "2026-05-03"],
    "temperature_2m_max": [24.1, 23.8, 25.0, 24.5, 23.9, 25.2, 24.8],
    "temperature_2m_min": [13.2, 12.9, 13.5, 13.0, 12.8, 13.6, 13.4],
    "precipitation_sum": [0.0, 2.4, 0.0, 1.1, 0.0, 0.0, 3.2],
    "et0_fao_evapotranspiration": [4.2, 4.5, 4.8, 4.6, 4.4, 4.9, 4.7],
    "uv_index_max": [10.5, 11.0, 10.8, 10.2, 11.2, 10.9, 10.6]
  },
  "interpretation": "Clima actual: 22.4°C, 68% humedad, viento 11.5 km/h. Próximos 7 días: max 24.5°C / min 13.2°C, lluvia acumulada 6.7 mm, ET₀ 32.1 mm."
}
```

### Fields

| Field                                 | Type            | Description                                  |
| ------------------------------------- | --------------- | -------------------------------------------- |
| `current.temperature_2m`              | float (°C)      | Temperature at 2 m                           |
| `current.relative_humidity_2m`        | int (%)         | Relative humidity                            |
| `current.precipitation`               | float (mm)      | Last-hour precipitation                      |
| `current.weather_code`                | int             | WMO weather code                             |
| `current.wind_speed_10m`              | float (km/h)    | Wind at 10 m                                 |
| `hourly.*`                            | array (168)     | Hourly forecast for 7 days                   |
| `daily.temperature_2m_max/min`        | array (7) °C    | Daily max/min temperature                    |
| `daily.precipitation_sum`             | array (7) mm    | Daily total rainfall                         |
| `daily.et0_fao_evapotranspiration`    | array (7) mm    | FAO ET₀ — key input for irrigation risk      |
| `daily.uv_index_max`                  | array (7)       | Daily max UV index                           |
| `interpretation`                      | string          | Spanish summary ready for Gemma              |

### Errors

| Status | Cause                                              |
| ------ | -------------------------------------------------- |
| 422    | `lat`/`lon` missing or out of range                |
| 502    | Open-Meteo down or timed out                       |

## Tool definition (function calling)

```json
{
  "name": "weather",
  "description": "Clima actual + pronóstico horario y diario (7 días) desde Open-Meteo. Cacheado en Redis por 15 minutos por coordenada.",
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
- HTTP provider: [`providers/openmeteo/weather_provider.py`](../../providers/openmeteo/weather_provider.py)
- Redis cache: [`providers/redis/weather_cache.py`](../../providers/redis/weather_cache.py)
