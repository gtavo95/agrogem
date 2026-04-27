# Agrogem — Toolkit agronómico para LLMs

API REST de **herramientas agronómicas** (clima, suelo, riesgos fitosanitarios, ventana de cosecha, etc.) diseñada para ser consumida como **function calling tools** por modelos pequeños tipo **Gemma 2B/9B** desde una app móvil.

> Agrogem no genera el lenguaje natural — eso lo hace el LLM en el dispositivo. Agrogem aporta **datos confiables y deterministas** detrás de endpoints simples para que el modelo no tenga que saber agronomía ni inventar números.

📚 **Documentación completa** (arquitectura hexagonal, setup, deploy, referencia exhaustiva de cada endpoint, secretos, persistencia): **[`/docs/README.md`](docs/README.md)**

---

## ¿Por qué este diseño?

Los LLM pequeños tienen tres problemas para asistir a un productor agrícola:

1. **No conocen el clima ni el suelo de tu parcela.** No tienen acceso a datos en vivo.
2. **Alucinan umbrales agronómicos.** "¿Qué humedad favorece la roya del café?" → respuesta plausible pero inventada.
3. **No manejan bien parámetros complejos.** Function calling con 6 args y enums largos los rompe.

Agrogem resuelve los tres exponiendo cada fuente externa (NASA POWER, Open-Meteo, ISRIC SoilGrids, GBIF, Nominatim) y cada cálculo agronómico (riesgo de helada, riego, plaga, enfermedad, ventana de cosecha) detrás de **GETs deterministas con pocos parámetros y descripciones en español ya redactadas para `tool_description`**.

---

## Catálogo de tools, ordenado por compatibilidad con Gemma

### 🟢 Tier 1 — Plug & play (solo `lat` / `lon`)

Cero enums, dos floats. Los más seguros para Gemma chico.

| Tool                   | Para qué sirve                                                  |
| ---------------------- | --------------------------------------------------------------- |
| `GET /weather`         | Clima actual + forecast horario y diario 7d (Open-Meteo)        |
| `GET /soil`            | Perfil de suelo 0–30 cm: pH, SOC, N, textura USDA, CEC          |
| `GET /elevation`       | Altitud m.s.n.m (afecta heladas, ET₀, idoneidad de cultivo)     |
| `GET /frost-risk`      | Índice 0–1 de riesgo de helada 7d (ajustado por elevación)      |
| `GET /geocode/reverse` | `lat,lon` → país / estado / municipio                           |

### 🟢 Tier 2 — Tool chaining (resolver ubicación primero)

| Tool             | Para qué sirve                                                                       |
| ---------------- | ------------------------------------------------------------------------------------ |
| `GET /geocode`   | Texto libre → `lat,lon`. **Llamada inicial** cuando el usuario dice "Chimaltenango". |

### 🟡 Tier 3 — Bien con prompt cuidado (lat/lon + 1 enum corto)

| Tool                    | Enum                                  | Para qué sirve                              |
| ----------------------- | ------------------------------------- | ------------------------------------------- |
| `GET /pest-risk`        | 9 plagas                              | Riesgo de plaga 7d (grados-día + humedad)   |
| `GET /irrigation-risk`  | ~12 cultivos                          | Estrés hídrico 7d (ET₀ Hargreaves + Kc)     |
| `GET /harvest-window`   | ~13 cultivos                          | Ventana óptima de cosecha (T°, RH, lluvia)  |

### 🟠 Tier 4 — Avanzados (más parámetros o enum grande)

| Tool                    | Caveat para Gemma                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| `GET /disease-risk`     | Enum de **~50 enfermedades**. Gemma chico puede alucinar valores — filtra por cultivo.     |
| `GET /climate/history`  | 4–5 args incluyendo dos fechas ISO. Cuida que `start ≤ end` en el system prompt.           |
| `GET /gbif/species`     | Requiere nombre científico binomial (`Spodoptera frugiperda`).                             |

### ⚫ No exponer como tool

`/users/*`, `/sessions/*`, `/chat/*` (es el **consumidor**, no una tool) y `/pest/upload-url` + `/pest/identify` (flujo multimodal con archivos — no encaja en function calling).

---

## Patrón de uso recomendado

```
Usuario: "¿hay riesgo de helada en mi parcela en Tecpán esta semana?"
         │
         ▼
Gemma  ──► geocode(q="Tecpán", country="GT")
         │      ↩ { lat: 14.76, lon: -90.99 }
         ▼
Gemma  ──► frost_risk(lat=14.76, lon=-90.99)
         │      ↩ { risk_score: 0.62, risk_level: "high", interpretation: "..." }
         ▼
Gemma  ──► respuesta en lenguaje natural al usuario
```

Stack mínimo viable para una demo: **`geocode` + `weather` + `soil` + `frost-risk` + `irrigation-risk`**. Cinco tools, cubren la mayoría de consultas agronómicas.

---

## Esqueleto de tool schema (Gemma / OpenAI-style)

```json
{
  "name": "weather",
  "description": "Clima actual + pronóstico horario y diario (7 días) desde Open-Meteo. Cacheado en Redis por 15 minutos por coordenada.",
  "parameters": {
    "type": "object",
    "properties": {
      "lat": { "type": "number", "minimum": -90,  "maximum": 90  },
      "lon": { "type": "number", "minimum": -180, "maximum": 180 }
    },
    "required": ["lat", "lon"]
  }
}
```

> 💡 Las **descripciones en español** que ves en cada router (`@router.get(...)` con docstring) están redactadas para que las copies tal cual al campo `description` del tool.

---

## Quick start

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # ajustá MODE, MONGODB_URI, REDIS_URI

fastapi dev main.py
# → http://127.0.0.1:8000/docs   (OpenAPI interactivo, ideal para extraer tool schemas)
```

Cada endpoint tiene un request de ejemplo en `.http/` (usá la extensión **REST Client** en VS Code).

Para detalles de instalación, deploy en Cloud Run, secretos GCP, arquitectura hexagonal y referencia campo-por-campo de cada respuesta, ver [`docs/README.md`](docs/README.md).

---

## Stack

FastAPI · MongoDB · Redis · GCP Secret Manager · Docker. Datos: Open-Meteo · NASA POWER · ISRIC SoilGrids · Nominatim/OSM · GBIF.

## License

[MIT](LICENSE) © 2026 Gustavo Gordillo
