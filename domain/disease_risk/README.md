# `/disease-risk` — Riesgo de enfermedad fitopatológica 7 días

Tier 🟠 4 · Derivado de `/weather` · Sin cache propio (reusa el de weather, 15 min).

← [Volver al README principal](../../README.md)

Combina forecast horario (T° media, humedad relativa, días lluviosos) con umbrales agronómicos específicos por enfermedad. Cubre **~50 enfermedades** entre granos, hortalizas, frutales, ornamentales, cacao, café y banano.

## Endpoint

```
GET /disease-risk?lat=<float>&lon=<float>&disease=<enum>
```

## Input

| Parámetro | Tipo  | Requerido | Descripción                  | Ejemplo         |
| --------- | ----- | --------- | ---------------------------- | --------------- |
| `lat`     | float | sí        | `[-90, 90]`                  | `14.5586`       |
| `lon`     | float | sí        | `[-180, 180]`                | `-90.7295`      |
| `disease` | enum  | sí        | Una de las ~50 enfermedades  | `"coffee_rust"` |

### Enum `disease` (50 valores)

```
coffee_rust · late_blight · corn_rust · wheat_leaf_rust · wheat_yellow_rust · wheat_stem_rust ·
sugarbeet_cercospora · sugarbeet_rust · barley_rust · rice_blast · rice_brown_spot ·
rice_sheath_blight · rice_bacterial_leaf_blight · tomato_early_blight · tomato_late_blight ·
tomato_fusarium_wilt · potato_late_blight · potato_early_blight · bean_rust ·
bean_angular_leaf_spot · bean_anthracnose · banana_black_sigatoka · banana_fusarium_wilt ·
cardamom_rot · sugarcane_rust · sugarcane_smut · sugarcane_red_rot · rose_botrytis ·
rose_powdery_mildew · rose_downy_mildew · rose_black_spot · cacao_monilia · cacao_black_pod ·
cacao_witches_broom · cacao_frosty_pod · banana_moko · banana_cordana_leaf_spot ·
potato_bacterial_wilt · potato_blackleg · oca_downy_mildew · broccoli_downy_mildew ·
broccoli_black_rot · broccoli_alternaria · oil_palm_bud_rot · oil_palm_spear_rot ·
oil_palm_ganoderma · corn_gray_leaf_spot · corn_northern_leaf_blight · corn_stalk_rot ·
coffee_cercospora
```

> 💡 Tip: para function calling, **inyectá dinámicamente** solo las enfermedades del cultivo del usuario en el `enum` de la tool. Mantiene el prompt corto y enfocado.

### Request

```bash
curl "http://localhost:8000/disease-risk?lat=14.5586&lon=-90.7295&disease=coffee_rust"
```

```http
GET http://localhost:8000/disease-risk?lat=14.5586&lon=-90.7295&disease=coffee_rust
Accept: application/json
```

## Output

### 200 OK

```json
{
  "disease": "coffee_rust",
  "lat": 14.5586,
  "lon": -90.7295,
  "risk_score": 0.72,
  "risk_level": "high",
  "factors": {
    "window_days": 7,
    "avg_temp_c": 22.4,
    "avg_humidity_pct": 84,
    "rainy_days": 4,
    "rule_notes": [
      "T° media 22.4°C en rango óptimo [21-25°C]",
      "humedad relativa 84% ≥ 80%",
      "4 días lluviosos (umbral 3)"
    ]
  },
  "interpretation": "Riesgo alto de roya del café (Hemileia vastatrix) en los próximos 7 días. Factores: T° media 22.4°C en rango óptimo [21-25°C]; humedad relativa 84% ≥ 80%; 4 días lluviosos."
}
```

### Campos

| Campo                       | Tipo            | Descripción                                       |
| --------------------------- | --------------- | ------------------------------------------------- |
| `disease`                   | enum            | Enfermedad consultada                             |
| `risk_score`                | float (0–1)     | Índice compuesto                                  |
| `risk_level`                | enum            | `low` / `moderate` / `high` / `very_high`         |
| `factors.avg_temp_c`        | float \| null   | T° media horaria de la ventana                    |
| `factors.avg_humidity_pct`  | float \| null   | Humedad relativa media                            |
| `factors.rainy_days`        | int             | Días con precipitación ≥ 1 mm                     |
| `factors.rule_notes`        | string[]        | Condiciones favorables detectadas                 |
| `interpretation`            | string          | Resumen para Gemma                                |

### Errores

| Status | Causa                                                |
| ------ | ---------------------------------------------------- |
| 422    | `disease` no reconocida o `lat`/`lon` fuera de rango |
| 502    | Weather provider caído                               |

## Tool definition (function calling)

> Para Gemma, recortá el `enum` a solo las enfermedades del cultivo del usuario.

```json
{
  "name": "disease_risk",
  "description": "Índice de riesgo de enfermedad (0.0-1.0) para los próximos 7 días. Combina el forecast con reglas agronómicas específicas por enfermedad.",
  "parameters": {
    "type": "object",
    "properties": {
      "lat":     { "type": "number", "minimum": -90,  "maximum": 90,  "description": "Latitud" },
      "lon":     { "type": "number", "minimum": -180, "maximum": 180, "description": "Longitud" },
      "disease": {
        "type": "string",
        "enum": ["coffee_rust", "late_blight", "corn_rust", "tomato_late_blight", "potato_late_blight"],
        "description": "Enfermedad relevante al cultivo en producción"
      }
    },
    "required": ["lat", "lon", "disease"]
  }
}
```

## Implementación

- Router: [`router.py`](router.py)
- Service: [`service.py`](service.py) — reglas en `_DISEASE_RULES`
- Schema: [`schema.py`](schema.py)
- Composición: depende de `domain/weather`

### Agregar una enfermedad

1. Agregar entrada a `_DISEASE_RULES` en `service.py` (umbrales T°, RH, días lluviosos).
2. Ampliar el `Literal` `DiseaseName` en `schema.py`.
3. Listo — el endpoint la sirve sin tocar nada más.
