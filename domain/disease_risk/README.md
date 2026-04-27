# `/disease-risk` — 7-day phytopathological disease risk

Tier 🟠 4 · Derived from `/weather` · No own cache (reuses weather cache, 15 min).

← [Back to main README](../../README.md)

Combines the hourly forecast (mean temperature, relative humidity, rainy days) with disease-specific agronomic thresholds. Covers **~50 diseases** across grains, vegetables, fruit trees, ornamentals, cocoa, coffee and banana.

## Endpoint

```
GET /disease-risk?lat=<float>&lon=<float>&disease=<enum>
```

## Input

| Parameter | Type  | Required | Description                  | Example         |
| --------- | ----- | -------- | ---------------------------- | --------------- |
| `lat`     | float | yes      | `[-90, 90]`                  | `14.5586`       |
| `lon`     | float | yes      | `[-180, 180]`                | `-90.7295`      |
| `disease` | enum  | yes      | One of the ~50 diseases      | `"coffee_rust"` |

### `disease` enum (50 values)

```
coffee_rust · late_blight · corn_rust · wheat_leaf_rust · wheat_yellow_rust · wheat_stem_rust ·
sugarbeet_cercospora · sugarbeet_rust · barley_rust · rice_blast · rice_brown_spot ·
rice_sheath_blight · rice_bacterial_leaf_blight · tomato_early_blight · tomato_late_blight ·
tomato_fusarium_wilt · potato_late_blight · potato_early_blight · bean_rust ·
bean_angular_leaf_spot · bean_anthracnose · banana_black_sigatoka · banana_fusarium_wilt ·
cardamom_rot · sugarcane_rust · sugarcane_smut · sugarcane_red_rot · rose_botrytis ·
rose_powdery_mildew · rose_downy_mildew · rose_black_spot · cacao_monilia · cacao_black_pod ·
cacao_witches_broom · cacao_frosty_pod · banana_moko · banana_cordana_leaf_spot ·
potato_bacterial_wilt · potato_blackleg · oca_downy_mildew · broccoli_downy_mildew ·
broccoli_black_rot · broccoli_alternaria · oil_palm_bud_rot · oil_palm_spear_rot ·
oil_palm_ganoderma · corn_gray_leaf_spot · corn_northern_leaf_blight · corn_stalk_rot ·
coffee_cercospora
```

> 💡 Tip: for function calling, **dynamically inject** only the diseases relevant to the user's crop into the tool's `enum`. Keeps the prompt short and focused.

### Request

```bash
curl "http://localhost:8000/disease-risk?lat=14.5586&lon=-90.7295&disease=coffee_rust"
```

```http
GET http://localhost:8000/disease-risk?lat=14.5586&lon=-90.7295&disease=coffee_rust
Accept: application/json
```

## Output

### 200 OK

```json
{
  "disease": "coffee_rust",
  "lat": 14.5586,
  "lon": -90.7295,
  "risk_score": 0.72,
  "risk_level": "high",
  "factors": {
    "window_days": 7,
    "avg_temp_c": 22.4,
    "avg_humidity_pct": 84,
    "rainy_days": 4,
    "rule_notes": [
      "T° media 22.4°C en rango óptimo [21-25°C]",
      "humedad relativa 84% ≥ 80%",
      "4 días lluviosos (umbral 3)"
    ]
  },
  "interpretation": "Riesgo alto de roya del café (Hemileia vastatrix) en los próximos 7 días. Factores: T° media 22.4°C en rango óptimo [21-25°C]; humedad relativa 84% ≥ 80%; 4 días lluviosos."
}
```

### Fields

| Field                       | Type            | Description                                       |
| --------------------------- | --------------- | ------------------------------------------------- |
| `disease`                   | enum            | Queried disease                                   |
| `risk_score`                | float (0–1)     | Composite index                                   |
| `risk_level`                | enum            | `low` / `moderate` / `high` / `very_high`         |
| `factors.avg_temp_c`        | float \| null   | Mean hourly temperature in the window             |
| `factors.avg_humidity_pct`  | float \| null   | Mean relative humidity                            |
| `factors.rainy_days`        | int             | Days with precipitation ≥ 1 mm                    |
| `factors.rule_notes`        | string[]        | Detected favorable conditions                     |
| `interpretation`            | string          | Spanish summary for Gemma                         |

### Errors

| Status | Cause                                                |
| ------ | ---------------------------------------------------- |
| 422    | Unrecognized `disease` or `lat`/`lon` out of range   |
| 502    | Weather provider down                                |

## Tool definition (function calling)

> For Gemma, trim the `enum` to only the diseases relevant to the user's crop.

```json
{
  "name": "disease_risk",
  "description": "Índice de riesgo de enfermedad (0.0-1.0) para los próximos 7 días. Combina el forecast con reglas agronómicas específicas por enfermedad.",
  "parameters": {
    "type": "object",
    "properties": {
      "lat":     { "type": "number", "minimum": -90,  "maximum": 90,  "description": "Latitud" },
      "lon":     { "type": "number", "minimum": -180, "maximum": 180, "description": "Longitud" },
      "disease": {
        "type": "string",
        "enum": ["coffee_rust", "late_blight", "corn_rust", "tomato_late_blight", "potato_late_blight"],
        "description": "Enfermedad relevante al cultivo en producción"
      }
    },
    "required": ["lat", "lon", "disease"]
  }
}
```

## Implementation

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py) — rules in `_DISEASE_RULES`
- Schema: [`schema.py`](schema.py)
- Composition: depends on `domain/weather`

### Adding a disease

1. Add an entry to `_DISEASE_RULES` in `service.py` (T°, RH and rainy-day thresholds).
2. Extend the `Literal` `DiseaseName` in `schema.py`.
3. Done — the endpoint serves it without any other changes.
