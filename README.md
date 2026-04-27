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

**Input:** `lat: float` (-90..90), `lon: float` (-180..180)

**Output (resumido):**
```json
{
  "latitude": 14.76, "longitude": -90.99, "timezone": "America/Guatemala",
  "current": {
    "time": "2026-04-27T14:00", "temperature_2m": 22.4,
    "relative_humidity_2m": 68, "precipitation": 0.0,
    "weather_code": 2, "wind_speed_10m": 11.5
  },
  "hourly": { "time": ["..."], "temperature_2m": [...], "relative_humidity_2m": [...], "precipitation_probability": [...] },
  "daily":  { "time": ["..."], "temperature_2m_max": [...], "temperature_2m_min": [...],
              "precipitation_sum": [...], "et0_fao_evapotranspiration": [...], "uv_index_max": [...] }
}
```

#### `GET /soil`
Perfil ISRIC SoilGrids 0–30 cm (cache 90 días).

**Input:** `lat`, `lon`

**Output:**
```json
{
  "lat": 14.76, "lon": -90.99,
  "horizons": [
    { "depth": "0-5cm",   "ph": 6.2, "soc_g_per_kg": 12.4, "nitrogen_g_per_kg": 1.1,
      "clay_pct": 28, "sand_pct": 35, "silt_pct": 37, "cec_mmol_per_kg": 185, "texture_class": "clay loam" },
    { "depth": "5-15cm",  "...": "..." },
    { "depth": "15-30cm", "...": "..." }
  ],
  "dominant_texture": "clay loam",
  "interpretation": "Horizonte superficial (0-5 cm): ligeramente ácido (pH 6.2); materia orgánica moderada (SOC 12.4 g/kg); textura clay loam."
}
```

#### `GET /elevation`
Altitud m.s.n.m (Open-Meteo, cache 365 días).

**Input:** `lat`, `lon` → **Output:** `{ "lat": 14.76, "lon": -90.99, "elevation_m": 2310.0 }`

#### `GET /frost-risk`
Índice 0–1 de helada 7d, ya corregido por elevación.

**Input:** `lat`, `lon`

**Output:**
```json
{
  "lat": 14.76, "lon": -90.99, "elevation_m": 2310.0,
  "risk_score": 0.62, "risk_level": "high",
  "factors": {
    "window_days": 7, "min_temp_c": -1.2, "frost_hours": 3,
    "freezing_probability_pct": 18.5, "altitude_correction_c": -1.4,
    "rule_notes": ["3 horas con T° < 0°C", "elevación 2310 m → corrección -1.4°C"]
  },
  "interpretation": "Riesgo alto de helada los próximos 7 días. Mínima esperada -1.2°C..."
}
```

#### `GET /geocode/reverse`
`lat,lon` → país / estado / municipio.

**Input:** `lat`, `lon`

**Output:** `{ "lat": 14.76, "lon": -90.99, "display_name": "Tecpán Guatemala, Chimaltenango, Guatemala", "country_code": "gt", "state": "Chimaltenango", "municipality": "Tecpán Guatemala", "type": "administrative" }`

---

### 🟢 Tier 2 — Tool chaining

#### `GET /geocode`
Texto libre → `lat,lon`. **Es la primera llamada** cuando el usuario menciona un lugar por nombre.

**Input:**
- `q: string` (requerido) — texto libre. Ej: `"Chimaltenango"`, `"Zapopan, Jal."`, `"finca el quetzal, alta verapaz"`.
- `country: string` (opcional) — filtro ISO alpha-2. Ej: `"GT"`, `"MX"`. Recomendado para reducir ambigüedad.

**Output:** mismo shape que `/geocode/reverse` (devuelve top-1).

```json
{ "lat": 14.6611, "lon": -90.8210, "display_name": "Chimaltenango, Guatemala",
  "country_code": "gt", "state": "Chimaltenango", "municipality": "Chimaltenango",
  "type": "administrative" }
```

---

### 🟡 Tier 3 — `lat` / `lon` + 1 enum corto

#### `GET /pest-risk`
Riesgo de plaga 7d (grados-día + humedad). Reusa cache de `/weather`.

**Input:**
- `lat`, `lon`
- `pest`: enum de **9 valores** — `spider_mite | whitefly | broad_mite | white_grub | thrips | leafminer | fall_armyworm | root_knot_nematode | coffee_berry_borer`

**Output:**
```json
{
  "pest": "fall_armyworm", "pest_type": "insect", "life_stage_risk": "larva",
  "affected_crops": ["corn", "rice", "sugarcane"],
  "lat": 14.66, "lon": -90.82,
  "risk_score": 0.74, "risk_level": "high",
  "factors": {
    "window_days": 7, "avg_temp_c": 24.8, "avg_humidity_pct": 72, "rainy_days": 2,
    "rule_notes": ["T° media 24.8°C óptima para desarrollo larval", "2 días lluviosos"]
  },
  "virus_coalert": null,
  "interpretation": "Riesgo alto de gusano cogollero (Spodoptera frugiperda)..."
}
```

#### `GET /irrigation-risk`
Estrés hídrico 7d. Combina ET₀ Hargreaves con coeficientes Kc por cultivo y forecast de lluvia.

