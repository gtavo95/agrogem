# `/elevation` — Altitud m.s.n.m

Tier 🟢 1 · Fuente: [Open-Meteo Elevation](https://open-meteo.com/en/docs/elevation-api) · Cache Redis 365 días · Sin API key.

← [Volver al README principal](../../README.md)

## Endpoint

```
GET /elevation?lat=<float>&lon=<float>
```

## Input

| Parámetro | Tipo  | Requerido | Rango          | Descripción | Ejemplo  |
| --------- | ----- | --------- | -------------- | ----------- | -------- |
| `lat`     | float | sí        | `[-90, 90]`    | Latitud     | `14.5586`|
| `lon`     | float | sí        | `[-180, 180]`  | Longitud    | `-90.7295`|

### Request

```bash
curl "http://localhost:8000/elevation?lat=14.5586&lon=-90.7295"
```

```http
GET http://localhost:8000/elevation?lat=14.5586&lon=-90.7295
Accept: application/json
```

## Output

### 200 OK

```json
{
  "lat": 14.5586,
  "lon": -90.7295,
  "elevation_m": 1530.0,
  "interpretation": "Altitud 1530 m s.n.m (tierra templada / piso cafetero)."
}
```

### Campos

| Campo            | Tipo       | Descripción                                                      |
| ---------------- | ---------- | ---------------------------------------------------------------- |
| `lat`, `lon`     | float      | Coordenadas eco                                                  |
| `elevation_m`    | float (m)  | Altitud sobre el nivel del mar                                   |
| `interpretation` | string     | Resumen en español con clasificación por piso altitudinal        |

### Pisos altitudinales

| Rango (m) | Piso                                |
| --------- | ----------------------------------- |
| `< 800`   | tierra caliente / costa             |
| `< 1800`  | tierra templada / piso cafetero     |
| `< 2800`  | tierra fría / sierra                |
| `< 3500`  | tierra muy fría / altiplano         |
| `≥ 3500`  | páramo / puna alta                  |

### Errores

| Status | Causa                                  |
| ------ | -------------------------------------- |
| 404    | Sin dato para esas coordenadas         |
| 422    | `lat`/`lon` fuera de rango             |
| 502    | Open-Meteo caído o timeout             |

## Tool definition (function calling)

```json
{
  "name": "elevation",
  "description": "Altitud (m.s.n.m) desde Open-Meteo Elevation. Cacheado 365 días (la altitud no cambia).",
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
- Provider HTTP: [`providers/openmeteo/elevation_provider.py`](../../providers/openmeteo/elevation_provider.py)
- Cache Redis: [`providers/redis/elevation_cache.py`](../../providers/redis/elevation_cache.py)
