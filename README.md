# Agrogem — Toolkit agronómico para LLMs

API REST de **herramientas agronómicas** (clima, suelo, riesgos fitosanitarios, ventana de cosecha, etc.) diseñada para ser consumida como **function calling tools** por **Gemma** desde una app móvil.

> Gemma se encarga del lenguaje natural y la conversación con el productor agrícola; Agrogem aporta los **datos en vivo y los cálculos agronómicos** detrás de endpoints HTTP simples y deterministas.

📚 **Documentación completa** (arquitectura hexagonal, setup, deploy, referencia exhaustiva, secretos, persistencia): **[`/docs/README.md`](docs/README.md)**

---

## ¿Qué resuelve Agrogem?

Cuando un productor le pregunta a Gemma *"¿debo regar mañana?"*, el modelo necesita tres cosas que no puede generar por sí mismo:

1. **Saber dónde está la parcela** — `/geocode` traduce `"mi finca en Tecpán"` a coordenadas.
2. **Saber el clima y el suelo de ese punto** — `/weather`, `/soil`, `/elevation` exponen fuentes oficiales (Open-Meteo, NASA POWER, ISRIC SoilGrids).
3. **Aplicar reglas agronómicas validadas** — `/irrigation-risk`, `/frost-risk`, `/disease-risk`, `/pest-risk`, `/harvest-window` combinan el forecast con coeficientes Kc, ET₀ Hargreaves, grados-día y umbrales fitopatológicos.

Cada tool devuelve además un campo `interpretation` en español pensado para que Gemma lo cite o reformule directamente.

---

## Cómo se usa — flujo end-to-end

```
Usuario: "¿hay riesgo de helada en mi finca de papa en Tecpán esta semana?"
   │
   ▼
Gemma decide: necesito ubicación → llama a geocode
   │
   │  geocode(q="Tecpán", country="GT")
   │  ↩ { "lat": 14.7639, "lon": -90.9914, "municipality": "Tecpán Guatemala", ... }
   │
   ▼
Gemma decide: tengo coords → llama a frost_risk
   │
   │  frost_risk(lat=14.7639, lon=-90.9914)
   │  ↩ { "risk_score": 0.62, "risk_level": "high",
   │      "factors": { "min_temp_c": -1.2, "frost_hours": 3, ... },
   │      "interpretation": "Riesgo alto de helada los próximos 7 días..." }
   │
   ▼
Gemma redacta la respuesta en lenguaje natural y la entrega al usuario.
```

**Stack mínimo viable** para una demo: 5 tools — `geocode`, `weather`, `soil`, `frost-risk`, `irrigation-risk`. Cubre la mayoría de consultas de un productor.

---

## Esqueleto de tool schema

Las descripciones en español de cada router (`@router.get(...)` con docstring) están redactadas para usarse tal cual como `description` del tool:

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

Podés extraer el schema completo de cada endpoint desde `http://127.0.0.1:8000/openapi.json` y mapearlo al formato que use tu runtime de Gemma.

---

## Catálogo de tools

### 🟢 Tier 1 — Solo `lat` / `lon`

Dos floats. Ideales para empezar: una sola llamada, sin enums.

#### `GET /weather`
Clima actual + forecast horario y diario 7d (Open-Meteo, cache 15 min).

**Input**

| Parámetro | Tipo  | Descripción            | Ejemplo |
| --------- | ----- | ---------------------- | ------- |
| `lat`     | float | Latitud (-90..90)      | `14.76` |
| `lon`     | float | Longitud (-180..180)   | `-90.99`|

**Output**

