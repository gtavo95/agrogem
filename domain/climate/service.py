from domain.climate.cache import ClimateHistoryCache
from domain.climate.provider import ClimateHistoryProvider
from domain.climate.schema import ClimateHistoryResponse, Granularity


def _interpret(r: ClimateHistoryResponse) -> str:
    if not r.series:
        return f"Sin datos disponibles para {r.start} a {r.end}."
    label = "diario" if r.granularity == "daily" else "mensual"
    parts = [
        f"Histórico {label} de {r.start} a {r.end} ({len(r.series)} puntos)."
    ]
    temps = [p.t2m for p in r.series if p.t2m is not None]
    precs = [
        (p.date, p.precipitation_mm)
        for p in r.series
        if p.precipitation_mm is not None
    ]
    if temps:
        avg_t = sum(temps) / len(temps)
        parts.append(f"T° media {avg_t:.1f}°C.")
    if precs:
        total_p = sum(p for _, p in precs)
        wettest_date, wettest_p = max(precs, key=lambda x: x[1])
        parts.append(
            f"Precipitación total {total_p:.0f} mm; "
            f"periodo más lluvioso: {wettest_date} ({wettest_p:.0f} mm)."
        )
    return " ".join(parts)


async def fetch_climate_history(
    provider: ClimateHistoryProvider,
    cache: ClimateHistoryCache,
    lat: float,
    lon: float,
    start: str,
    end: str,
    granularity: Granularity,
) -> ClimateHistoryResponse | None:
    cached = await cache.get(lat, lon, start, end, granularity)
    if cached is not None:
        cached.interpretation = _interpret(cached)
        return cached
    result = await provider.get(lat, lon, start, end, granularity)
    if result is None:
        return None
    result.interpretation = _interpret(result)
    await cache.set(lat, lon, start, end, granularity, result)
    return result
