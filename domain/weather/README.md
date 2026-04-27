# `/weather` — Clima actual + forecast 7 días

Tier 🟢 1 · Fuente: [Open-Meteo](https://open-meteo.com/) · Cache Redis 15 min · Sin API key.

← [Volver al README principal](../../README.md)

## Endpoint

```
GET /weather?lat=<float>&lon=<float>
```

## Input

| Parámetro | Tipo  | Requerido | Rango          | Descripción | Ejemplo  |
| --------- | ----- | --------- | -------------- | ----------- | -------- |
| `lat`     | float | sí        | `[-90, 90]`    | Latitud     | `14.76`  |
| `lon`     | float | sí        | `[-180, 180]`  | Longitud    | `-90.99` |

### Request

```bash
curl "http://localhost:8000/weather?lat=14.5586&lon=-90.7295"
```

```http
GET http://localhost:8000/weather?lat=14.5586&lon=-90.7295
Accept: application/json
```

## Output

### 200 OK

```json
{
  "latitude": 14.5586,
  "longitude": -90.7295,
  "timezone": "America/Guatemala",
  "current": {
    "time": "2026-04-27T14:00",
    "temperature_2m": 22.4,
    "relative_humidity_2m": 68,
    "precipitation": 0.0,
    "weather_code": 2,
    "wind_speed_10m": 11.5
  },
  "hourly": {
    "time": ["2026-04-27T00:00", "2026-04-27T01:00", "..."],
    "temperature_2m": [16.1, 15.8, null, "..."],
    "relative_humidity_2m": [82, 84, null, "..."],
    "precipitation_probability": [10, 12, null, "..."]
  },
  "daily": {
    "time": ["2026-04-27", "2026-04-28", "2026-04-29", "2026-04-30", "2026-05-01", "2026-05-02", "2026-05-03"],
    "temperature_2m_max": [24.1, 23.8, 25.0, 24.5, 23.9, 25.2, 24.8],
    "temperature_2m_min": [13.2, 12.9, 13.5, 13.0, 12.8, 13.6, 13.4],
    "precipitation_sum": [0.0, 2.4, 0.0, 1.1, 0.0, 0.0, 3.2],
    "et0_fao_evapotranspiration": [4.2, 4.5, 4.8, 4.6, 4.4, 4.9, 4.7],
    "uv_index_max": [10.5, 11.0, 10.8, 10.2, 11.2, 10.9, 10.6]
  },
  "interpretation": "Clima actual: 22.4°C, 68% humedad, viento 11.5 km/h. Próximos 7 días: max 24.5°C / min 13.2°C, lluvia acumulada 6.7 mm, ET₀ 32.1 mm."
}
```

### Campos

| Campo                                 | Tipo            | Descripción                                  |
| ------------------------------------- | --------------- | -------------------------------------------- |
| `current.temperature_2m`              | float (°C)      | Temperatura a 2 m                            |
| `current.relative_humidity_2m`        | int (%)         | Humedad relativa                             |
| `current.precipitation`               | float (mm)      | Precipitación última hora                    |
| `current.weather_code`                | int             | Código WMO de condición                      |
| `current.wind_speed_10m`              | float (km/h)    | Viento a 10 m                                |
| `hourly.*`                            | array (168)     | Forecast horario 7 días                      |
| `daily.temperature_2m_max/min`        | array (7) °C    | T° max/min diaria                            |
| `daily.precipitation_sum`             | array (7) mm    | Lluvia diaria total                          |
| `daily.et0_fao_evapotranspiration`    | array (7) mm    | ET₀ FAO — clave para riesgo de riego         |
| `daily.uv_index_max`                  | array (7)       | UV máximo diario                             |
| `interpretation`                      | string          | Resumen en español listo para Gemma          |

### Errores

| Status | Causa                                              |
| ------ | -------------------------------------------------- |
| 422    | `lat`/`lon` faltante o fuera de rango              |
| 502    | Open-Meteo caído o timeout                         |

## Tool definition (function calling)

```json
{
  "name": "weather",
  "description": "Clima actual + pronóstico horario y diario (7 días) desde Open-Meteo. Cacheado en Redis por 15 minutos por coordenada.",
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
- Provider HTTP: [`providers/openmeteo/weather_provider.py`](../../providers/openmeteo/weather_provider.py)
- Cache Redis: [`providers/redis/weather_cache.py`](../../providers/redis/weather_cache.py)