| Campo                                  | Descripción                                            | Ejemplo                  |
| -------------------------------------- | ------------------------------------------------------ | ------------------------ |
| `latitude`, `longitude`                | Coordenadas eco                                        | `14.76`, `-90.99`        |
| `timezone`                             | Zona horaria local                                     | `"America/Guatemala"`    |
| `current.temperature_2m`               | Temperatura actual a 2 m (°C)                          | `22.4`                   |
| `current.relative_humidity_2m`         | Humedad relativa actual (%)                            | `68`                     |
| `current.precipitation`                | Precipitación última hora (mm)                         | `0.0`                    |
| `current.weather_code`                 | Código WMO de condición                                | `2` (parcialmente nubl.) |
| `current.wind_speed_10m`               | Viento a 10 m (km/h)                                   | `11.5`                   |
| `hourly.*` (arrays 7d)                 | `time`, `temperature_2m`, `relative_humidity_2m`, `precipitation_probability` | listas de 168 valores |
| `daily.temperature_2m_max/min`         | T° max/min diaria (°C)                                 | `[24.1, 23.8, ...]`      |
| `daily.precipitation_sum`              | Lluvia diaria total (mm)                               | `[0.0, 2.4, ...]`        |
| `daily.et0_fao_evapotranspiration`     | ET₀ FAO diaria (mm)                                    | `[4.2, 4.5, ...]`        |
| `daily.uv_index_max`                   | UV máximo diario                                       | `[10.5, 11.0, ...]`      |

#### `GET /soil`
Perfil ISRIC SoilGrids 0–30 cm (cache 90 días).

**Input**

| Parámetro | Tipo  | Descripción          | Ejemplo |
| --------- | ----- | -------------------- | ------- |
| `lat`     | float | Latitud              | `14.76` |
| `lon`     | float | Longitud             | `-90.99`|

**Output**

| Campo                          | Descripción                                                       | Ejemplo                |
| ------------------------------ | ----------------------------------------------------------------- | ---------------------- |
| `horizons[]`                   | 3 horizontes: `0-5cm`, `5-15cm`, `15-30cm` (mismos campos abajo)  | array de 3 objetos     |
| `horizons[].depth`             | Rango de profundidad                                              | `"0-5cm"`              |
| `horizons[].ph`                | pH en H₂O                                                         | `6.2`                  |
| `horizons[].soc_g_per_kg`      | Carbono orgánico (g/kg)                                           | `12.4`                 |
| `horizons[].nitrogen_g_per_kg` | Nitrógeno total (g/kg)                                            | `1.1`                  |
| `horizons[].clay_pct` / `sand_pct` / `silt_pct` | Composición textural (%)                         | `28` / `35` / `37`     |
| `horizons[].cec_mmol_per_kg`   | Capacidad de intercambio catiónico                                | `185`                  |
| `horizons[].texture_class`     | Clase USDA derivada                                               | `"clay loam"`          |
| `dominant_texture`             | Textura del horizonte 0-5 cm                                      | `"clay loam"`          |
| `interpretation`               | Resumen agronómico en español                                     | `"Horizonte superficial (0-5 cm): ligeramente ácido (pH 6.2)..."` |

#### `GET /elevation`
Altitud m.s.n.m (Open-Meteo, cache 365 días).

**Input**

| Parámetro | Tipo  | Descripción | Ejemplo |
| --------- | ----- | ----------- | ------- |
| `lat`     | float | Latitud     | `14.76` |
| `lon`     | float | Longitud    | `-90.99`|

**Output**

| Campo         | Descripción            | Ejemplo  |
| ------------- | ---------------------- | -------- |
| `lat`, `lon`  | Coordenadas eco        | `14.76`, `-90.99` |
| `elevation_m` | Altitud sobre el nivel del mar (m) | `2310.0` |

#### `GET /frost-risk`
Índice 0–1 de helada 7d, ya corregido por elevación.

**Input**

| Parámetro | Tipo  | Descripción | Ejemplo |
| --------- | ----- | ----------- | ------- |
| `lat`     | float | Latitud     | `14.76` |
| `lon`     | float | Longitud    | `-90.99`|

**Output**

| Campo                              | Descripción                                       | Ejemplo                                 |
| ---------------------------------- | ------------------------------------------------- | --------------------------------------- |
| `elevation_m`                      | Elevación usada para la corrección                | `2310.0`                                |
| `risk_score`                       | Índice 0.0–1.0                                    | `0.62`                                  |
| `risk_level`                       | `low` / `moderate` / `high` / `very_high`         | `"high"`                                |
| `factors.window_days`              | Días evaluados                                    | `7`                                     |
| `factors.min_temp_c`               | T° mínima forecast                                | `-1.2`                                  |
| `factors.frost_hours`              | Horas con T° < 0 °C en la ventana                 | `3`                                     |
| `factors.freezing_probability_pct` | Probabilidad de helada (%)                        | `18.5`                                  |
| `factors.altitude_correction_c`    | Corrección aplicada por elevación (°C)            | `-1.4`                                  |
| `factors.rule_notes`               | Lista de factores detectados, en español          | `["3 horas con T° < 0°C", ...]`         |
| `interpretation`                   | Resumen para Gemma                                | `"Riesgo alto de helada los próximos 7 días..."` |

