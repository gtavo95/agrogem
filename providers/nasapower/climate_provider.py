from typing import Any

import httpx

from domain.climate.schema import (
    ClimateHistoryResponse,
    ClimatePoint,
    Granularity,
)


NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal"
REQUEST_TIMEOUT_SECONDS = 30.0
COMMUNITY = "AG"

PARAMETERS = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
]

SENTINEL_MISSING = -999.0


def _clean(value: Any) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v <= SENTINEL_MISSING:
        return None
    return v


def _format_date(raw_key: str, granularity: Granularity) -> str:
    """POWER returns daily keys as YYYYMMDD and monthly as YYYYMM (+ annual aggregates like '13')."""
    if granularity == "daily" and len(raw_key) == 8:
        return f"{raw_key[0:4]}-{raw_key[4:6]}-{raw_key[6:8]}"
    if granularity == "monthly" and len(raw_key) == 6:
        return f"{raw_key[0:4]}-{raw_key[4:6]}"
    return raw_key


def _is_monthly_annual_bucket(raw_key: str) -> bool:
    """POWER's monthly endpoint includes an annual aggregate keyed 'YYYY13'; skip it."""
    return len(raw_key) == 6 and raw_key.endswith("13")


class NasaPowerClimateProvider:
    """NASA POWER adapter for the ClimateHistoryProvider port."""

    def __init__(self, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS):
        self._timeout = timeout_seconds

    async def get(
        self,
        lat: float,
        lon: float,
        start: str,
        end: str,
        granularity: Granularity,
    ) -> ClimateHistoryResponse | None:
        start_compact = start.replace("-", "")
        end_compact = end.replace("-", "")
        params = {
            "parameters": ",".join(PARAMETERS),
            "community": COMMUNITY,
            "latitude": lat,
            "longitude": lon,
            "start": start_compact,
            "end": end_compact,
            "format": "JSON",
        }
        url = f"{NASA_POWER_BASE_URL}/{granularity}/point"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        parameter_block = (
            data.get("properties") or {}
        ).get("parameter") or {}
        if not parameter_block:
            return None

        t2m_series = parameter_block.get("T2M") or {}
        if not t2m_series:
            return None

        keys = sorted(
            k for k in t2m_series.keys()
            if not (granularity == "monthly" and _is_monthly_annual_bucket(k))
        )

        series: list[ClimatePoint] = []
        for key in keys:
            series.append(
                ClimatePoint(
                    date=_format_date(key, granularity),
                    t2m=_clean(parameter_block.get("T2M", {}).get(key)),
                    t2m_max=_clean(parameter_block.get("T2M_MAX", {}).get(key)),
                    t2m_min=_clean(parameter_block.get("T2M_MIN", {}).get(key)),
                    precipitation_mm=_clean(
                        parameter_block.get("PRECTOTCORR", {}).get(key)
                    ),
                    rh_pct=_clean(parameter_block.get("RH2M", {}).get(key)),
                    solar_mj_m2=_clean(
                        parameter_block.get("ALLSKY_SFC_SW_DWN", {}).get(key)
                    ),
                )
            )

        if not series:
            return None

        return ClimateHistoryResponse(
            lat=lat,
            lon=lon,
            granularity=granularity,
            start=start,
            end=end,
            series=series,
        )
