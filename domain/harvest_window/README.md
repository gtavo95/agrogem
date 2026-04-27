# `/harvest-window` — Ventana óptima de cosecha 7 días

Tier 🟡 3 · Derivado de `/weather` · Sin cache propio (reusa el de weather, 15 min).

← [Volver al README principal](../../README.md)

Evalúa T° media, humedad relativa, lluvia y rachas secas para identificar los mejores días de cosecha (calidad de grano/fruto y secado en campo).

## Endpoint

```
GET /harvest-window?lat=<float>&lon=<float>&crop=<enum>
```

## Input

| Parámetro | Tipo  | Requerido | Valores                                                                                                                              | Ejemplo    |
| --------- | ----- | --------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| `lat`     | float | sí        | `[-90, 90]`                                                                                                                          | `14.6`     |
| `lon`     | float | sí        | `[-180, 180]`                                                                                                                        | `-90.5`    |
| `crop`    | enum  | sí        | `corn` · `rice` · `bean` · `wheat` · `coffee` · `sugarcane` · `banana` · `tomato` · `potato` · `onion` · `broccoli` · `rose` · `strawberry` | `"coffee"` |

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

### Campos

| Campo                       | Tipo            | Descripción                                       |
| --------------------------- | --------------- | ------------------------------------------------- |
| `window_score`              | float (0–1)     | Índice (1 = óptimo)                               |
| `window_level`              | enum            | `low` / `moderate` / `high` / `very_high`         |
| `factors.avg_temp_c`        | float \| null   | T° media de la ventana                            |
| `factors.avg_humidity_pct`  | float \| null   | Humedad relativa media                            |
| `factors.rainy_days`        | int             | Días con precipitación                            |
| `factors.dry_spells`        | int             | Días secos consecutivos                           |
| `factors.rule_notes`        | string[]        | Factores detectados                               |
| `optimal_dates`             | string[]        | Fechas sugeridas (`YYYY-MM-DD`)                   |
| `warning`                   | string \| null  | Aviso si las condiciones no son ideales           |
| `interpretation`            | string          | Resumen para Gemma                                |

### Errores

| Status | Causa                                              |
| ------ | -------------------------------------------------- |
| 422    | `crop` no reconocido o `lat`/`lon` fuera de rango  |
| 502    | Weather provider caído                             |

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

## Implementación

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py) — reglas en `_HARVEST_RULES`
- Schema: [`schema.py`](schema.py)
- Composición: depende de `domain/weather`
