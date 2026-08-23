from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.router import api_router
from app.config import get_settings
from app.infra.db import create_db_and_tables

settings = get_settings()

TAGS_METADATA = [
    {"name": "system", "description": "Service and database health."},
    {"name": "auth", "description": "Strava OAuth login and session handling."},
    {"name": "groups", "description": "Create, join and inspect athlete groups."},
    {"name": "strava", "description": "Strava webhook subscription endpoints."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Strava Group Tracker",
    description=(
        "Backend API for tracking and comparing Strava activity across groups of athletes.\n\n"
        "Interactive docs: **/docs** (Swagger UI) · **/redoc** (ReDoc) · **/openapi.json** (raw schema)."
    ),
    version="0.1.0",
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True, "displayRequestDuration": True},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")
