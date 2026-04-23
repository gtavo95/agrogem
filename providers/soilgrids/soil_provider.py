from typing import Any

import httpx

from domain.soil.schema import SoilHorizon, SoilResponse


SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
REQUEST_TIMEOUT_SECONDS = 20.0

DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]
PROPERTIES = ["phh2o", "soc", "nitrogen", "clay", "sand", "silt", "cec"]
VALUE = "mean"

PROPERTY_TO_FIELD = {
    "phh2o": "ph",
    "soc": "soc_g_per_kg",
    "nitrogen": "nitrogen_g_per_kg",
    "clay": "clay_pct",
    "sand": "sand_pct",
    "silt": "silt_pct",
    "cec": "cec_mmol_per_kg",
}


def _usda_texture(
    sand: float | None, silt: float | None, clay: float | None
) -> str | None:
    if sand is None or silt is None or clay is None:
        return None
    if clay >= 40:
        if sand >= 45:
            return "sandy clay"
        if silt >= 40:
            return "silty clay"
        return "clay"
    if clay >= 27:
        if 20 < sand <= 45 and silt < 40:
            return "clay loam"
        if silt >= 40 and sand <= 20:
            return "silty clay loam"
        if sand > 45:
            return "sandy clay loam"
    if clay >= 20 and sand > 45 and silt < 28:
        return "sandy clay loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if silt >= 50 and clay < 27 and (clay >= 12 or silt < 80):
        return "silt loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if sand > 85 and (silt + 1.5 * clay) < 15:
        return "sand"
    if 70 < sand <= 85 and (silt + 2 * clay) < 30:
        return "loamy sand"
    if clay < 20 and (
        (sand >= 52 and (silt + 2 * clay) >= 30)
        or (clay < 7 and silt < 50 and sand >= 43)
    ):
        return "sandy loam"
    return "loam"


def _interpret(top: SoilHorizon) -> str:
    parts: list[str] = []
    if top.ph is not None:
        if top.ph < 5.5:
            parts.append(f"suelo ácido (pH {top.ph:.1f})")
        elif top.ph < 6.5:
            parts.append(f"ligeramente ácido (pH {top.ph:.1f})")
        elif top.ph < 7.5:
            parts.append(f"pH cercano a neutro ({top.ph:.1f})")
        elif top.ph < 8.5:
            parts.append(f"ligeramente alcalino (pH {top.ph:.1f})")
        else:
            parts.append(f"alcalino (pH {top.ph:.1f})")
    if top.soc_g_per_kg is not None:
        if top.soc_g_per_kg < 5:
            parts.append(
                f"baja materia orgánica (SOC {top.soc_g_per_kg:.1f} g/kg)"
            )
        elif top.soc_g_per_kg < 15:
            parts.append(
                f"materia orgánica moderada (SOC {top.soc_g_per_kg:.1f} g/kg)"
            )
        else:
            parts.append(
                f"alta materia orgánica (SOC {top.soc_g_per_kg:.1f} g/kg)"
            )
    if top.texture_class:
        parts.append(f"textura {top.texture_class}")
    if not parts:
        return "Sin datos suficientes para interpretar el perfil de suelo."
    return "Horizonte superficial (0-5 cm): " + "; ".join(parts) + "."


def _horizon_is_empty(fields: dict[str, float | None]) -> bool:
    return all(v is None for v in fields.values())


class SoilGridsSoilProvider:
    """ISRIC SoilGrids adapter for the SoilProvider port."""

    def __init__(self, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS):
        self._timeout = timeout_seconds

    async def get_profile(self, lat: float, lon: float) -> SoilResponse | None:
        params: list[tuple[str, Any]] = [
            ("lat", lat),
            ("lon", lon),
            ("value", VALUE),
        ]
        for p in PROPERTIES:
            params.append(("property", p))
        for d in DEPTHS:
            params.append(("depth", d))

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(SOILGRIDS_URL, params=params)
            response.raise_for_status()
            data = response.json()

        layers = (data.get("properties") or {}).get("layers") or []
        if not layers:
            return None

        horizons_data: dict[str, dict[str, float | None]] = {
            d: {field: None for field in PROPERTY_TO_FIELD.values()}
            for d in DEPTHS
        }

        for layer in layers:
            name = layer.get("name")
            field = PROPERTY_TO_FIELD.get(name)
            if field is None:
                continue
            d_factor = (layer.get("unit_measure") or {}).get("d_factor") or 1
            for depth_entry in layer.get("depths") or []:
                label = depth_entry.get("label")
                if label not in horizons_data:
                    continue
                raw = (depth_entry.get("values") or {}).get(VALUE)
                horizons_data[label][field] = (
                    None if raw is None else raw / d_factor
                )

        if all(_horizon_is_empty(f) for f in horizons_data.values()):
            return None

        horizons: list[SoilHorizon] = []
        for depth_label in DEPTHS:
            fields = horizons_data[depth_label]
            horizons.append(
                SoilHorizon(
                    depth=depth_label,
                    ph=fields["ph"],
                    soc_g_per_kg=fields["soc_g_per_kg"],
                    nitrogen_g_per_kg=fields["nitrogen_g_per_kg"],
                    clay_pct=fields["clay_pct"],
                    sand_pct=fields["sand_pct"],
                    silt_pct=fields["silt_pct"],
                    cec_mmol_per_kg=fields["cec_mmol_per_kg"],
                    texture_class=_usda_texture(
                        fields["sand_pct"],
                        fields["silt_pct"],
                        fields["clay_pct"],
                    ),
                )
            )

        top = horizons[0]
        return SoilResponse(
            lat=lat,
            lon=lon,
            horizons=horizons,
            dominant_texture=top.texture_class,
            interpretation=_interpret(top),
        )
