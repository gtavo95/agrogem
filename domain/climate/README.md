# `/climate/history` — Climate history since 1981

Tier 🟠 4 · Source: [NASA POWER](https://power.larc.nasa.gov/) (community `AG`) · Redis cache 7 days.

← [Back to main README](../../README.md)

For questions like *"did it rain more this year than the average?"* or *"is this year warmer than usual?"*. Global data since 1981.

## Endpoint

```
GET /climate/history?lat=<float>&lon=<float>&start=<YYYY-MM-DD>&end=<YYYY-MM-DD>&granularity=<monthly|daily>
```

## Input

| Parameter     | Type   | Required | Description                                                          | Example        |
| ------------- | ------ | -------- | -------------------------------------------------------------------- | -------------- |
| `lat`         | float  | yes      | `[-90, 90]`                                                          | `14.5586`      |
| `lon`         | float  | yes      | `[-180, 180]`                                                        | `-90.7295`     |
| `start`       | string | yes      | Start date `YYYY-MM-DD`                                              | `"2020-01-01"` |
| `end`         | string | yes      | End date `YYYY-MM-DD` (must be ≥ `start`)                            | `"2023-12-31"` |
| `granularity` | enum   | no       | `monthly` (default, recommended) or `daily` (max. 366 days per call) | `"monthly"`    |

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

### Fields

| Field                       | Type                | Description                                                                |
| --------------------------- | ------------------- | -------------------------------------------------------------------------- |
| `granularity`               | enum                | Echoed granularity                                                         |
| `start`, `end`              | string              | Echoed range                                                               |
| `series[]`                  | array               | Time series                                                                |
| `series[].date`             | string              | `YYYY-MM-DD` (daily) or `YYYY-MM` (monthly)                                |
| `series[].t2m`              | float \| null (°C)  | Mean temperature at 2 m                                                    |
| `series[].t2m_max`          | float \| null (°C)  | Max temperature at 2 m                                                     |
| `series[].t2m_min`          | float \| null (°C)  | Min temperature at 2 m                                                     |
| `series[].precipitation_mm` | float \| null (mm)  | Precipitation                                                              |
| `series[].rh_pct`           | float \| null (%)   | Relative humidity at 2 m                                                   |
| `series[].solar_mj_m2`      | float \| null       | Solar radiation (MJ/m²/day in daily, MJ/m²/month in monthly)               |
| `interpretation`            | string              | Spanish aggregated summary (mean T°, total rainfall, wettest period)       |

> `null` values appear when POWER has no data at that point (the `-999` sentinel is already filtered).

### Errors

| Status | Cause                                                |
| ------ | ---------------------------------------------------- |
| 422    | Malformed dates, `end < start`, or range > 366 days in `daily` |
| 404    | No data for those parameters                         |
| 502    | NASA POWER down or timed out                         |

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

## Implementation

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py)
- Schema: [`schema.py`](schema.py)
- HTTP provider: [`providers/nasapower/climate_provider.py`](../../providers/nasapower/climate_provider.py)
- Redis cache: [`providers/redis/climate_cache.py`](../../providers/redis/climate_cache.py)
