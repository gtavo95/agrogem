from fastapi import FastAPI

from config import lifespan
from domain.chat.router import router as chat_router
from domain.climate.router import router as climate_router
from domain.disease_risk.router import router as disease_risk_router
from domain.elevation.router import router as elevation_router
from domain.gbif.router import router as gbif_router
from domain.geocoding.router import router as geocoding_router
from domain.pest.router import router as pest_router
from domain.pest_risk.router import router as pest_risk_router
from domain.session.router import router as session_router
from domain.soil.router import router as soil_router
from domain.user.router import router as user_router
from domain.weather.router import router as weather_router

app = FastAPI(lifespan=lifespan)
app.include_router(user_router)
app.include_router(session_router)
app.include_router(chat_router)
app.include_router(weather_router)
app.include_router(gbif_router)
app.include_router(geocoding_router)
app.include_router(soil_router)
app.include_router(pest_router)
app.include_router(pest_risk_router)
app.include_router(elevation_router)
app.include_router(climate_router)
app.include_router(disease_risk_router)
