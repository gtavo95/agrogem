# `/pest-risk` — Riesgo de plaga 7 días

Tier 🟡 3 · Derivado de `/weather` · Sin cache propio (reusa el de weather, 15 min).

← [Volver al README principal](../../README.md)

A diferencia de las enfermedades fungales, las plagas responden a temperatura (grados-día) e inversa-humedad (spider mite, thrips prosperan en sequedad).

## Endpoint

```
GET /pest-risk?lat=<float>&lon=<float>&pest=<enum>
```

## Input

| Parámetro | Tipo  | Requerido | Valores                                                                                                                          | Ejemplo            |
| --------- | ----- | --------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `lat`     | float | sí        | `[-90, 90]`                                                                                                                      | `14.66`            |
| `lon`     | float | sí        | `[-180, 180]`                                                                                                                    | `-90.82`           |
| `pest`    | enum  | sí        | `spider_mite` · `whitefly` · `broad_mite` · `white_grub` · `thrips` · `leafminer` · `fall_armyworm` · `root_knot_nematode` · `coffee_berry_borer` | `"fall_armyworm"`  |

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

### Campos

| Campo                        | Tipo            | Descripción                                                                  |
| ---------------------------- | --------------- | ---------------------------------------------------------------------------- |
| `pest`                       | enum            | Plaga consultada                                                             |
| `pest_type`                  | enum            | `mite` / `insect` / `nematode`                                               |
| `life_stage_risk`            | enum            | `larva` / `adult` / `both`                                                   |
| `affected_crops`             | string[]        | Cultivos sensibles a esta plaga                                              |
| `risk_score`                 | float (0–1)     | Índice compuesto                                                             |
| `risk_level`                 | enum            | `low` / `moderate` / `high` / `very_high`                                    |
| `factors.window_days`        | int             | Días evaluados                                                               |
| `factors.avg_temp_c`         | float \| null   | T° media horaria de la ventana                                               |
| `factors.avg_humidity_pct`   | float \| null   | Humedad relativa media                                                       |
| `factors.rainy_days`         | int             | Días con precipitación ≥ 1 mm                                                |
| `factors.rule_notes`         | string[]        | Condiciones favorables detectadas                                            |
| `virus_coalert`              | string \| null  | Alerta de virus asociado (ej: BGMV en frijol cuando hay whitefly alto)       |
| `interpretation`             | string          | Resumen en español listo para Gemma                                          |

### Errores

| Status | Causa                                              |
| ------ | -------------------------------------------------- |
| 422    | `pest` no reconocida o `lat`/`lon` fuera de rango  |
| 502    | Weather provider caído                             |

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

## Implementación

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py) — reglas en `_PEST_RULES`
- Schema: [`schema.py`](schema.py)
- Composición: depende de `domain/weather`
