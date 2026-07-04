"""
app/db/session.py
-------------------
SQLAlchemy engine, session factory, and FastAPI dependency for DB access.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings
@property
def sqlalchemy_database_url(self) -> str:
    if self.DATABASE_URL:
        return self.DATABASE_URL

    return f"sqlite:///{BASE_DIR / 'data' / 'resume_ranking.db'}"

# SQLite needs check_same_thread=False
if settings.sqlalchemy_database_url.startswith("sqlite"):
    engine = create_engine(
        settings.sqlalchemy_database_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        settings.sqlalchemy_database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
