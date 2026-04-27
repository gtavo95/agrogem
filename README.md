# Agrogem — Agronomic toolkit for LLMs

REST API of **agronomic tools** (weather, soil, frost / pest / disease / irrigation risks, harvest window, etc.) designed to be consumed as **function calling tools** by **Gemma** from a mobile app.

> Gemma handles the natural-language conversation with the farmer; Agrogem provides the **live data and agronomic computations** behind simple, deterministic HTTP endpoints.

> 🧠 **Every endpoint includes an `interpretation` field** — a Spanish summary ready to inject as context into Gemma. The frontend doesn't have to assemble the context by hand. (API responses are in Spanish on purpose: the product targets Spanish-speaking farmers.)

📚 **Full documentation** (hexagonal architecture, setup, deploy, exhaustive reference, secrets, persistence): **[`/docs/README.md`](docs/README.md)**

---

## What does Agrogem solve?

When a farmer asks Gemma *"should I irrigate tomorrow?"*, the model needs three things it can't generate on its own:

1. **Knowing where the plot is** — `/geocode` translates `"my farm in Tecpán"` into coordinates.
2. **Knowing the local weather and soil** — `/weather`, `/soil`, `/elevation` expose official sources (Open-Meteo, NASA POWER, ISRIC SoilGrids).
3. **Applying validated agronomic rules** — `/irrigation-risk`, `/frost-risk`, `/disease-risk`, `/pest-risk`, `/harvest-window` combine the forecast with Kc coefficients, Hargreaves ET₀, growing-degree days and phytopathological thresholds.

Each tool also returns an `interpretation` field in Spanish so Gemma can quote or rephrase it directly.

---

## How it's used — end-to-end flow

```
User: "Is there frost risk on my potato farm in Tecpán this week?"
   │
   ▼
Gemma decides: I need a location → calls geocode
   │
   │  geocode(q="Tecpán", country="GT")
   │  ↩ { "lat": 14.7639, "lon": -90.9914, "municipality": "Tecpán Guatemala", ... }
   │
   ▼
Gemma decides: I have coords → calls frost_risk
   │
   │  frost_risk(lat=14.7639, lon=-90.9914)
   │  ↩ { "risk_score": 0.62, "risk_level": "high",
   │      "factors": { "min_temp_c": -1.2, "frost_hours": 3, ... },
   │      "interpretation": "Riesgo alto de helada los próximos 7 días..." }
   │
   ▼
Gemma drafts the natural-language answer and delivers it to the user.
```

**Minimum viable stack** for a demo: 5 tools — `geocode`, `weather`, `soil`, `frost-risk`, `irrigation-risk`. Covers most farmer queries.

---

## Tool schema skeleton

The Spanish descriptions in each router (`@router.get(...)` docstring) are written to be used as-is for the tool's `description`:

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

You can pull the full schema for each endpoint from `http://127.0.0.1:8000/openapi.json` and map it to your Gemma runtime's format.

---

## Tool catalog

> 📖 Each tool has a **dedicated README** with copy-paste-ready JSON inputs/outputs, function-calling tool definition, and implementation notes. Click the endpoint title to jump to its doc.

### 🟢 Tier 1 — `lat` / `lon` only

Two floats. The easiest to start with: a single call, no enums.

#### [`GET /weather`](domain/weather/README.md)
Current weather + hourly and daily 7-day forecast (Open-Meteo, 15 min cache).

**Input**

| Parameter | Type  | Description           | Example  |
| --------- | ----- | --------------------- | -------- |
| `lat`     | float | Latitude (-90..90)    | `14.76`  |
| `lon`     | float | Longitude (-180..180) | `-90.99` |

**Output (abridged)**