#### `GET /geocode/reverse`
`lat,lon` → país / estado / municipio.

**Input**

| Parámetro | Tipo  | Descripción | Ejemplo |
| --------- | ----- | ----------- | ------- |
| `lat`     | float | Latitud     | `14.76` |
| `lon`     | float | Longitud    | `-90.99`|

**Output**

| Campo          | Descripción                          | Ejemplo                                          |
| -------------- | ------------------------------------ | ------------------------------------------------ |
| `lat`, `lon`   | Coordenadas eco                      | `14.76`, `-90.99`                                |
| `display_name` | Etiqueta completa del lugar          | `"Tecpán Guatemala, Chimaltenango, Guatemala"`   |
| `country_code` | ISO alpha-2 en minúsculas            | `"gt"`                                           |
| `state`        | Departamento / estado / provincia    | `"Chimaltenango"`                                |
| `municipality` | Municipio / ciudad                   | `"Tecpán Guatemala"`                             |
| `type`         | Tipo OSM (administrative, village…)  | `"administrative"`                               |

---

### 🟢 Tier 2 — Tool chaining

#### `GET /geocode`
Texto libre → `lat,lon`. **Es la primera llamada** cuando el usuario menciona un lugar por nombre.

**Input**

| Parámetro | Tipo   | Requerido | Descripción                            | Ejemplo                          |
| --------- | ------ | --------- | -------------------------------------- | -------------------------------- |
| `q`       | string | sí        | Texto libre del lugar                  | `"Chimaltenango"`, `"finca el quetzal, alta verapaz"` |
| `country` | string | no        | Filtro ISO alpha-2 (reduce ambigüedad) | `"GT"`, `"MX"`                   |

**Output** — mismo shape que `/geocode/reverse` (devuelve top-1).

| Campo          | Descripción                         | Ejemplo                                |
| -------------- | ----------------------------------- | -------------------------------------- |
| `lat`, `lon`   | Coordenadas resueltas               | `14.6611`, `-90.8210`                  |
| `display_name` | Etiqueta completa                   | `"Chimaltenango, Guatemala"`           |
| `country_code` | ISO alpha-2                         | `"gt"`                                 |
| `state`        | Departamento / estado               | `"Chimaltenango"`                      |
| `municipality` | Municipio                           | `"Chimaltenango"`                      |
| `type`         | Tipo OSM                            | `"administrative"`                     |

---

### 🟡 Tier 3 — `lat` / `lon` + 1 enum corto

#### `GET /pest-risk`
Riesgo de plaga 7d (grados-día + humedad). Reusa cache de `/weather`.

**Input**

| Parámetro | Tipo   | Descripción                                     | Ejemplo            |
| --------- | ------ | ----------------------------------------------- | ------------------ |
| `lat`     | float  | Latitud                                         | `14.66`            |
| `lon`     | float  | Longitud                                        | `-90.82`           |
| `pest`    | enum   | `spider_mite \| whitefly \| broad_mite \| white_grub \| thrips \| leafminer \| fall_armyworm \| root_knot_nematode \| coffee_berry_borer` | `"fall_armyworm"`  |

**Output**

| Campo                       | Descripción                                       | Ejemplo                                                 |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------------- |
| `pest`                      | Plaga consultada                                  | `"fall_armyworm"`                                       |
| `pest_type`                 | `mite` / `insect` / `nematode`                    | `"insect"`                                              |
| `life_stage_risk`           | `larva` / `adult` / `both`                        | `"larva"`                                               |
| `affected_crops`            | Cultivos sensibles                                | `["corn", "rice", "sugarcane"]`                         |
| `risk_score`                | Índice 0.0–1.0                                    | `0.74`                                                  |
| `risk_level`                | `low` / `moderate` / `high` / `very_high`         | `"high"`                                                |
| `factors.avg_temp_c`        | T° media de la ventana                            | `24.8`                                                  |
| `factors.avg_humidity_pct`  | Humedad relativa media                            | `72`                                                    |
| `factors.rainy_days`        | Días con precipitación ≥ 1 mm                     | `2`                                                     |
| `factors.rule_notes`        | Factores detectados                               | `["T° media 24.8°C óptima para desarrollo larval"]`     |
| `virus_coalert`             | Alerta de virus asociado (puede ser `null`)       | `null`                                                  |
| `interpretation`            | Resumen para Gemma                                | `"Riesgo alto de gusano cogollero..."`                  |

