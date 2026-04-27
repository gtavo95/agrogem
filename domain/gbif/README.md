# `/gbif/species` — Documented species occurrences

Tier 🟠 4 · Source: [GBIF](https://www.gbif.org/) · Redis cache 24 h.

← [Back to main README](../../README.md)

Useful for *"has fall armyworm been seen in Guatemala?"* or *"in which regions of the country are there reports of Hemileia vastatrix?"*.

## Endpoint

```
GET /gbif/species?scientific_name=<string>&country=<ISO2>&limit=<int>
```

## Input

| Parameter         | Type   | Required | Description                                | Example                    |
| ----------------- | ------ | -------- | ------------------------------------------ | -------------------------- |
| `scientific_name` | string | yes      | Binomial scientific name (≥ 2 chars)       | `"Spodoptera frugiperda"`  |
| `country`         | string | yes      | ISO alpha-2 (exactly 2 chars)              | `"GT"`                     |
| `limit`           | int    | no       | Sample size `[1, 300]`, default 300        | `300`                      |

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

### Fields

| Field                         | Type                       | Description                                  |
| ----------------------------- | -------------------------- | -------------------------------------------- |
| `found`                       | bool                       | Whether the species was found in GBIF        |
| `scientific_name`             | string \| null             | Canonical name                               |
| `kingdom`, `family`           | string \| null             | Taxonomy                                     |
| `common_names[]`              | array                      | Common names with ISO language code          |
| `country`                     | string                     | Queried country                              |
| `total_records_in_country`    | int                        | Total occurrences                            |
| `records_in_sample`           | int                        | How many were fetched in this call           |
| `top_regions`                 | (string, int)[]            | Regions with the most reports                |
| `recent_years`                | dict[string, int]          | Reports per recent year                      |
| `interpretation`              | string                     | Spanish summary for Gemma                    |

### Errors

| Status | Cause                                                |
| ------ | ---------------------------------------------------- |
| 422    | `country` not ISO alpha-2 or `limit` out of range    |
| 502    | GBIF down or timed out                               |

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

## Implementation

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py)
- Schema: [`schema.py`](schema.py)
- Repository / cache: direct Redis layer