| Field                                  | Description                                            | Example                  |
| -------------------------------------- | ------------------------------------------------------ | ------------------------ |
| `latitude`, `longitude`                | Echoed coordinates                                     | `14.76`, `-90.99`        |
| `timezone`                             | Local timezone                                         | `"America/Guatemala"`    |
| `current.temperature_2m`               | Current temperature at 2 m (°C)                        | `22.4`                   |
| `current.relative_humidity_2m`         | Current relative humidity (%)                          | `68`                     |
| `current.precipitation`                | Last-hour precipitation (mm)                           | `0.0`                    |
| `current.weather_code`                 | WMO weather code                                       | `2` (partly cloudy)      |
| `current.wind_speed_10m`               | Wind speed at 10 m (km/h)                              | `11.5`                   |
| `hourly.*` (7d arrays)                 | `time`, `temperature_2m`, `relative_humidity_2m`, `precipitation_probability` | 168-element lists |
| `daily.temperature_2m_max/min`         | Daily max/min temperature (°C)                         | `[24.1, 23.8, ...]`      |
| `daily.precipitation_sum`              | Daily total rainfall (mm)                              | `[0.0, 2.4, ...]`        |
| `daily.et0_fao_evapotranspiration`     | Daily FAO ET₀ (mm)                                     | `[4.2, 4.5, ...]`        |
| `daily.uv_index_max`                   | Daily max UV index                                     | `[10.5, 11.0, ...]`      |
| `interpretation`                       | Spanish summary for Gemma                              | `"Clima actual: 22.4°C, 68% humedad..."` |

#### [`GET /soil`](domain/soil/README.md)
ISRIC SoilGrids profile, 0–30 cm (90 day cache).

**Input**

| Parameter | Type  | Description | Example   |
| --------- | ----- | ----------- | --------- |
| `lat`     | float | Latitude    | `14.76`   |
| `lon`     | float | Longitude   | `-90.99`  |

**Output**

| Field                             | Description                                               | Example                |
| --------------------------------- | --------------------------------------------------------- | ---------------------- |
| `horizons[]`                      | 3 horizons: `0-5cm`, `5-15cm`, `15-30cm` (fields below)   | array of 3 objects     |
| `horizons[].depth`                | Depth range                                               | `"0-5cm"`              |
| `horizons[].ph`                   | pH in H₂O                                                 | `6.2`                  |
| `horizons[].soc_g_per_kg`         | Soil organic carbon (g/kg)                                | `12.4`                 |
| `horizons[].nitrogen_g_per_kg`    | Total nitrogen (g/kg)                                     | `1.1`                  |
| `horizons[].clay_pct` / `sand_pct` / `silt_pct` | Texture composition (%)                     | `28` / `35` / `37`     |
| `horizons[].cec_mmol_per_kg`      | Cation exchange capacity                                  | `185`                  |
| `horizons[].texture_class`        | Derived USDA class                                        | `"clay loam"`          |
| `dominant_texture`                | Texture of the 0-5 cm horizon                             | `"clay loam"`          |
| `interpretation`                  | Spanish agronomic summary                                 | `"Horizonte superficial (0-5 cm): ligeramente ácido (pH 6.2)..."` |

#### [`GET /elevation`](domain/elevation/README.md)
Altitude in m a.s.l. (Open-Meteo, 365 day cache).

**Input**

| Parameter | Type  | Description | Example  |
| --------- | ----- | ----------- | -------- |
| `lat`     | float | Latitude    | `14.76`  |
| `lon`     | float | Longitude   | `-90.99` |

**Output**

| Field            | Description                                       | Example  |
| ---------------- | ------------------------------------------------- | -------- |
| `lat`, `lon`     | Echoed coordinates                                | `14.76`, `-90.99` |
| `elevation_m`    | Altitude above sea level (m)                      | `2310.0` |
| `interpretation` | Spanish summary with altitudinal-belt classification | `"Altitud 2310 m s.n.m (tierra fría / sierra)."` |

#### [`GET /frost-risk`](domain/frost_risk/README.md)
0–1 frost risk index for the next 7 days, already corrected for elevation.

**Input**

| Parameter | Type  | Description | Example  |
| --------- | ----- | ----------- | -------- |
| `lat`     | float | Latitude    | `14.76`  |
| `lon`     | float | Longitude   | `-90.99` |

**Output**

| Field                              | Description                                       | Example                                 |
| ---------------------------------- | ------------------------------------------------- | --------------------------------------- |
| `elevation_m`                      | Elevation used for the correction                 | `2310.0`                                |
| `risk_score`                       | Index 0.0–1.0                                     | `0.62`                                  |
| `risk_level`                       | `low` / `moderate` / `high` / `very_high`         | `"high"`                                |
| `factors.window_days`              | Days evaluated                                    | `7`                                     |
| `factors.min_temp_c`               | Forecast minimum temperature                      | `-1.2`                                  |
| `factors.frost_hours`              | Hours below 0 °C in the window                    | `3`                                     |
| `factors.freezing_probability_pct` | Frost probability (%)                             | `18.5`                                  |
| `factors.altitude_correction_c`    | Correction applied for elevation (°C)             | `-1.4`                                  |
| `factors.rule_notes`               | Detected factors, in Spanish                      | `["3 horas con T° < 0°C", ...]`         |
| `interpretation`                   | Spanish summary for Gemma                         | `"Riesgo alto de helada los próximos 7 días..."` |

