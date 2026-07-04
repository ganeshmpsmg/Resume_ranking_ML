from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
import numpy as np

# Corrected imports for services
from app.services.search_service import hybrid_search
from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.embedding_service import EmbeddingService
from app.services.skill_service import extract_skills, skill_match_score
from app.schemas.schemas import RankedCandidate, RankResponse, RankingWeights

logger = get_logger(__name__)

# ─── Individual component scorers ────────────────────────────────────────────

def _experience_score(resume_years: float, jd_min_years: float) -> float:
    if jd_min_years <= 0:
        return 1.0
    if resume_years >= jd_min_years:
        return 1.0
    return max(0.0, resume_years / jd_min_years)

def _education_score(resume_rank: int, jd_required_rank: int) -> float:
    if jd_required_rank <= 0:
        return 1.0
    if resume_rank >= jd_required_rank:
        return 1.0
    if resume_rank == 0:
        return 0.0
    return max(0.0, resume_rank / jd_required_rank)

def _project_relevance(project_text: str, jd_embedding: np.ndarray) -> float:
    if not project_text or not project_text.strip():
        return 0.0
    proj_emb = np.array(EmbeddingService.encode_single(project_text))
    jd_emb = np.array(jd_embedding)
    sim = float(np.dot(proj_emb, jd_emb))
    return max(0.0, min(1.0, sim))

def _confidence(score: float) -> str:
    if score >= 0.75:
        return "High"
    elif score >= 0.50:
        return "Medium"
    return "Low"

@dataclass
class ResumeCandidate:
    resume_id: str
    vector_id: str
    name: str
    filename: str
    raw_text: str
    skills: list[str]
    years_experience: float
    education_rank: int
    education_level: str | None
    sections: dict = field(default_factory=dict)

# ─── Main ranking function ───────────────────────────────────────────────────

def rank_candidates(
    candidates: list[ResumeCandidate],
    jd_text: str,
    jd_skills: list[str],
    jd_min_experience: float,
    jd_edu_rank: int,
    jd_id: str,
    weights: RankingWeights | None = None,
    use_hybrid: bool = True,
    top_k: int | None = None,
) -> RankResponse:
    t0 = time.time()
    if weights is None:
        weights = RankingWeights()

    w = {
        "semantic_similarity": weights.semantic_similarity,
        "skill_match": weights.skill_match,
        "experience_match": weights.experience_match,
        "education_match": weights.education_match,
        "project_relevance": weights.project_relevance,
    }
    total_w = sum(w.values())
    if total_w > 0:
        w = {k: v / total_w for k, v in w.items()}

    if not candidates:
        return RankResponse(
            ranking_job_id=str(uuid.uuid4()),
            job_description_id=jd_id,
            job_title="",
            num_resumes=0,
            weights=weights,
            results=[],
            elapsed_seconds=0.0,
        )

    jd_embedding = np.array(EmbeddingService.encode_single(jd_text))
    candidate_ids = [c.vector_id for c in candidates]

    # Use the robust hybrid_search from search_service.py
    if use_hybrid:
        hybrid_scores_list = hybrid_search(
            query_embedding=jd_embedding.tolist(),
            query_text=jd_text,
            candidate_ids=candidate_ids,
            top_k=len(candidates),
        )
        sem_scores: dict[str, float] = {doc_id: score for doc_id, score in hybrid_scores_list}
    else:
        # Fallback if hybrid search is disabled
        texts = [c.raw_text for c in candidates]
        resume_embeddings = EmbeddingService.encode(texts)
        sims = EmbeddingService.cosine_similarity(resume_embeddings, jd_embedding)
        sem_scores = {c.vector_id: float(sim) for c, sim in zip(candidates, sims)}

    results: list[RankedCandidate] = []

    for cand in candidates:
        sem_sim = sem_scores.get(cand.vector_id, 0.0)
        sections = cand.sections or {}
        skill_result = skill_match_score(cand.skills, jd_skills)
        exp_score = _experience_score(cand.years_experience, jd_min_experience)
        edu_score = _education_score(cand.education_rank, jd_edu_rank)
        proj_score = _project_relevance(sections.get("projects", ""), jd_embedding)

        final = (
            w["semantic_similarity"] * sem_sim
            + w["skill_match"]       * skill_result.get("score", 0.0)
            + w["experience_match"]  * exp_score
            + w["education_match"]   * edu_score
            + w["project_relevance"] * proj_score
        )

        results.append(
            RankedCandidate(
                resume_id=cand.resume_id,
                name=cand.name or "Unknown",
                filename=cand.filename,
                final_score=round(final, 4),
                confidence=_confidence(final),
                semantic_similarity=round(sem_sim, 4),
                skill_match=round(skill_result.get("score", 0.0), 4),
                experience_match=round(exp_score, 4),
                education_match=round(edu_score, 4),
                project_relevance=round(proj_score, 4),
                matching_skills=skill_result.get("matching", []),
                missing_skills=skill_result.get("missing", []),
                extra_skills=skill_result.get("extra", []),
                years_experience=cand.years_experience,
                education_level=cand.education_level,
            )
        )

    results.sort(key=lambda r: r.final_score, reverse=True)
    if top_k:
        results = results[:top_k]

    return RankResponse(
        ranking_job_id=str(uuid.uuid4()),
        job_description_id=jd_id,
        job_title="",
        num_resumes=len(candidates),
        weights=weights,
        results=results,
        elapsed_seconds=round(time.time() - t0, 3),
    )