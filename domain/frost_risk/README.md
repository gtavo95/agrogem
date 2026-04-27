# `/frost-risk` — Riesgo de helada 7 días

Tier 🟢 1 · Derivado de `/weather` + `/elevation` · Sin cache propio (reusa el de weather/elevation).

← [Volver al README principal](../../README.md)

Combina el forecast horario con corrección por elevación (`-6.5 °C/km`). Especialmente relevante para Sierra andina y altiplanos.

## Endpoint

```
GET /frost-risk?lat=<float>&lon=<float>
```

## Input

| Parámetro | Tipo  | Requerido | Rango          | Descripción | Ejemplo  |
| --------- | ----- | --------- | -------------- | ----------- | -------- |
| `lat`     | float | sí        | `[-90, 90]`    | Latitud     | `-0.6`   |
| `lon`     | float | sí        | `[-180, 180]`  | Longitud    | `-78.5`  |

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

### Campos

| Campo                              | Tipo        | Descripción                                       |
| ---------------------------------- | ----------- | ------------------------------------------------- |
| `elevation_m`                      | float (m)   | Elevación usada para la corrección                |
| `risk_score`                       | float       | Índice 0.0–1.0                                    |
| `risk_level`                       | enum        | `low` / `moderate` / `high` / `very_high`         |
| `factors.window_days`              | int         | Días del forecast evaluado                        |
| `factors.min_temp_c`               | float (°C)  | Temperatura mínima forecast                       |
| `factors.frost_hours`              | int         | Horas con T° < 0 °C                               |
| `factors.freezing_probability_pct` | float (%)   | Probabilidad de helada                            |
| `factors.altitude_correction_c`    | float (°C)  | Corrección aplicada                               |
| `factors.rule_notes`               | string[]    | Factores detectados, en español                   |
| `interpretation`                   | string      | Resumen para Gemma                                |

### Errores

| Status | Causa                                              |
| ------ | -------------------------------------------------- |
| 422    | `lat`/`lon` fuera de rango                         |
| 502    | Weather/elevation provider caído                   |

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

## Implementación

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py)
- Schema: [`schema.py`](schema.py)
- Composición: depende de `domain/weather` + `domain/elevation`