#### [`GET /geocode/reverse`](domain/geocoding/README.md)
`lat,lon` → country / state / municipality.

**Input**

| Parameter | Type  | Description | Example  |
| --------- | ----- | ----------- | -------- |
| `lat`     | float | Latitude    | `14.76`  |
| `lon`     | float | Longitude   | `-90.99` |

**Output**

| Field            | Description                          | Example                                          |
| ---------------- | ------------------------------------ | ------------------------------------------------ |
| `lat`, `lon`     | Echoed coordinates                   | `14.76`, `-90.99`                                |
| `display_name`   | Full place label                     | `"Tecpán Guatemala, Chimaltenango, Guatemala"`   |
| `country_code`   | Lowercase ISO alpha-2                | `"gt"`                                           |
| `state`          | Department / state / province        | `"Chimaltenango"`                                |
| `municipality`   | Municipality / city                  | `"Tecpán Guatemala"`                             |
| `type`           | OSM type (administrative, village…)  | `"administrative"`                               |
| `interpretation` | Spanish summary for Gemma            | `"Esa coordenada corresponde a Tecpán Guatemala..."` |

---

### 🟢 Tier 2 — Tool chaining

#### [`GET /geocode`](domain/geocoding/README.md)
Free text → `lat,lon`. **The first call** when the user mentions a place by name.

**Input**

| Parameter | Type   | Required | Description                              | Example                                                |
| --------- | ------ | -------- | ---------------------------------------- | ------------------------------------------------------ |
| `q`       | string | yes      | Free-form place text                     | `"Chimaltenango"`, `"finca el quetzal, alta verapaz"`  |
| `country` | string | no       | ISO alpha-2 filter (reduces ambiguity)   | `"GT"`, `"MX"`                                         |

**Output** — same shape as `/geocode/reverse` (returns top-1).

| Field            | Description                         | Example                                |
| ---------------- | ----------------------------------- | -------------------------------------- |
| `lat`, `lon`     | Resolved coordinates                | `14.6611`, `-90.8210`                  |
| `display_name`   | Full label                          | `"Chimaltenango, Guatemala"`           |
| `country_code`   | ISO alpha-2                         | `"gt"`                                 |
| `state`          | Department / state                  | `"Chimaltenango"`                      |
| `municipality`   | Municipality                        | `"Chimaltenango"`                      |
| `type`           | OSM type                            | `"administrative"`                     |
| `interpretation` | Spanish summary for Gemma           | `"Ubicación encontrada: Chimaltenango, Guatemala (14.6611, -90.8210)."` |

---

### 🟡 Tier 3 — `lat` / `lon` + 1 short enum

#### [`GET /pest-risk`](domain/pest_risk/README.md)
7-day pest risk (growing-degree days + humidity). Reuses `/weather` cache.

**Input**

| Parameter | Type   | Description                                     | Example            |
| --------- | ------ | ----------------------------------------------- | ------------------ |
| `lat`     | float  | Latitude                                        | `14.66`            |
| `lon`     | float  | Longitude                                       | `-90.82`           |
| `pest`    | enum   | `spider_mite \| whitefly \| broad_mite \| white_grub \| thrips \| leafminer \| fall_armyworm \| root_knot_nematode \| coffee_berry_borer` | `"fall_armyworm"`  |

**Output**