#### `GET /irrigation-risk`
Estrés hídrico 7d. Combina ET₀ Hargreaves con coeficientes Kc por cultivo y forecast de lluvia.

**Input**

| Parámetro | Tipo   | Descripción                              | Ejemplo     |
| --------- | ------ | ---------------------------------------- | ----------- |
| `lat`     | float  | Latitud                                  | `14.76`     |
| `lon`     | float  | Longitud                                 | `-90.99`    |
| `crop`    | enum   | `corn \| rice \| bean \| wheat \| coffee \| sugarcane \| banana \| tomato \| potato \| onion \| broccoli \| rose` | `"potato"`  |

**Output**

| Campo                                | Descripción                                     | Ejemplo                                  |
| ------------------------------------ | ----------------------------------------------- | ---------------------------------------- |
| `risk_score`                         | Índice 0.0–1.0                                  | `0.58`                                   |
| `risk_level`                         | `low` / `moderate` / `high` / `very_high`       | `"moderate"`                             |
| `factors.et0_sum_mm`                 | Evapotranspiración total en la ventana (mm)     | `32.4`                                   |
| `factors.precipitation_sum_mm`       | Lluvia forecast total (mm)                      | `8.2`                                    |
| `factors.crop_water_requirement_mm`  | Demanda hídrica del cultivo (mm)                | `35.6`                                   |
| `factors.soil_water_deficit_mm`      | Déficit en el suelo (mm)                        | `27.4`                                   |
| `factors.rule_notes`                 | Factores detectados                             | `["Déficit hídrico 27.4 mm en 7 días"]`  |
| `irrigation_recommendation_mm`       | **Mm de agua a aplicar** (campo accionable)     | `27.4`                                   |
| `interpretation`                     | Resumen para Gemma                              | `"Aplicar ~27 mm de riego..."`           |

#### `GET /harvest-window`
Ventana óptima de cosecha (T°, RH, lluvia, días secos).

**Input**

| Parámetro | Tipo   | Descripción                              | Ejemplo     |
| --------- | ------ | ---------------------------------------- | ----------- |
| `lat`     | float  | Latitud                                  | `14.76`     |
| `lon`     | float  | Longitud                                 | `-90.99`    |
| `crop`    | enum   | `corn \| rice \| bean \| wheat \| coffee \| sugarcane \| banana \| tomato \| potato \| onion \| broccoli \| rose \| strawberry` | `"coffee"`  |

**Output**

| Campo                       | Descripción                                       | Ejemplo                                                |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| `window_score`              | Índice 0.0–1.0 (1 = óptimo)                       | `0.81`                                                 |
| `window_level`              | `low` / `moderate` / `high` / `very_high`         | `"high"`                                               |
| `factors.avg_temp_c`        | T° media de la ventana                            | `21.5`                                                 |
| `factors.avg_humidity_pct`  | Humedad relativa media                            | `65`                                                   |
| `factors.rainy_days`        | Días lluviosos                                    | `1`                                                    |
| `factors.dry_spells`        | Días secos consecutivos                           | `4`                                                    |
| `factors.rule_notes`        | Factores detectados                               | `["4 días secos consecutivos óptimos para secado"]`    |
| `optimal_dates`             | Fechas sugeridas para cosechar                    | `["2026-04-29", "2026-04-30", "2026-05-01"]`           |
| `warning`                   | Aviso si las condiciones no son ideales           | `null`                                                 |
| `interpretation`            | Resumen para Gemma                                | `"Ventana óptima para cosechar café..."`               |

---

### 🟠 Tier 4 — Más parámetros / enum extenso

