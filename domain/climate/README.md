# `/climate/history` — Histórico climático desde 1981

Tier 🟠 4 · Fuente: [NASA POWER](https://power.larc.nasa.gov/) (community `AG`) · Cache Redis 7 días.

← [Volver al README principal](../../README.md)

Para preguntas tipo *"¿llovió más este año que el promedio?"*, *"¿este año es más cálido que lo normal?"*. Datos globales desde 1981.

## Endpoint

```
GET /climate/history?lat=<float>&lon=<float>&start=<YYYY-MM-DD>&end=<YYYY-MM-DD>&granularity=<monthly|daily>
```

## Input

| Parámetro     | Tipo   | Requerido | Descripción                                                          | Ejemplo        |
| ------------- | ------ | --------- | -------------------------------------------------------------------- | -------------- |
| `lat`         | float  | sí        | `[-90, 90]`                                                          | `14.5586`      |
| `lon`         | float  | sí        | `[-180, 180]`                                                        | `-90.7295`     |
| `start`       | string | sí        | Fecha inicial `YYYY-MM-DD`                                           | `"2020-01-01"` |
| `end`         | string | sí        | Fecha final `YYYY-MM-DD` (debe ser ≥ `start`)                        | `"2023-12-31"` |
| `granularity` | enum   | no        | `monthly` (default, recomendado) o `daily` (máx. 366 días por call)  | `"monthly"`    |

### Request

```bash
curl "http://localhost:8000/climate/history?lat=14.5586&lon=-90.7295&start=2020-01-01&end=2023-12-31&granularity=monthly"
```

```http
GET http://localhost:8000/climate/history?lat=14.5586&lon=-90.7295&start=2020-01-01&end=2023-12-31&granularity=monthly
Accept: application/json
```

## Output

### 200 OK

```json
{
  "lat": 14.5586,
  "lon": -90.7295,
  "granularity": "monthly",
  "start": "2020-01-01",
  "end": "2023-12-31",
  "series": [
    {
      "date": "2020-01",
      "t2m": 16.2,
      "t2m_max": 22.1,
      "t2m_min": 9.8,
      "precipitation_mm": 4.1,
      "rh_pct": 71,
      "solar_mj_m2": 540.2
    },
    {
      "date": "2020-02",
      "t2m": 17.0,
      "t2m_max": 23.4,
      "t2m_min": 10.5,
      "precipitation_mm": 2.8,
      "rh_pct": 68,
      "solar_mj_m2": 562.1
    }
  ],
  "interpretation": "Histórico mensual de 2020-01-01 a 2023-12-31 (48 puntos). T° media 17.4°C. Precipitación total 4892 mm; periodo más lluvioso: 2022-06 (312 mm)."
}
```

### Campos

| Campo                       | Tipo                | Descripción                                                                |
| --------------------------- | ------------------- | -------------------------------------------------------------------------- |
| `granularity`               | enum                | Granularidad eco                                                           |
| `start`, `end`              | string              | Rango eco                                                                  |
| `series[]`                  | array               | Serie temporal                                                             |
| `series[].date`             | string              | `YYYY-MM-DD` (daily) o `YYYY-MM` (monthly)                                 |
| `series[].t2m`              | float \| null (°C)  | T° media a 2 m                                                             |
| `series[].t2m_max`          | float \| null (°C)  | T° máxima a 2 m                                                            |
| `series[].t2m_min`          | float \| null (°C)  | T° mínima a 2 m                                                            |
| `series[].precipitation_mm` | float \| null (mm)  | Precipitación                                                              |
| `series[].rh_pct`           | float \| null (%)   | Humedad relativa a 2 m                                                     |
| `series[].solar_mj_m2`      | float \| null       | Radiación solar (MJ/m²/día en daily, MJ/m²/mes en monthly)                 |
| `interpretation`            | string              | Resumen agregado en español (T° media, precipitación total, periodo más lluvioso) |

> Los `null` aparecen cuando POWER no tiene dato en ese punto (sentinela `-999` ya filtrado).

### Errores

| Status | Causa                                              |
| ------ | -------------------------------------------------- |
| 422    | Fechas mal formadas, `end < start`, o rango > 366 días en `daily` |
| 404    | Sin datos para los parámetros                      |
| 502    | NASA POWER caído o timeout                         |

## Tool definition (function calling)

```json
{
  "name": "climate_history",
  "description": "Histórico climático desde 1981 (NASA POWER, community AG): T°, precipitación, humedad, radiación solar. Granularidad mensual (recomendada) o diaria.",
  "parameters": {
    "type": "object",
    "properties": {
      "lat":   { "type": "number", "minimum": -90,  "maximum": 90,  "description": "Latitud" },
      "lon":   { "type": "number", "minimum": -180, "maximum": 180, "description": "Longitud" },
      "start": { "type": "string", "description": "Fecha inicial YYYY-MM-DD" },
      "end":   { "type": "string", "description": "Fecha final YYYY-MM-DD (debe ser >= start)" },
      "granularity": {
        "type": "string",
        "enum": ["monthly", "daily"],
        "description": "monthly (default, ergonómico para LLM) o daily (máx. 366 días por request)"
      }
    },
    "required": ["lat", "lon", "start", "end"]
  }
}
```

## Implementación

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py)
- Schema: [`schema.py`](schema.py)
- Provider HTTP: [`providers/nasapower/climate_provider.py`](../../providers/nasapower/climate_provider.py)
- Cache Redis: [`providers/redis/climate_cache.py`](../../providers/redis/climate_cache.py)
