"""
app/core/config.py
-------------------
Centralized application settings, loaded from environment variables / .env
via pydantic-settings. Import `settings` anywhere config values are needed.
"""

from __future__ import annotations
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

   


    # --- App ---
    APP_NAME: str = "Resume Ranking System API"
    APP_ENV: str = "development"  # development | production | test
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]
    
    # --- Chroma (keep temporarily if other files still use it) ---
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma")
    CHROMA_COLLECTION_RESUMES: str = "resumes"

    # --- LanceDB ---
    LANCEDB_PATH: str = str(BASE_DIR / "data" / "lancedb")


    # --- Postgres ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "resume_user"
    POSTGRES_PASSWORD: str = "resume_pass"
    POSTGRES_DB: str = "resume_ranking"
    DATABASE_URL: str | None = None  # if set, overrides the fields above

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        return f"sqlite:///{BASE_DIR / 'data' / 'resume_ranking.db'}"
        

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str | None = None
    CACHE_TTL_SECONDS: int = 3600

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- Chroma (vector DB) ---
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma")
    CHROMA_COLLECTION_RESUMES: str = "resumes"

    # --- Embeddings ---
    SBERT_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # --- Hybrid search weighting (vector vs BM25), used inside skill/semantic stage ---
    HYBRID_VECTOR_WEIGHT: float = 0.7
    HYBRID_BM25_WEIGHT: float = 0.3

    # --- Ranking weights (must sum to 1.0) ---
    WEIGHT_SEMANTIC_SIMILARITY: float = 0.40
    WEIGHT_SKILL_MATCH: float = 0.25
    WEIGHT_EXPERIENCE_MATCH: float = 0.20
    WEIGHT_EDUCATION_MATCH: float = 0.10
    WEIGHT_PROJECT_RELEVANCE: float = 0.05

    # --- LLM (bonus feedback feature only) ---
    OPENAI_API_KEY: str = Field(default="", description="Required only for /feedback/llm endpoint")
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_FEEDBACK_ENABLED: bool = False  # auto-enabled if OPENAI_API_KEY is set

    # --- File upload limits ---
    MAX_UPLOAD_MB: int = 10
    ALLOWED_RESUME_EXTENSIONS: list[str] = ["pdf", "docx", "doc", "txt"]

    # --- spaCy ---
    SPACY_MODEL: str = "en_core_web_sm"

    def model_post_init(self, __context) -> None:
        if self.OPENAI_API_KEY:
            object.__setattr__(self, "LLM_FEEDBACK_ENABLED", True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
