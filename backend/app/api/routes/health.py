"""
app/api/routes/health.py
--------------------------
Health-check endpoint — verifies connectivity to Postgres, Redis, Chroma,
and checks whether the SBERT model is loaded.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.services.cache_service import redis_is_ready
from app.db.lancedb_client import table
from app.services.embedding_service import EmbeddingService
from app.schemas.schemas import HealthResponse

router = APIRouter(tags=["Health"])


def lancedb_is_ready() -> bool:
    try:
        table.count_rows()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    # Postgres
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database=db_ok,
        redis=redis_is_ready(),
        chroma=lancedb_is_ready(),
        embedding_model_loaded=EmbeddingService.is_loaded(),
    )