| Field                       | Description                                       | Example                                                 |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------------- |
| `pest`                      | Queried pest                                      | `"fall_armyworm"`                                       |
| `pest_type`                 | `mite` / `insect` / `nematode`                    | `"insect"`                                              |
| `life_stage_risk`           | `larva` / `adult` / `both`                        | `"larva"`                                               |
| `affected_crops`            | Susceptible crops                                 | `["corn", "rice", "sugarcane"]`                         |
| `risk_score`                | Index 0.0–1.0                                     | `0.74`                                                  |
| `risk_level`                | `low` / `moderate` / `high` / `very_high`         | `"high"`                                                |
| `factors.avg_temp_c`        | Mean temperature in the window                    | `24.8`                                                  |
| `factors.avg_humidity_pct`  | Mean relative humidity                            | `72`                                                    |
| `factors.rainy_days`        | Days with precipitation ≥ 1 mm                    | `2`                                                     |
| `factors.rule_notes`        | Detected factors                                  | `["T° media 24.8°C óptima para desarrollo larval"]`     |
| `virus_coalert`             | Associated virus alert (may be `null`)            | `null`                                                  |
| `interpretation`            | Spanish summary for Gemma                         | `"Riesgo alto de gusano cogollero..."`                  |

#### [`GET /irrigation-risk`](domain/irrigation_risk/README.md)
7-day water stress. Combines Hargreaves ET₀ with crop Kc coefficients and rainfall forecast.

**Input**

| Parameter | Type   | Description                              | Example     |
| --------- | ------ | ---------------------------------------- | ----------- |
| `lat`     | float  | Latitude                                 | `14.76`     |
| `lon`     | float  | Longitude                                | `-90.99`    |
| `crop`    | enum   | `corn \| rice \| bean \| wheat \| coffee \| sugarcane \| banana \| tomato \| potato \| onion \| broccoli \| rose` | `"potato"`  |

**Output**

| Field                                | Description                                     | Example                                  |
| ------------------------------------ | ----------------------------------------------- | ---------------------------------------- |
| `risk_score`                         | Index 0.0–1.0                                   | `0.58`                                   |
| `risk_level`                         | `low` / `moderate` / `high` / `very_high`       | `"moderate"`                             |
| `factors.et0_sum_mm`                 | Total evapotranspiration in the window (mm)     | `32.4`                                   |
| `factors.precipitation_sum_mm`       | Forecast total rainfall (mm)                    | `8.2`                                    |
| `factors.crop_water_requirement_mm`  | Crop water demand (mm)                          | `35.6`                                   |
| `factors.soil_water_deficit_mm`      | Estimated soil deficit (mm)                     | `27.4`                                   |
| `factors.rule_notes`                 | Detected factors                                | `["Déficit hídrico 27.4 mm en 7 días"]`  |
| `irrigation_recommendation_mm`       | **Mm of water to apply** (actionable field)     | `27.4`                                   |
| `interpretation`                     | Spanish summary for Gemma                       | `"Aplicar ~27 mm de riego..."`           |

#### [`GET /harvest-window`](domain/harvest_window/README.md)
Optimal harvest window (T°, RH, rain, dry spells).

**Input**

| Parameter | Type   | Description                              | Example     |
| --------- | ------ | ---------------------------------------- | ----------- |
| `lat`     | float  | Latitude                                 | `14.76`     |
| `lon`     | float  | Longitude                                | `-90.99`    |
| `crop`    | enum   | `corn \| rice \| bean \| wheat \| coffee \| sugarcane \| banana \| tomato \| potato \| onion \| broccoli \| rose \| strawberry` | `"coffee"`  |

**Output**

| Field                       | Description                                       | Example                                                |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| `window_score`              | Index 0.0–1.0 (1 = optimal)                       | `0.81`                                                 |
| `window_level`              | `low` / `moderate` / `high` / `very_high`         | `"high"`                                               |
| `factors.avg_temp_c`        | Mean temperature in the window                    | `21.5`                                                 |
| `factors.avg_humidity_pct`  | Mean relative humidity                            | `65`                                                   |
| `factors.rainy_days`        | Rainy days                                        | `1`                                                    |
| `factors.dry_spells`        | Consecutive dry days                              | `4`                                                    |
| `factors.rule_notes`        | Detected factors                                  | `["4 días secos consecutivos óptimos para secado"]`    |
| `optimal_dates`             | Suggested harvest dates                           | `["2026-04-29", "2026-04-30", "2026-05-01"]`           |
| `warning`                   | Warning if conditions are not ideal               | `null`                                                 |
| `interpretation`            | Spanish summary for Gemma                         | `"Ventana óptima para cosechar café..."`               |

---

### 🟠 Tier 4 — More parameters / large enum

