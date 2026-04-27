# `/harvest-window` — 7-day optimal harvest window

Tier 🟡 3 · Derived from `/weather` · No own cache (reuses weather cache, 15 min).

← [Back to main README](../../README.md)

Evaluates mean temperature, relative humidity, rainfall and dry spells to identify the best harvest days (grain/fruit quality and field drying).

## Endpoint

```
GET /harvest-window?lat=<float>&lon=<float>&crop=<enum>
```

## Input

| Parameter | Type  | Required | Values                                                                                                                              | Example    |
| --------- | ----- | -------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `lat`     | float | yes      | `[-90, 90]`                                                                                                                         | `14.6`     |
| `lon`     | float | yes      | `[-180, 180]`                                                                                                                       | `-90.5`    |
| `crop`    | enum  | yes      | `corn` · `rice` · `bean` · `wheat` · `coffee` · `sugarcane` · `banana` · `tomato` · `potato` · `onion` · `broccoli` · `rose` · `strawberry` | `"coffee"` |

### Request

```bash
curl "http://localhost:8000/harvest-window?lat=14.6&lon=-90.5&crop=coffee"
```

```http
GET http://localhost:8000/harvest-window?lat=14.6&lon=-90.5&crop=coffee
Accept: application/json
```

## Output

### 200 OK

```json
{
  "crop": "coffee",
  "lat": 14.6,
  "lon": -90.5,
  "window_score": 0.81,
  "window_level": "high",
  "factors": {
    "window_days": 7,
    "avg_temp_c": 21.5,
    "avg_humidity_pct": 65,
    "rainy_days": 1,
    "dry_spells": 4,
    "rule_notes": [
      "4 días secos consecutivos óptimos para secado en patio",
      "Humedad relativa media 65% favorable"
    ]
  },
  "optimal_dates": ["2026-04-29", "2026-04-30", "2026-05-01"],
  "warning": null,
  "interpretation": "Ventana óptima para cosechar café entre el 29 abr y el 1 may: 4 días secos consecutivos, T° media 21.5°C, humedad 65%."
}
```

### Fields

| Field                       | Type            | Description                                       |
| --------------------------- | --------------- | ------------------------------------------------- |
| `window_score`              | float (0–1)     | Index (1 = optimal)                               |
| `window_level`              | enum            | `low` / `moderate` / `high` / `very_high`         |
| `factors.avg_temp_c`        | float \| null   | Mean temperature in the window                    |
| `factors.avg_humidity_pct`  | float \| null   | Mean relative humidity                            |
| `factors.rainy_days`        | int             | Days with precipitation                           |
| `factors.dry_spells`        | int             | Consecutive dry days                              |
| `factors.rule_notes`        | string[]        | Detected factors                                  |
| `optimal_dates`             | string[]        | Suggested dates (`YYYY-MM-DD`)                    |
| `warning`                   | string \| null  | Warning if conditions are not ideal               |
| `interpretation`            | string          | Spanish summary for Gemma                         |

### Errors

| Status | Cause                                              |
| ------ | -------------------------------------------------- |
| 422    | Unrecognized `crop` or `lat`/`lon` out of range    |
| 502    | Weather provider down                              |

## Tool definition (function calling)

```json
{
  "name": "harvest_window",
  "description": "Índice de ventana óptima para cosecha (0.0-1.0). Combina forecast de temperatura, humedad y precipitación. Evalúa condiciones para secado en campo y calidad de grano/fruto.",
  "parameters": {
    "type": "object",
    "properties": {
      "lat":  { "type": "number", "minimum": -90,  "maximum": 90,  "description": "Latitud" },
      "lon":  { "type": "number", "minimum": -180, "maximum": 180, "description": "Longitud" },
      "crop": {
        "type": "string",
        "enum": ["corn", "rice", "bean", "wheat", "coffee", "sugarcane", "banana",
                 "tomato", "potato", "onion", "broccoli", "rose", "strawberry"],
        "description": "Cultivo a cosechar"
      }
    },
    "required": ["lat", "lon", "crop"]
  }
}
```

## Implementation

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py) — rules in `_HARVEST_RULES`
- Schema: [`schema.py`](schema.py)
- Composition: depends on `domain/weather`
