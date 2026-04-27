# `/soil` — Soil profile 0–30 cm

Tier 🟢 1 · Source: [ISRIC SoilGrids v2.0](https://www.isric.org/explore/soilgrids) · Redis cache 90 days · No API key.

← [Back to main README](../../README.md)

## Endpoint

```
GET /soil?lat=<float>&lon=<float>
```

## Input

| Parameter | Type  | Required | Range          | Description | Example   |
| --------- | ----- | -------- | -------------- | ----------- | --------- |
| `lat`     | float | yes      | `[-90, 90]`    | Latitude    | `14.5586` |
| `lon`     | float | yes      | `[-180, 180]`  | Longitude   | `-90.7295`|

### Request

```bash
curl "http://localhost:8000/soil?lat=14.5586&lon=-90.7295"
```

```http
GET http://localhost:8000/soil?lat=14.5586&lon=-90.7295
Accept: application/json
```

## Output

### 200 OK

```json
{
  "lat": 14.5586,
  "lon": -90.7295,
  "horizons": [
    {
      "depth": "0-5cm",
      "ph": 6.2,
      "soc_g_per_kg": 12.4,
      "nitrogen_g_per_kg": 1.1,
      "clay_pct": 28,
      "sand_pct": 35,
      "silt_pct": 37,
      "cec_mmol_per_kg": 185,
      "texture_class": "clay loam"
    },
    {
      "depth": "5-15cm",
      "ph": 6.0,
      "soc_g_per_kg": 9.1,
      "nitrogen_g_per_kg": 0.8,
      "clay_pct": 30,
      "sand_pct": 33,
      "silt_pct": 37,
      "cec_mmol_per_kg": 178,
      "texture_class": "clay loam"
    },
    {
      "depth": "15-30cm",
      "ph": 5.9,
      "soc_g_per_kg": 6.7,
      "nitrogen_g_per_kg": 0.6,
      "clay_pct": 32,
      "sand_pct": 30,
      "silt_pct": 38,
      "cec_mmol_per_kg": 170,
      "texture_class": "clay loam"
    }
  ],
  "dominant_texture": "clay loam",
  "interpretation": "Horizonte superficial (0-5 cm): ligeramente ácido (pH 6.2); materia orgánica moderada (SOC 12.4 g/kg); textura clay loam."
}
```

### Fields

| Field                              | Type               | Description                                |
| ---------------------------------- | ------------------ | ------------------------------------------ |
| `horizons[]`                       | array (3)          | Horizons `0-5cm`, `5-15cm`, `15-30cm`      |
| `horizons[].depth`                 | string             | Depth range                                |
| `horizons[].ph`                    | float (pH)         | pH in H₂O                                  |
| `horizons[].soc_g_per_kg`          | float (g/kg)       | Soil organic carbon                        |
| `horizons[].nitrogen_g_per_kg`     | float (g/kg)       | Total nitrogen                             |
| `horizons[].clay_pct`              | float (%)          | Clay                                       |
| `horizons[].sand_pct`              | float (%)          | Sand                                       |
| `horizons[].silt_pct`              | float (%)          | Silt                                       |
| `horizons[].cec_mmol_per_kg`       | float (mmol(c)/kg) | Cation exchange capacity                   |
| `horizons[].texture_class`         | string             | Derived USDA class                         |
| `dominant_texture`                 | string             | Texture of the 0-5 cm horizon              |
| `interpretation`                   | string             | Spanish agronomic summary for Gemma        |

### Errors

| Status | Cause                                                                     |
| ------ | ------------------------------------------------------------------------- |
| 404    | No coverage (ocean, water bodies, extreme latitudes)                      |
| 422    | `lat`/`lon` out of range                                                  |
| 502    | ISRIC SoilGrids down or timed out                                         |

## Tool definition (function calling)

```json
{
  "name": "soil",
  "description": "Perfil de suelo en zona radicular (0-5, 5-15, 15-30 cm) desde ISRIC SoilGrids: pH, SOC, N, textura USDA, CEC. Cacheado 90 días.",
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
- HTTP provider: [`providers/soilgrids/soil_provider.py`](../../providers/soilgrids/soil_provider.py)
- Redis cache: [`providers/redis/soil_cache.py`](../../providers/redis/soil_cache.py)