#### `GET /disease-risk`
Cubre **~50 enfermedades** entre cultivos de granos, hortalizas, frutales, ornamentales y cacao/café/banano.

**Input**

| Parámetro | Tipo   | Descripción                                                      | Ejemplo         |
| --------- | ------ | ---------------------------------------------------------------- | --------------- |
| `lat`     | float  | Latitud                                                          | `14.56`         |
| `lon`     | float  | Longitud                                                         | `-90.73`        |
| `disease` | enum   | ~50 valores (`coffee_rust`, `late_blight`, `corn_rust`, `wheat_leaf_rust`, `rice_blast`, `tomato_late_blight`, `potato_late_blight`, `banana_black_sigatoka`, `cacao_monilia`, `rose_botrytis`, …). Lista completa en `domain/disease_risk/schema.py`. | `"coffee_rust"` |

> 💡 Tip: para function calling, conviene **inyectar dinámicamente** solo las enfermedades del cultivo del usuario en el `enum` de la tool. Mantiene el prompt corto y enfocado.

**Output**

| Campo                       | Descripción                                       | Ejemplo                                       |
| --------------------------- | ------------------------------------------------- | --------------------------------------------- |
| `disease`                   | Enfermedad consultada                             | `"coffee_rust"`                               |
| `risk_score`                | Índice 0.0–1.0                                    | `0.72`                                        |
| `risk_level`                | `low` / `moderate` / `high` / `very_high`         | `"high"`                                      |
| `factors.avg_temp_c`        | T° media de la ventana                            | `22.4`                                        |
| `factors.avg_humidity_pct`  | Humedad relativa media                            | `84`                                          |
| `factors.rainy_days`        | Días lluviosos                                    | `4`                                           |
| `factors.rule_notes`        | Factores detectados                               | `["T° media 22.4°C en rango óptimo [21-25°C]", "RH 84% ≥ 80%", "4 días lluviosos"]` |
| `interpretation`            | Resumen para Gemma                                | `"Riesgo alto de roya del café (Hemileia vastatrix)..."` |

#### `GET /climate/history`
Histórico desde 1981 (NASA POWER comunidad AG). Para preguntas tipo *"¿llovió más este año que el promedio?"*.

**Input**

| Parámetro     | Tipo   | Requerido | Descripción                                   | Ejemplo        |
| ------------- | ------ | --------- | --------------------------------------------- | -------------- |
| `lat`         | float  | sí        | Latitud                                       | `14.66`        |
| `lon`         | float  | sí        | Longitud                                      | `-90.82`       |
| `start`       | string | sí        | Fecha inicial `YYYY-MM-DD`                    | `"2024-01-01"` |
| `end`         | string | sí        | Fecha final `YYYY-MM-DD` (debe ser ≥ `start`) | `"2024-12-31"` |
| `granularity` | enum   | no        | `monthly` (default) o `daily` (máx. 366 días) | `"monthly"`    |

**Output**

| Campo                     | Descripción                                                | Ejemplo                                  |
| ------------------------- | ---------------------------------------------------------- | ---------------------------------------- |
| `granularity`             | Granularidad eco                                           | `"monthly"`                              |
| `start`, `end`            | Rango eco                                                  | `"2024-01-01"`, `"2024-12-31"`           |
| `series[]`                | Serie temporal (mismos campos abajo)                       | array                                    |
| `series[].date`           | `YYYY-MM-DD` (daily) o `YYYY-MM` (monthly)                 | `"2024-01"`                              |
| `series[].t2m`            | T° media (°C)                                              | `16.2`                                   |
| `series[].t2m_max/min`    | T° max / min (°C)                                          | `22.1` / `9.8`                           |
| `series[].precipitation_mm` | Precipitación (mm)                                       | `4.1`                                    |
| `series[].rh_pct`         | Humedad relativa (%)                                       | `71`                                     |
| `series[].solar_mj_m2`    | Radiación solar (MJ/m²/día o /mes)                         | `540.2`                                  |

#### `GET /gbif/species`
Ocurrencias documentadas de una especie en un país (GBIF). Útil para *"¿se ha visto el gusano cogollero en Guatemala?"*.

**Input**