**Input:**
- `lat`, `lon`
- `crop`: `corn | rice | bean | wheat | coffee | sugarcane | banana | tomato | potato | onion | broccoli | rose`

**Output:**
```json
{
  "crop": "potato", "lat": 14.76, "lon": -90.99,
  "risk_score": 0.58, "risk_level": "moderate",
  "factors": {
    "window_days": 7, "et0_sum_mm": 32.4, "precipitation_sum_mm": 8.2,
    "crop_water_requirement_mm": 35.6, "soil_water_deficit_mm": 27.4,
    "rule_notes": ["Déficit hídrico 27.4 mm en 7 días"]
  },
  "irrigation_recommendation_mm": 27.4,
  "interpretation": "Riesgo moderado de estrés hídrico para papa. Aplicar ~27 mm de riego en los próximos 7 días."
}
```

#### `GET /harvest-window`
Ventana óptima de cosecha (T°, RH, lluvia, días secos).

**Input:**
- `lat`, `lon`
- `crop`: `corn | rice | bean | wheat | coffee | sugarcane | banana | tomato | potato | onion | broccoli | rose | strawberry`

**Output:**
```json
{
  "crop": "coffee", "lat": 14.76, "lon": -90.99,
  "window_score": 0.81, "window_level": "high",
  "factors": {
    "window_days": 7, "avg_temp_c": 21.5, "avg_humidity_pct": 65,
    "rainy_days": 1, "dry_spells": 4,
    "rule_notes": ["4 días secos consecutivos óptimos para secado en patio"]
  },
  "optimal_dates": ["2026-04-29", "2026-04-30", "2026-05-01"],
  "warning": null,
  "interpretation": "Ventana óptima para cosechar café entre el 29 abr y el 1 may..."
}
```

---

### 🟠 Tier 4 — Más parámetros / enum extenso

#### `GET /disease-risk`
Cubre **~50 enfermedades** entre cultivos de granos, hortalizas, frutales, ornamentales y cacao/café/banano. Mismo formato de respuesta que `pest-risk`.

**Input:**
- `lat`, `lon`
- `disease`: enum largo — `coffee_rust | late_blight | corn_rust | wheat_leaf_rust | rice_blast | tomato_late_blight | potato_late_blight | banana_black_sigatoka | cacao_monilia | rose_botrytis | ...` (lista completa en `domain/disease_risk/schema.py`).

> 💡 Tip: para function calling con Gemma, conviene **inyectar dinámicamente** solo las enfermedades relevantes al cultivo del usuario en el `enum` de la tool (en vez de las 50). Eso mantiene el prompt corto y la latencia baja.

**Output (ejemplo `coffee_rust`):**
```json
{
  "disease": "coffee_rust", "lat": 14.56, "lon": -90.73,
  "risk_score": 0.72, "risk_level": "high",
  "factors": {
    "window_days": 7, "avg_temp_c": 22.4, "avg_humidity_pct": 84, "rainy_days": 4,
    "rule_notes": [
      "T° media 22.4°C en rango óptimo [21-25°C]",
      "humedad relativa 84% ≥ 80%",
      "4 días lluviosos (umbral 3)"
    ]
  },
  "interpretation": "Riesgo alto de roya del café (Hemileia vastatrix) en los próximos 7 días..."
}
```

#### `GET /climate/history`
Histórico desde 1981 (NASA POWER comunidad AG). Para preguntas tipo *"¿llovió más este año que el promedio?"*.

**Input:**
- `lat`, `lon`
- `start: string` (`YYYY-MM-DD`)
- `end: string` (`YYYY-MM-DD`)
- `granularity: string` (opcional, default `monthly`) — `monthly` (recomendado para rangos largos) o `daily` (máx. 366 días por request).

**Output:**
```json
{
  "lat": 14.66, "lon": -90.82, "granularity": "monthly",
  "start": "2024-01-01", "end": "2024-12-31",
  "series": [
    { "date": "2024-01", "t2m": 16.2, "t2m_max": 22.1, "t2m_min": 9.8,
      "precipitation_mm": 4.1, "rh_pct": 71, "solar_mj_m2": 540.2 },
    { "date": "2024-02", "...": "..." }
  ]
}
```

#### `GET /gbif/species`
Ocurrencias documentadas de una especie en un país (GBIF). Útil para responder *"¿se ha visto el gusano cogollero en Guatemala?"*.

**Input:**
- `scientific_name: string` (binomial, ≥2 chars). Ej: `"Spodoptera frugiperda"`.
- `country: string` (ISO alpha-2). Ej: `"GT"`.
- `limit: int` (1..300).

**Output:**
```json
{
  "found": true, "scientific_name": "Spodoptera frugiperda",
  "kingdom": "Animalia", "family": "Noctuidae",
  "common_names": [{ "name": "fall armyworm", "lang": "eng" },
                   { "name": "gusano cogollero", "lang": "spa" }],
  "country": "GT", "total_records_in_country": 412, "records_in_sample": 300,
  "top_regions": [["Petén", 84], ["Escuintla", 61], ["Izabal", 47]],
  "recent_years": { "2023": 58, "2024": 71, "2025": 33 },
  "interpretation": "Especie documentada en Guatemala con 412 registros..."
}
```

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
