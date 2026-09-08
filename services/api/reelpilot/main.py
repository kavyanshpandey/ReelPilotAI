from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from reelpilot.config import get_settings
from reelpilot.database import create_tables
from reelpilot.routers.analysis import router as analysis_router
from reelpilot.routers.auth import router as auth_router
from reelpilot.routers.content_packs import router as content_packs_router
from reelpilot.routers.health import router as health_router
from reelpilot.routers.imports import router as imports_router
from reelpilot.routers.instagram import router as instagram_router
from reelpilot.routers.usage import router as usage_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title=settings.name,
    version="0.1.0",
    description="Audience intelligence and Reel content-pack API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(imports_router)
app.include_router(instagram_router)
app.include_router(analysis_router)
app.include_router(content_packs_router)
app.include_router(usage_router)