| Parámetro         | Tipo   | Requerido | Descripción                                   | Ejemplo                    |
| ----------------- | ------ | --------- | --------------------------------------------- | -------------------------- |
| `scientific_name` | string | sí        | Nombre científico binomial (≥ 2 caracteres)   | `"Spodoptera frugiperda"`  |
| `country`         | string | sí        | ISO alpha-2                                   | `"GT"`                     |
| `limit`           | int    | no        | Tamaño de muestra (1..300, default 300)       | `300`                      |

**Output**

| Campo                         | Descripción                                       | Ejemplo                                                |
| ----------------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| `found`                       | Si la especie fue encontrada en GBIF              | `true`                                                 |
| `scientific_name`             | Nombre canónico                                   | `"Spodoptera frugiperda"`                              |
| `kingdom`, `family`           | Taxonomía                                         | `"Animalia"`, `"Noctuidae"`                            |
| `common_names`                | Nombres comunes con idioma                        | `[{"name":"gusano cogollero","lang":"spa"}]`           |
| `country`                     | País consultado                                   | `"GT"`                                                 |
| `total_records_in_country`    | Total de ocurrencias                              | `412`                                                  |
| `records_in_sample`           | Cuántas se trajeron en esta llamada               | `300`                                                  |
| `top_regions`                 | Regiones con más reportes                         | `[["Petén", 84], ["Escuintla", 61]]`                   |
| `recent_years`                | Reportes por año reciente                         | `{"2023": 58, "2024": 71, "2025": 33}`                 |
| `interpretation`              | Resumen para Gemma                                | `"Especie documentada en Guatemala con 412 registros..."` |

---

### ⚫ No exponer como tool

- `/users/*`, `/sessions/*`, `/chat/*` — son el **consumidor** del agente, no herramientas que Gemma deba invocar.
- `/pest/upload-url` + `/pest/identify` — flujo multimodal de identificación de plagas por foto. No encaja en function calling clásico; consúmelos directo desde la app.

---

## Tabla resumen

| Tool                         | Inputs                                    | Output clave                          |
| ---------------------------- | ----------------------------------------- | ------------------------------------- |
| `GET /geocode`               | `q`, `country?`                           | `lat`, `lon`, lugar                   |
| `GET /geocode/reverse`       | `lat`, `lon`                              | país, estado, municipio               |
| `GET /weather`               | `lat`, `lon`                              | current + hourly + daily 7d           |
| `GET /soil`                  | `lat`, `lon`                              | 3 horizontes + textura + interpretación|
| `GET /elevation`             | `lat`, `lon`                              | `elevation_m`                         |
| `GET /frost-risk`            | `lat`, `lon`                              | `risk_score`, `risk_level`, factores  |
| `GET /pest-risk`             | `lat`, `lon`, `pest`                      | `risk_score`, factores, virus coalert |
| `GET /irrigation-risk`       | `lat`, `lon`, `crop`                      | `risk_score`, mm a aplicar            |
| `GET /harvest-window`        | `lat`, `lon`, `crop`                      | `window_score`, fechas óptimas        |
| `GET /disease-risk`          | `lat`, `lon`, `disease`                   | `risk_score`, factores                |
| `GET /climate/history`       | `lat`, `lon`, `start`, `end`, `granularity?` | serie temporal                     |
| `GET /gbif/species`          | `scientific_name`, `country`, `limit?`    | ocurrencias, regiones, años           |

---

## Quick start

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # ajustá MODE, MONGODB_URI, REDIS_URI

fastapi dev main.py
# → http://127.0.0.1:8000/docs       OpenAPI interactivo
# → http://127.0.0.1:8000/openapi.json  schema crudo (extraer tool definitions)
```

Cada endpoint tiene un request de ejemplo en `.http/` (extensión **REST Client** en VS Code).

Para detalles de instalación, deploy en Cloud Run, secretos GCP, arquitectura hexagonal y referencia completa de cada respuesta, ver **[`docs/README.md`](docs/README.md)**.

---

## Stack

FastAPI · MongoDB · Redis · GCP Secret Manager · Docker.
**Datos**: Open-Meteo · NASA POWER · ISRIC SoilGrids · Nominatim/OSM · GBIF.

## License

[MIT](LICENSE) © 2026 Gustavo Gordillo