#### [`GET /disease-risk`](domain/disease_risk/README.md)
Covers **~50 diseases** across grains, vegetables, fruit trees, ornamentals, and cocoa/coffee/banana.

**Input**

| Parameter | Type   | Description                                                      | Example         |
| --------- | ------ | ---------------------------------------------------------------- | --------------- |
| `lat`     | float  | Latitude                                                         | `14.56`         |
| `lon`     | float  | Longitude                                                        | `-90.73`        |
| `disease` | enum   | ~50 values (`coffee_rust`, `late_blight`, `corn_rust`, `wheat_leaf_rust`, `rice_blast`, `tomato_late_blight`, `potato_late_blight`, `banana_black_sigatoka`, `cacao_monilia`, `rose_botrytis`, …). Full list in `domain/disease_risk/schema.py`. | `"coffee_rust"` |

> 💡 Tip: for function calling, **dynamically inject** only the diseases relevant to the user's crop into the tool's `enum`. Keeps the prompt short and focused.

**Output**

| Field                       | Description                                       | Example                                       |
| --------------------------- | ------------------------------------------------- | --------------------------------------------- |
| `disease`                   | Queried disease                                   | `"coffee_rust"`                               |
| `risk_score`                | Index 0.0–1.0                                     | `0.72`                                        |
| `risk_level`                | `low` / `moderate` / `high` / `very_high`         | `"high"`                                      |
| `factors.avg_temp_c`        | Mean temperature in the window                    | `22.4`                                        |
| `factors.avg_humidity_pct`  | Mean relative humidity                            | `84`                                          |
| `factors.rainy_days`        | Rainy days                                        | `4`                                           |
| `factors.rule_notes`        | Detected factors                                  | `["T° media 22.4°C en rango óptimo [21-25°C]", "RH 84% ≥ 80%", "4 días lluviosos"]` |
| `interpretation`            | Spanish summary for Gemma                         | `"Riesgo alto de roya del café (Hemileia vastatrix)..."` |

#### [`GET /climate/history`](domain/climate/README.md)
History since 1981 (NASA POWER, AG community). For questions like *"did it rain more this year than the average?"*.

**Input**

| Parameter     | Type   | Required | Description                                       | Example        |
| ------------- | ------ | -------- | ------------------------------------------------- | -------------- |
| `lat`         | float  | yes      | Latitude                                          | `14.66`        |
| `lon`         | float  | yes      | Longitude                                         | `-90.82`       |
| `start`       | string | yes      | Start date `YYYY-MM-DD`                           | `"2024-01-01"` |
| `end`         | string | yes      | End date `YYYY-MM-DD` (must be ≥ `start`)         | `"2024-12-31"` |
| `granularity` | enum   | no       | `monthly` (default) or `daily` (max. 366 days)    | `"monthly"`    |

**Output**

| Field                       | Description                                                | Example                                  |
| --------------------------- | ---------------------------------------------------------- | ---------------------------------------- |
| `granularity`               | Echoed granularity                                         | `"monthly"`                              |
| `start`, `end`              | Echoed range                                               | `"2024-01-01"`, `"2024-12-31"`           |
| `series[]`                  | Time series (fields below)                                 | array                                    |
| `series[].date`             | `YYYY-MM-DD` (daily) or `YYYY-MM` (monthly)                | `"2024-01"`                              |
| `series[].t2m`              | Mean temperature (°C)                                      | `16.2`                                   |
| `series[].t2m_max/min`      | Max / min temperature (°C)                                 | `22.1` / `9.8`                           |
| `series[].precipitation_mm` | Precipitation (mm)                                         | `4.1`                                    |
| `series[].rh_pct`           | Relative humidity (%)                                      | `71`                                     |
| `series[].solar_mj_m2`      | Solar radiation (MJ/m²/day or /month)                      | `540.2`                                  |
| `interpretation`            | Spanish aggregated summary (mean T°, total rain, wettest)  | `"Histórico mensual de 2024-01-01 a 2024-12-31..."` |

#### [`GET /gbif/species`](domain/gbif/README.md)
Documented occurrences of a species in a country (GBIF). Useful for *"has fall armyworm been seen in Guatemala?"*.

**Input**

