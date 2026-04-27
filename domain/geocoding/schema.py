from pydantic import BaseModel, ConfigDict


class GeocodeResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lat: float
    lon: float
    display_name: str
    country_code: str | None = None
    state: str | None = None
    municipality: str | None = None
    type: str | None = None
    interpretation: str = ""


class ReverseGeocodeResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lat: float
    lon: float
    display_name: str
    country_code: str | None = None
    state: str | None = None
    municipality: str | None = None
    type: str | None = None
    interpretation: str = ""
