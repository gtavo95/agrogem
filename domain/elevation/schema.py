from pydantic import BaseModel, ConfigDict


class ElevationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lat: float
    lon: float
    elevation_m: float
    interpretation: str = ""
