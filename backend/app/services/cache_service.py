"""
app/services/cache_service.py
------------------------------
Redis-backed caching layer for ranking results and feedback records.

Key naming convention:
  rank:<job_description_id>:<sorted_resume_ids_hash>  → RankResponse JSON
  feedback:<resume_id>:<job_description_id>           → FeedbackOut JSON
  health:redis                                         → "ok"

TTL defaults to settings.CACHE_TTL_SECONDS (1 hour).
The cache degrades gracefully: on any Redis error the operation is logged
and execution continues without caching (never raises to caller).
"""

from __future__ import annotations
import hashlib
import json
from typing import Any

import redis

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_redis_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


def redis_is_ready() -> bool:
    try:
        return _get_client().ping()
    except Exception:
        return False


def _safe(fn, *args, default=None, **kwargs):
    """Run a Redis operation and swallow any exception, returning default."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.warning(f"Redis operation failed (non-fatal): {exc}")
        return default


# ─── Key builders ─────────────────────────────────────────────────────────────

def _rank_key(jd_id: str, resume_ids: list[str]) -> str:
    ids_hash = hashlib.md5("|".join(sorted(resume_ids)).encode()).hexdigest()[:12]
    return f"rank:{jd_id}:{ids_hash}"


def _feedback_key(resume_id: str, jd_id: str) -> str:
    return f"feedback:{resume_id}:{jd_id}"


# ─── Ranking cache ────────────────────────────────────────────────────────────

def get_ranking(jd_id: str, resume_ids: list[str]) -> dict | None:
    key = _rank_key(jd_id, resume_ids)
    raw = _safe(_get_client().get, key)
    if raw:
        logger.debug(f"Cache HIT: {key}")
        return json.loads(raw)
    logger.debug(f"Cache MISS: {key}")
    return None


def set_ranking(jd_id: str, resume_ids: list[str], data: dict, ttl: int | None = None) -> None:
    key = _rank_key(jd_id, resume_ids)
    _safe(
        _get_client().setex,
        key,
        ttl or settings.CACHE_TTL_SECONDS,
        json.dumps(data, default=str),
    )


def invalidate_ranking(jd_id: str) -> None:
    """Delete all ranking cache entries for a given JD (e.g. after new resume upload)."""
    pattern = f"rank:{jd_id}:*"
    keys = _safe(_get_client().keys, pattern, default=[])
    if keys:
        _safe(_get_client().delete, *keys)
        logger.debug(f"Invalidated {len(keys)} ranking cache entries for JD {jd_id}")


# ─── Feedback cache ───────────────────────────────────────────────────────────

def get_feedback(resume_id: str, jd_id: str) -> dict | None:
    key = _feedback_key(resume_id, jd_id)
    raw = _safe(_get_client().get, key)
    return json.loads(raw) if raw else None


def set_feedback(resume_id: str, jd_id: str, data: dict, ttl: int | None = None) -> None:
    key = _feedback_key(resume_id, jd_id)
    _safe(
        _get_client().setex,
        key,
        ttl or settings.CACHE_TTL_SECONDS,
        json.dumps(data, default=str),
    )


def delete_feedback(resume_id: str, jd_id: str) -> None:
    key = _feedback_key(resume_id, jd_id)
    _safe(_get_client().delete, key)
