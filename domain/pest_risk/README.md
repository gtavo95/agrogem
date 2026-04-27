# `/pest-risk` — 7-day pest risk

Tier 🟡 3 · Derived from `/weather` · No own cache (reuses weather cache, 15 min).

← [Back to main README](../../README.md)

Unlike fungal diseases, pests respond to temperature (growing-degree days) and inverse humidity (spider mites and thrips thrive in dry conditions).

## Endpoint

```
GET /pest-risk?lat=<float>&lon=<float>&pest=<enum>
```

## Input

| Parameter | Type  | Required | Values                                                                                                                                                  | Example            |
| --------- | ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `lat`     | float | yes      | `[-90, 90]`                                                                                                                                             | `14.66`            |
| `lon`     | float | yes      | `[-180, 180]`                                                                                                                                           | `-90.82`           |
| `pest`    | enum  | yes      | `spider_mite` · `whitefly` · `broad_mite` · `white_grub` · `thrips` · `leafminer` · `fall_armyworm` · `root_knot_nematode` · `coffee_berry_borer`       | `"fall_armyworm"`  |

### Request

```bash
curl "http://localhost:8000/pest-risk?lat=14.66&lon=-90.82&pest=fall_armyworm"
```

```http
GET http://localhost:8000/pest-risk?lat=14.66&lon=-90.82&pest=fall_armyworm
Accept: application/json
```

## Output

### 200 OK

```json
{
  "pest": "fall_armyworm",
  "pest_type": "insect",
  "life_stage_risk": "larva",
  "affected_crops": ["corn", "sorghum", "sugarcane", "rice", "bean"],
  "lat": 14.66,
  "lon": -90.82,
  "risk_score": 0.74,
  "risk_level": "high",
  "factors": {
    "window_days": 7,
    "avg_temp_c": 24.8,
    "avg_humidity_pct": 72,
    "rainy_days": 2,
    "rule_notes": [
      "T° media 24.8°C óptima para desarrollo larval",
      "2 días lluviosos en la ventana"
    ]
  },
  "virus_coalert": null,
  "interpretation": "Riesgo alto de gusano cogollero (Spodoptera frugiperda) en los próximos 7 días. Temperatura media 24.8°C ideal para desarrollo larval; cultivos afectados: corn, sorghum, sugarcane."
}
```

### Fields

| Field                        | Type            | Description                                                                  |
| ---------------------------- | --------------- | ---------------------------------------------------------------------------- |
| `pest`                       | enum            | Queried pest                                                                 |
| `pest_type`                  | enum            | `mite` / `insect` / `nematode`                                               |
| `life_stage_risk`            | enum            | `larva` / `adult` / `both`                                                   |
| `affected_crops`             | string[]        | Crops susceptible to this pest                                               |
| `risk_score`                 | float (0–1)     | Composite index                                                              |
| `risk_level`                 | enum            | `low` / `moderate` / `high` / `very_high`                                    |
| `factors.window_days`        | int             | Days evaluated                                                               |
| `factors.avg_temp_c`         | float \| null   | Mean hourly temperature in the window                                        |
| `factors.avg_humidity_pct`   | float \| null   | Mean relative humidity                                                       |
| `factors.rainy_days`         | int             | Days with precipitation ≥ 1 mm                                               |
| `factors.rule_notes`         | string[]        | Detected favorable conditions                                                |
| `virus_coalert`              | string \| null  | Associated virus alert (e.g. BGMV in beans when whitefly risk is high)       |
| `interpretation`             | string          | Spanish summary ready for Gemma                                              |

### Errors

| Status | Cause                                              |
| ------ | -------------------------------------------------- |
| 422    | Unrecognized `pest` or `lat`/`lon` out of range    |
| 502    | Weather provider down                              |

## Tool definition (function calling)

```json
{
  "name": "pest_risk",
  "description": "Índice de riesgo de plaga (0.0-1.0) para los próximos 7 días. Las plagas responden a temperatura (grados-día) e inversa humedad (spider mite, thrips prosperan en sequedad). Reusa el cache del weather.",
  "parameters": {
    "type": "object",
    "properties": {
      "lat":  { "type": "number", "minimum": -90,  "maximum": 90,  "description": "Latitud" },
      "lon":  { "type": "number", "minimum": -180, "maximum": 180, "description": "Longitud" },
      "pest": {
        "type": "string",
        "enum": ["spider_mite", "whitefly", "broad_mite", "white_grub", "thrips",
                 "leafminer", "fall_armyworm", "root_knot_nematode", "coffee_berry_borer"],
        "description": "Plaga a evaluar"
      }
    },
    "required": ["lat", "lon", "pest"]
  }
}
```

## Implementation

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py) — rules in `_PEST_RULES`
- Schema: [`schema.py`](schema.py)
- Composition: depends on `domain/weather`
