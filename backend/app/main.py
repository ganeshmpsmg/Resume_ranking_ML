"""
app/main.py
------------
FastAPI application factory.

Startup sequence:
  1. Configure structured logging
  2. Pre-warm the SBERT embedding model
  3. Ensure database tables exist
  4. Initialize LanceDB
  5. Register all API routers

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ───────────── Startup ─────────────

    logger.info(f"Starting {settings.APP_NAME} [{settings.APP_ENV}]")

    # Create database tables
    from app.db.session import engine
    from app.models.orm_models import Base

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created.")

    # Load SBERT model
    from app.services.embedding_service import EmbeddingService

    try:
        EmbeddingService.load()
        logger.info("Embedding model loaded successfully.")
    except Exception as exc:
        logger.error(f"Could not load embedding model: {exc}")

    # Initialize LanceDB
    try:
        from app.db.lancedb_client import table

        logger.info(f"LanceDB table ready: {table.name}")
    except Exception as exc:
        logger.error(f"Could not initialize LanceDB: {exc}")

    logger.info("Application startup complete.")

    yield

    # ───────────── Shutdown ─────────────

    logger.info("Application shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "AI-powered Resume Ranking API using "
        "Sentence Transformers + LanceDB + FastAPI."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers

from app.api.routes import (
    health,
    resumes,
    job_descriptions,
    ranking,
    feedback,
    evaluation,
)

app.include_router(health.router)
app.include_router(resumes.router, prefix=settings.API_V1_PREFIX)
app.include_router(job_descriptions.router, prefix=settings.API_V1_PREFIX)
app.include_router(ranking.router, prefix=settings.API_V1_PREFIX)
app.include_router(feedback.router, prefix=settings.API_V1_PREFIX)
app.include_router(evaluation.router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "vector_database": "LanceDB",
    }
