# `/geocode` y `/geocode/reverse` — Geocoding

Tier 🟢 2 (forward) · 🟢 1 (reverse) · Fuente: [Nominatim](https://nominatim.org/) (OpenStreetMap) · Cache Redis 30 días.

← [Volver al README principal](../../README.md)

Pensado como **primera tool** del agente: el LLM traduce *"mi finca en Tecpán"* a coordenadas antes de llamar a `/weather`, `/soil`, etc.

---

## `GET /geocode` — Forward (texto → coords)

### Input

| Parámetro | Tipo   | Requerido | Descripción                                     | Ejemplo                |
| --------- | ------ | --------- | ----------------------------------------------- | ---------------------- |
| `q`       | string | sí        | Texto libre, mín. 1 carácter                    | `"Chimaltenango"`      |
| `country` | string | no        | Filtro ISO alpha-2 (reduce ambigüedad)          | `"GT"`                 |

### Request

```bash
curl "http://localhost:8000/geocode?q=Chimaltenango&country=GT"
```

```http
GET http://localhost:8000/geocode?q=Chimaltenango&country=GT
Accept: application/json
```

### Output 200

```json
{
  "lat": 14.6611,
  "lon": -90.8210,
  "display_name": "Chimaltenango, Guatemala",
  "country_code": "gt",
  "state": "Chimaltenango",
  "municipality": "Chimaltenango",
  "type": "administrative",
  "interpretation": "Ubicación encontrada: Chimaltenango, Guatemala (14.6611, -90.8210)."
}
```

### Errores

| Status | Causa                                |
| ------ | ------------------------------------ |
| 404    | Ninguna coincidencia                 |
| 422    | `q` vacío o `country` inválido       |
| 502    | Nominatim caído o timeout            |

---

## `GET /geocode/reverse` — Reverse (coords → lugar)

### Input

| Parámetro | Tipo  | Requerido | Rango          | Descripción | Ejemplo  |
| --------- | ----- | --------- | -------------- | ----------- | -------- |
| `lat`     | float | sí        | `[-90, 90]`    | Latitud     | `14.5586`|
| `lon`     | float | sí        | `[-180, 180]`  | Longitud    | `-90.7295`|

### Request

```bash
curl "http://localhost:8000/geocode/reverse?lat=14.5586&lon=-90.7295"
```

```http
GET http://localhost:8000/geocode/reverse?lat=14.5586&lon=-90.7295
Accept: application/json
```

### Output 200

```json
{
  "lat": 14.5586,
  "lon": -90.7295,
  "display_name": "Antigua Guatemala, Sacatepéquez, Guatemala",
  "country_code": "gt",
  "state": "Sacatepéquez",
  "municipality": "Antigua Guatemala",
  "type": "city",
  "interpretation": "Esa coordenada corresponde a Antigua Guatemala, Sacatepéquez, Guatemala."
}
```

### Errores

| Status | Causa                                  |
| ------ | -------------------------------------- |
| 404    | Sin resultado para esas coordenadas    |
| 422    | `lat`/`lon` fuera de rango             |
| 502    | Nominatim caído o timeout              |

---

## Campos (ambos endpoints)

| Campo          | Tipo         | Descripción                                  |
| -------------- | ------------ | -------------------------------------------- |
| `lat`, `lon`   | float        | Coordenadas (devueltas o resueltas)          |
| `display_name` | string       | Etiqueta completa del lugar                  |
| `country_code` | string\|null | ISO alpha-2 en minúsculas                    |
| `state`        | string\|null | Departamento / estado / provincia            |
| `municipality` | string\|null | Municipio / ciudad                           |
| `type`         | string\|null | Tipo OSM (administrative, village, city…)    |
| `interpretation` | string     | Resumen en español listo para Gemma          |

## Tool definitions (function calling)

```json
{
  "name": "geocode",
  "description": "Convierte texto libre en lat/lon (top-1). Cacheado 30 días por query normalizada + país.",
  "parameters": {
    "type": "object",
    "properties": {
      "q":       { "type": "string", "minLength": 1, "description": "Texto libre del lugar" },
      "country": { "type": "string", "minLength": 2, "maxLength": 2, "description": "ISO alpha-2 opcional" }
    },
    "required": ["q"]
  }
}
```

```json
{
  "name": "geocode_reverse",
  "description": "Convierte lat/lon en nombre de lugar (país, estado, municipio). Cacheado 30 días por coordenada.",
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

## Notas operativas

- Nominatim público limita a ~1 req/s y exige `User-Agent` identificable (`agrogem/1.0`).
- El cache agresivo (30 días, keys `geocode:fwd:{country|ANY}:{query}` y `geocode:rev:{lat}:{lon}`) absorbe la mayoría del tráfico.
- Para volumen alto: self-hostear Nominatim o cambiar el adapter a Mapbox / LocationIQ / Google.

## Implementación

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py)
- Schema: [`schema.py`](schema.py)
- Provider HTTP: [`providers/nominatim/geocoding_provider.py`](../../providers/nominatim/geocoding_provider.py)
- Cache Redis: [`providers/redis/geocoding_cache.py`](../../providers/redis/geocoding_cache.py)
