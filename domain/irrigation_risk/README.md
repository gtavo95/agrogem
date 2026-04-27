# `/irrigation-risk` — 7-day water stress risk

Tier 🟡 3 · Derived from `/weather` · No own cache (reuses weather cache, 15 min).

← [Back to main README](../../README.md)

Combines Hargreaves ET₀ with crop Kc coefficients and the rainfall forecast to estimate the deficit and the amount of water to apply.

## Endpoint

```
GET /irrigation-risk?lat=<float>&lon=<float>&crop=<enum>
```

## Input

| Parameter | Type  | Required | Values                                                                                                                | Example    |
| --------- | ----- | -------- | --------------------------------------------------------------------------------------------------------------------- | ---------- |
| `lat`     | float | yes      | `[-90, 90]`                                                                                                           | `14.6`     |
| `lon`     | float | yes      | `[-180, 180]`                                                                                                         | `-90.5`    |
| `crop`    | enum  | yes      | `corn` · `rice` · `bean` · `wheat` · `coffee` · `sugarcane` · `banana` · `tomato` · `potato` · `onion` · `broccoli` · `rose` | `"potato"` |

### Request

```bash
curl "http://localhost:8000/irrigation-risk?lat=14.6&lon=-90.5&crop=potato"
```

```http
GET http://localhost:8000/irrigation-risk?lat=14.6&lon=-90.5&crop=potato
Accept: application/json
```

## Output

### 200 OK

```json
{
  "crop": "potato",
  "lat": 14.6,
  "lon": -90.5,
  "risk_score": 0.58,
  "risk_level": "moderate",
  "factors": {
    "window_days": 7,
    "et0_sum_mm": 32.4,
    "precipitation_sum_mm": 8.2,
    "crop_water_requirement_mm": 35.6,
    "soil_water_deficit_mm": 27.4,
    "rule_notes": [
      "Déficit hídrico 27.4 mm en 7 días",
      "Lluvia forecast 8.2 mm insuficiente"
    ]
  },
  "irrigation_recommendation_mm": 27.4,
  "interpretation": "Riesgo moderado de estrés hídrico para papa los próximos 7 días. Déficit estimado 27 mm — aplicar ~27 mm de riego distribuido."
}
```

### Fields

| Field                                | Type         | Description                                              |
| ------------------------------------ | ------------ | -------------------------------------------------------- |
| `risk_score`                         | float (0–1)  | Composite index                                          |
| `risk_level`                         | enum         | `low` / `moderate` / `high` / `very_high`                |
| `factors.et0_sum_mm`                 | float (mm)   | Total FAO ET₀ in the window                              |
| `factors.precipitation_sum_mm`       | float (mm)   | Forecast total rainfall                                  |
| `factors.crop_water_requirement_mm`  | float (mm)   | Crop water demand (`ET₀ × Kc`)                           |
| `factors.soil_water_deficit_mm`      | float (mm)   | Estimated soil deficit                                   |
| `factors.rule_notes`                 | string[]     | Detected factors                                         |
| `irrigation_recommendation_mm`       | float (mm)   | **Mm to apply** (actionable field for the farmer)        |
| `interpretation`                     | string       | Spanish summary for Gemma                                |

### Errors

| Status | Cause                                              |
| ------ | -------------------------------------------------- |
| 422    | Unrecognized `crop` or `lat`/`lon` out of range    |
| 502    | Weather provider down                              |

## Tool definition (function calling)

```json
{
  "name": "irrigation_risk",
  "description": "Índice de riesgo de estrés hídrico (0.0-1.0) para los próximos 7 días. Combina ET0 (Hargreaves) con forecast de precipitación y coeficientes Kc del cultivo. Devuelve mm de riego recomendados.",
  "parameters": {
    "type": "object",
    "properties": {
      "lat":  { "type": "number", "minimum": -90,  "maximum": 90,  "description": "Latitud" },
      "lon":  { "type": "number", "minimum": -180, "maximum": 180, "description": "Longitud" },
      "crop": {
        "type": "string",
        "enum": ["corn", "rice", "bean", "wheat", "coffee", "sugarcane", "banana",
                 "tomato", "potato", "onion", "broccoli", "rose"],
        "description": "Cultivo en producción"
      }
    },
    "required": ["lat", "lon", "crop"]
  }
}
```

## Implementation

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py) — Kc coefficients in `_CROP_KC`
- Schema: [`schema.py`](schema.py)
- Composition: depends on `domain/weather`
