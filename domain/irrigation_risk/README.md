# `/irrigation-risk` — Riesgo de estrés hídrico 7 días

Tier 🟡 3 · Derivado de `/weather` · Sin cache propio (reusa el de weather, 15 min).

← [Volver al README principal](../../README.md)

Combina ET₀ (Hargreaves) con coeficientes Kc por cultivo y forecast de precipitación para estimar el déficit y la cantidad de agua a aplicar.

## Endpoint

```
GET /irrigation-risk?lat=<float>&lon=<float>&crop=<enum>
```

## Input

| Parámetro | Tipo  | Requerido | Valores                                                                                                            | Ejemplo    |
| --------- | ----- | --------- | ------------------------------------------------------------------------------------------------------------------ | ---------- |
| `lat`     | float | sí        | `[-90, 90]`                                                                                                        | `14.6`     |
| `lon`     | float | sí        | `[-180, 180]`                                                                                                      | `-90.5`    |
| `crop`    | enum  | sí        | `corn` · `rice` · `bean` · `wheat` · `coffee` · `sugarcane` · `banana` · `tomato` · `potato` · `onion` · `broccoli` · `rose` | `"potato"` |

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

### Campos

| Campo                                | Tipo         | Descripción                                              |
| ------------------------------------ | ------------ | -------------------------------------------------------- |
| `risk_score`                         | float (0–1)  | Índice compuesto                                         |
| `risk_level`                         | enum         | `low` / `moderate` / `high` / `very_high`                |
| `factors.et0_sum_mm`                 | float (mm)   | ET₀ FAO total en la ventana                              |
| `factors.precipitation_sum_mm`       | float (mm)   | Lluvia forecast total                                    |
| `factors.crop_water_requirement_mm`  | float (mm)   | Demanda hídrica del cultivo (`ET₀ × Kc`)                 |
| `factors.soil_water_deficit_mm`      | float (mm)   | Déficit estimado en suelo                                |
| `factors.rule_notes`                 | string[]     | Factores detectados                                      |
| `irrigation_recommendation_mm`       | float (mm)   | **Mm a aplicar** (campo accionable para el productor)    |
| `interpretation`                     | string       | Resumen para Gemma                                       |

### Errores

| Status | Causa                                              |
| ------ | -------------------------------------------------- |
| 422    | `crop` no reconocido o `lat`/`lon` fuera de rango  |
| 502    | Weather provider caído                             |

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

## Implementación

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py) — coeficientes Kc en `_CROP_KC`
- Schema: [`schema.py`](schema.py)
- Composición: depende de `domain/weather`
