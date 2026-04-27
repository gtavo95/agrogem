# `/frost-risk` — 7-day frost risk

Tier 🟢 1 · Derived from `/weather` + `/elevation` · No own cache (reuses weather/elevation cache).

← [Back to main README](../../README.md)

Combines the hourly forecast with elevation correction (`-6.5 °C/km`). Especially relevant for Andean highlands and high plateaus.

## Endpoint

```
GET /frost-risk?lat=<float>&lon=<float>
```

## Input

| Parameter | Type  | Required | Range          | Description | Example  |
| --------- | ----- | -------- | -------------- | ----------- | -------- |
| `lat`     | float | yes      | `[-90, 90]`    | Latitude    | `-0.6`   |
| `lon`     | float | yes      | `[-180, 180]`  | Longitude   | `-78.5`  |

### Request

```bash
curl "http://localhost:8000/frost-risk?lat=-0.6&lon=-78.5"
```

```http
GET http://localhost:8000/frost-risk?lat=-0.6&lon=-78.5
Accept: application/json
```

## Output

### 200 OK

```json
{
  "lat": -0.6,
  "lon": -78.5,
  "elevation_m": 3120.0,
  "risk_score": 0.62,
  "risk_level": "high",
  "factors": {
    "window_days": 7,
    "min_temp_c": -1.2,
    "frost_hours": 3,
    "freezing_probability_pct": 18.5,
    "altitude_correction_c": -1.4,
    "rule_notes": [
      "3 horas con T° < 0°C en la ventana",
      "elevación 3120 m → corrección -1.4°C"
    ]
  },
  "interpretation": "Riesgo alto de helada los próximos 7 días. Mínima esperada -1.2°C; 3 horas bajo cero. Cubre cultivos sensibles."
}
```

### Fields

| Field                              | Type        | Description                                       |
| ---------------------------------- | ----------- | ------------------------------------------------- |
| `elevation_m`                      | float (m)   | Elevation used for the correction                 |
| `risk_score`                       | float       | Index 0.0–1.0                                     |
| `risk_level`                       | enum        | `low` / `moderate` / `high` / `very_high`         |
| `factors.window_days`              | int         | Days evaluated                                    |
| `factors.min_temp_c`               | float (°C)  | Forecast minimum temperature                      |
| `factors.frost_hours`              | int         | Hours below 0 °C                                  |
| `factors.freezing_probability_pct` | float (%)   | Frost probability                                 |
| `factors.altitude_correction_c`    | float (°C)  | Correction applied                                |
| `factors.rule_notes`               | string[]    | Detected factors, in Spanish                      |
| `interpretation`                   | string      | Spanish summary for Gemma                         |

### Errors

| Status | Cause                                              |
| ------ | -------------------------------------------------- |
| 422    | `lat`/`lon` out of range                           |
| 502    | Weather/elevation provider down                    |

## Tool definition (function calling)

```json
{
  "name": "frost_risk",
  "description": "Índice de riesgo de helada (0.0-1.0) para los próximos 7 días. Combina forecast hourly + corrección por elevación (-6.5°C/km). Especialmente relevante para Sierra andina.",
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
- Composition: depends on `domain/weather` + `domain/elevation`
