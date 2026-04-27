# `/gbif/species` — Ocurrencias documentadas de una especie

Tier 🟠 4 · Fuente: [GBIF](https://www.gbif.org/) · Cache Redis 24 h.

← [Volver al README principal](../../README.md)

Útil para *"¿se ha visto el gusano cogollero en Guatemala?"* o *"¿en qué regiones del país hay reportes de Hemileia vastatrix?"*.

## Endpoint

```
GET /gbif/species?scientific_name=<string>&country=<ISO2>&limit=<int>
```

## Input

| Parámetro         | Tipo   | Requerido | Descripción                                | Ejemplo                    |
| ----------------- | ------ | --------- | ------------------------------------------ | -------------------------- |
| `scientific_name` | string | sí        | Nombre científico binomial (≥ 2 chars)     | `"Spodoptera frugiperda"`  |
| `country`         | string | sí        | ISO alpha-2 (2 chars exactos)              | `"GT"`                     |
| `limit`           | int    | no        | Tamaño de muestra `[1, 300]`, default 300  | `300`                      |

### Request

```bash
curl "http://localhost:8000/gbif/species?scientific_name=Spodoptera%20frugiperda&country=GT&limit=300"
```

```http
GET http://localhost:8000/gbif/species?scientific_name=Spodoptera frugiperda&country=GT&limit=300
Accept: application/json
```

## Output

### 200 OK

```json
{
  "found": true,
  "scientific_name": "Spodoptera frugiperda",
  "kingdom": "Animalia",
  "family": "Noctuidae",
  "common_names": [
    { "name": "fall armyworm", "lang": "eng" },
    { "name": "gusano cogollero", "lang": "spa" }
  ],
  "country": "GT",
  "total_records_in_country": 412,
  "records_in_sample": 300,
  "top_regions": [
    ["Petén", 84],
    ["Escuintla", 61],
    ["Izabal", 47],
    ["Alta Verapaz", 33],
    ["Suchitepéquez", 28]
  ],
  "recent_years": {
    "2021": 42,
    "2022": 51,
    "2023": 58,
    "2024": 71,
    "2025": 33
  },
  "interpretation": "Especie documentada en Guatemala con 412 registros. Concentración mayor en Petén, Escuintla e Izabal. Reportes en aumento desde 2021."
}
```

### Campos

| Campo                         | Tipo                       | Descripción                                  |
| ----------------------------- | -------------------------- | -------------------------------------------- |
| `found`                       | bool                       | Si la especie fue encontrada en GBIF         |
| `scientific_name`             | string \| null             | Nombre canónico                              |
| `kingdom`, `family`           | string \| null             | Taxonomía                                    |
| `common_names[]`              | array                      | Nombres comunes con idioma ISO               |
| `country`                     | string                     | País consultado                              |
| `total_records_in_country`    | int                        | Total de ocurrencias                         |
| `records_in_sample`           | int                        | Cuántas se trajeron en esta llamada          |
| `top_regions`                 | (string, int)[]            | Regiones con más reportes                    |
| `recent_years`                | dict[string, int]          | Reportes por año reciente                    |
| `interpretation`              | string                     | Resumen para Gemma                           |

### Errores

| Status | Causa                                              |
| ------ | -------------------------------------------------- |
| 422    | `country` no es ISO alpha-2 o `limit` fuera de rango |
| 502    | GBIF caído o timeout                               |

## Tool definition (function calling)

```json
{
  "name": "gbif_species",
  "description": "Ocurrencias documentadas de una especie en un país (GBIF). Devuelve regiones con más reportes y tendencia anual reciente.",
  "parameters": {
    "type": "object",
    "properties": {
      "scientific_name": {
        "type": "string", "minLength": 2,
        "description": "Nombre científico binomial. Ej: 'Spodoptera frugiperda'"
      },
      "country": {
        "type": "string", "minLength": 2, "maxLength": 2,
        "description": "Código ISO alpha-2 del país. Ej: 'GT'"
      },
      "limit": {
        "type": "integer", "minimum": 1, "maximum": 300,
        "description": "Tamaño de la muestra de ocurrencias (máximo 300)"
      }
    },
    "required": ["scientific_name", "country"]
  }
}
```

## Implementación

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py)
- Schema: [`schema.py`](schema.py)
- Repository / cache: capa Redis directa
