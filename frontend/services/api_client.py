"""
frontend/services/api_client.py
---------------------------------
Thin wrapper around requests for all calls to the FastAPI backend.
Centralises base URL, error handling, and timeout configuration.
"""

from __future__ import annotations
import os
import requests
from requests.exceptions import RequestException

import streamlit as st

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_V1   = f"{BASE_URL}/api/v1"
TIMEOUT  = 120  # seconds — embedding can be slow on first run


def _handle(response: requests.Response) -> dict | list:
    try:
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        st.error(f"API error {response.status_code}: {detail}")
        st.stop()
    except RequestException as e:
        st.error(f"Could not reach backend at {BASE_URL}. Is it running?\n\n{e}")
        st.stop()


# ── Health ────────────────────────────────────────────────────────────────────

def get_health() -> dict:
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        return r.json()
    except Exception:
        return {"status": "unreachable", "database": False, "redis": False,
                "chroma": False, "embedding_model_loaded": False}


# ── Resumes ───────────────────────────────────────────────────────────────────

def upload_resumes(files: list) -> list[dict]:
    """files: list of (filename, bytes, mime_type) tuples."""
    file_tuples = [("files", (name, data, mime)) for name, data, mime in files]
    r = requests.post(f"{API_V1}/resumes/upload", files=file_tuples, timeout=TIMEOUT)
    return _handle(r)


def list_resumes() -> list[dict]:
    r = requests.get(f"{API_V1}/resumes", timeout=TIMEOUT)
    return _handle(r)


def get_resume(resume_id: str) -> dict:
    r = requests.get(f"{API_V1}/resumes/{resume_id}", timeout=TIMEOUT)
    return _handle(r)


def delete_resume(resume_id: str) -> None:
    requests.delete(f"{API_V1}/resumes/{resume_id}", timeout=TIMEOUT)


# ── Job Descriptions ──────────────────────────────────────────────────────────

def create_jd(text: str, title: str | None = None, source: str = "custom") -> dict:
    payload = {"text": text, "source": source}
    if title:
        payload["title"] = title
    r = requests.post(f"{API_V1}/jds", json=payload, timeout=TIMEOUT)
    return _handle(r)


def upload_jd_file(filename: str, data: bytes, mime: str, source: str = "custom") -> dict:
    r = requests.post(
        f"{API_V1}/jds/upload",
        files={"file": (filename, data, mime)},
        params={"source": source},
        timeout=TIMEOUT,
    )
    return _handle(r)


def list_jds() -> list[dict]:
    r = requests.get(f"{API_V1}/jds", timeout=TIMEOUT)
    return _handle(r)


def get_jd(jd_id: str) -> dict:
    r = requests.get(f"{API_V1}/jds/{jd_id}", timeout=TIMEOUT)
    return _handle(r)


# ── Ranking ───────────────────────────────────────────────────────────────────

def rank_resumes(
    jd_id: str,
    resume_ids: list[str] | None = None,
    weights: dict | None = None,
    top_k: int | None = None,
    use_hybrid: bool = True,
) -> dict:
    payload: dict = {
        "job_description_id": jd_id,
        "use_hybrid_search": use_hybrid,
    }
    if resume_ids:
        payload["resume_ids"] = resume_ids
    if weights:
        payload["weights"] = weights
    if top_k:
        payload["top_k"] = top_k
    r = requests.post(f"{API_V1}/ranking/rank", json=payload, timeout=TIMEOUT)
    return _handle(r)


def get_ranking(ranking_job_id: str) -> dict:
    r = requests.get(f"{API_V1}/ranking/{ranking_job_id}", timeout=TIMEOUT)
    return _handle(r)


# ── Feedback ──────────────────────────────────────────────────────────────────

def get_feedback(resume_id: str, jd_id: str) -> dict:
    r = requests.get(f"{API_V1}/feedback/{resume_id}/{jd_id}", timeout=TIMEOUT)
    return _handle(r)


def get_llm_feedback(resume_id: str, jd_id: str, regenerate: bool = False) -> dict:
    payload = {"resume_id": resume_id, "job_description_id": jd_id, "regenerate": regenerate}
    r = requests.post(f"{API_V1}/feedback/llm", json=payload, timeout=TIMEOUT)
    return _handle(r)


# ── Evaluation ────────────────────────────────────────────────────────────────

def compute_metrics(ranking_job_id: str, relevant_ids: list[str], k_values: list[int]) -> dict:
    payload = {
        "ranking_job_id": ranking_job_id,
        "relevant_resume_ids": relevant_ids,
        "k_values": k_values,
    }
    r = requests.post(f"{API_V1}/evaluation/metrics", json=payload, timeout=TIMEOUT)
    return _handle(r)


def compare_resumes(ranking_job_id: str, id_a: str, id_b: str) -> dict:
    payload = {"ranking_job_id": ranking_job_id, "resume_id_a": id_a, "resume_id_b": id_b}
    r = requests.post(f"{API_V1}/evaluation/compare", json=payload, timeout=TIMEOUT)
    return _handle(r)
