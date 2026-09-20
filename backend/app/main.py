from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import router
from app.cache import client, close_cache
from app.core.config import get_settings
from app.db import SessionLocal, engine
from app.models import Base
from app.scheduler import start_scheduler, stop_scheduler
from app.services.ingestion import pull_hazard_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await pull_hazard_data(session)
    start_scheduler()
    yield
    stop_scheduler()
    await close_cache()
    await engine.dispose()


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"]
)
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "PrithviNet API", "docs": "/docs", "health": "/api/v1/health"}
