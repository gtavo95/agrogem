# `/soil` — Perfil de suelo 0–30 cm

Tier 🟢 1 · Fuente: [ISRIC SoilGrids v2.0](https://www.isric.org/explore/soilgrids) · Cache Redis 90 días · Sin API key.

← [Volver al README principal](../../README.md)

## Endpoint

```
GET /soil?lat=<float>&lon=<float>
```

## Input

| Parámetro | Tipo  | Requerido | Rango          | Descripción | Ejemplo  |
| --------- | ----- | --------- | -------------- | ----------- | -------- |
| `lat`     | float | sí        | `[-90, 90]`    | Latitud     | `14.5586`|
| `lon`     | float | sí        | `[-180, 180]`  | Longitud    | `-90.7295`|

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

### Campos

| Campo                              | Tipo               | Descripción                                |
| ---------------------------------- | ------------------ | ------------------------------------------ |
| `horizons[]`                       | array (3)          | Horizontes `0-5cm`, `5-15cm`, `15-30cm`    |
| `horizons[].depth`                 | string             | Rango de profundidad                       |
| `horizons[].ph`                    | float (pH)         | pH en H₂O                                  |
| `horizons[].soc_g_per_kg`          | float (g/kg)       | Carbono orgánico                           |
| `horizons[].nitrogen_g_per_kg`     | float (g/kg)       | Nitrógeno total                            |
| `horizons[].clay_pct`              | float (%)          | Arcilla                                    |
| `horizons[].sand_pct`              | float (%)          | Arena                                      |
| `horizons[].silt_pct`              | float (%)          | Limo                                       |
| `horizons[].cec_mmol_per_kg`       | float (mmol(c)/kg) | Capacidad de intercambio catiónico         |
| `horizons[].texture_class`         | string             | Clase USDA derivada                        |
| `dominant_texture`                 | string             | Textura del horizonte 0-5 cm               |
| `interpretation`                   | string             | Resumen agronómico en español para Gemma   |

### Errores

| Status | Causa                                                                     |
| ------ | ------------------------------------------------------------------------- |
| 404    | Sin cobertura (océano, cuerpos de agua, latitudes extremas)               |
| 422    | `lat`/`lon` fuera de rango                                                |
| 502    | ISRIC SoilGrids caído o timeout                                           |

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

## Implementación

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py)
- Schema: [`schema.py`](schema.py)
- Provider HTTP: [`providers/soilgrids/soil_provider.py`](../../providers/soilgrids/soil_provider.py)
- Cache Redis: [`providers/redis/soil_cache.py`](../../providers/redis/soil_cache.py)