| Parameter         | Type   | Required | Description                                | Example                    |
| ----------------- | ------ | -------- | ------------------------------------------ | -------------------------- |
| `scientific_name` | string | yes      | Binomial scientific name (≥ 2 chars)       | `"Spodoptera frugiperda"`  |
| `country`         | string | yes      | ISO alpha-2                                | `"GT"`                     |
| `limit`           | int    | no       | Sample size (1..300, default 300)          | `300`                      |

**Output**

| Field                         | Description                                       | Example                                                |
| ----------------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| `found`                       | Whether the species was found in GBIF             | `true`                                                 |
| `scientific_name`             | Canonical name                                    | `"Spodoptera frugiperda"`                              |
| `kingdom`, `family`           | Taxonomy                                          | `"Animalia"`, `"Noctuidae"`                            |
| `common_names`                | Common names with language code                   | `[{"name":"gusano cogollero","lang":"spa"}]`           |
| `country`                     | Queried country                                   | `"GT"`                                                 |
| `total_records_in_country`    | Total occurrences                                 | `412`                                                  |
| `records_in_sample`           | How many were fetched in this call                | `300`                                                  |
| `top_regions`                 | Regions with the most reports                     | `[["Petén", 84], ["Escuintla", 61]]`                   |
| `recent_years`                | Reports per recent year                           | `{"2023": 58, "2024": 71, "2025": 33}`                 |
| `interpretation`              | Spanish summary for Gemma                         | `"Especie documentada en Guatemala con 412 registros..."` |

---

### ⚫ Don't expose as tools

- `/users/*`, `/sessions/*`, `/chat/*` — these are the **consumer** of the agent, not tools Gemma should call.
- `/pest/upload-url` + `/pest/identify` — multimodal pest-from-photo flow. Doesn't fit classic function calling; consume them directly from the app.

---

## Summary table

| Tool                                                       | Inputs                                       | Key output                              |
| ---------------------------------------------------------- | -------------------------------------------- | --------------------------------------- |
| [`GET /geocode`](domain/geocoding/README.md)               | `q`, `country?`                              | `lat`, `lon`, place                     |
| [`GET /geocode/reverse`](domain/geocoding/README.md)       | `lat`, `lon`                                 | country, state, municipality            |
| [`GET /weather`](domain/weather/README.md)                 | `lat`, `lon`                                 | current + hourly + daily 7d             |
| [`GET /soil`](domain/soil/README.md)                       | `lat`, `lon`                                 | 3 horizons + texture + interpretation   |
| [`GET /elevation`](domain/elevation/README.md)             | `lat`, `lon`                                 | `elevation_m`                           |
| [`GET /frost-risk`](domain/frost_risk/README.md)           | `lat`, `lon`                                 | `risk_score`, `risk_level`, factors     |
| [`GET /pest-risk`](domain/pest_risk/README.md)             | `lat`, `lon`, `pest`                         | `risk_score`, factors, virus coalert    |
| [`GET /irrigation-risk`](domain/irrigation_risk/README.md) | `lat`, `lon`, `crop`                         | `risk_score`, mm to apply               |
| [`GET /harvest-window`](domain/harvest_window/README.md)   | `lat`, `lon`, `crop`                         | `window_score`, optimal dates           |
| [`GET /disease-risk`](domain/disease_risk/README.md)       | `lat`, `lon`, `disease`                      | `risk_score`, factors                   |
| [`GET /climate/history`](domain/climate/README.md)         | `lat`, `lon`, `start`, `end`, `granularity?` | time series                             |
| [`GET /gbif/species`](domain/gbif/README.md)               | `scientific_name`, `country`, `limit?`       | occurrences, regions, years             |

---

## Quick start

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # set MODE, MONGODB_URI, REDIS_URI

fastapi dev main.py
# → http://127.0.0.1:8000/docs       interactive OpenAPI
# → http://127.0.0.1:8000/openapi.json  raw schema (extract tool definitions)
```

Each endpoint has a sample request in `.http/` (use the **REST Client** extension in VS Code).

For installation details, Cloud Run deploy, GCP secrets, hexagonal architecture and full per-field response reference, see **[`docs/README.md`](docs/README.md)**.

---

## Stack

FastAPI · MongoDB · Redis · GCP Secret Manager · Docker.
**Data sources**: Open-Meteo · NASA POWER · ISRIC SoilGrids · Nominatim/OSM · GBIF.

## License

[MIT](LICENSE) © 2026 Gustavo Gordillo
