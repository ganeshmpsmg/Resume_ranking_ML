"""
app/api/routes/ranking.py
---------------------------
Ranking endpoint:
  POST /ranking/rank  – Rank resumes against a JD (with Redis caching)
  GET  /ranking/{job_id}  – Retrieve a past ranking result from DB
"""

from __future__ import annotations
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.orm_models import Resume, JobDescription, RankingJob, RankingResult
from app.schemas.schemas import RankRequest, RankResponse, RankedCandidate, RankingWeights
from app.services.ranking_service import rank_candidates, ResumeCandidate
from app.services.cache_service import get_ranking, set_ranking

logger = get_logger(__name__)
router = APIRouter(prefix="/ranking", tags=["Ranking"])


@router.post("/rank", response_model=RankResponse, summary="Rank resumes against a job description")
def rank_resumes(payload: RankRequest, db: Session = Depends(get_db)):
    # ── Validate JD ──────────────────────────────────────────────────────
    jd = db.query(JobDescription).filter(JobDescription.id == payload.job_description_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found.")

    # ── Fetch resumes ─────────────────────────────────────────────────────
    q = db.query(Resume)
    if payload.resume_ids:
        q = q.filter(Resume.id.in_(payload.resume_ids))
    resumes = q.all()
    if not resumes:
        raise HTTPException(status_code=404, detail="No resumes found.")

    resume_ids = [str(r.id) for r in resumes]

    # ── Redis cache lookup ────────────────────────────────────────────────
    cached = get_ranking(jd.id, resume_ids)
    if cached:
        cached["cached"] = True
        return RankResponse(**cached)

    # ── Build candidate objects ───────────────────────────────────────────
    candidates = [
        ResumeCandidate(
            resume_id=str(r.id),
            vector_id=str(r.id),
            name=r.name or "Unknown",
            filename=r.filename,
            raw_text=r.raw_text,
            skills=r.skills or [],
            years_experience=r.years_experience or 0.0,
            education_rank=r.education_rank or 0,
            education_level=r.education_level,
            sections=r.sections or {},
        )
        for r in resumes
    ]

    # ── Run ranking ────────────────────────────────────────────────────────
    weights = payload.weights or RankingWeights()
    response = rank_candidates(
        candidates=candidates,
        jd_text=jd.raw_text,
        jd_skills=jd.required_skills or [],
        jd_min_experience=jd.min_experience_years or 0.0,
        jd_edu_rank=jd.required_education_rank or 0,
        jd_id=str(jd.id),
        weights=weights,
        use_hybrid=payload.use_hybrid_search,
        top_k=payload.top_k,
    )
    response.job_title = jd.title

    # ── Persist ranking job + results to DB ───────────────────────────────
    ranking_job = RankingJob(
        id=response.ranking_job_id,
        job_description_id=str(jd.id),
        weights=weights.model_dump(),
        num_resumes=len(candidates),
        status="completed",
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db.add(ranking_job)

    for rc in response.results:
        db.add(RankingResult(
            ranking_job_id=response.ranking_job_id,
            resume_id=rc.resume_id,
            final_score=rc.final_score,
            confidence=rc.confidence,
            semantic_similarity=rc.semantic_similarity,
            skill_match=rc.skill_match,
            experience_match=rc.experience_match,
            education_match=rc.education_match,
            project_relevance=rc.project_relevance,
            matching_skills=rc.matching_skills,
            missing_skills=rc.missing_skills,
            extra_skills=rc.extra_skills,
            created_at=datetime.utcnow(),
        ))
    db.commit()

    # ── Cache result ──────────────────────────────────────────────────────
    set_ranking(str(jd.id), resume_ids, response.model_dump())
    return response


@router.get(
    "/{ranking_job_id}",
    response_model=RankResponse,
    summary="Retrieve a past ranking result",
)
def get_ranking_result(ranking_job_id: str, db: Session = Depends(get_db)):
    job = db.query(RankingJob).filter(RankingJob.id == ranking_job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Ranking job not found.")

    jd = db.query(JobDescription).filter(JobDescription.id == job.job_description_id).first()
    results = (
        db.query(RankingResult)
        .filter(RankingResult.ranking_job_id == ranking_job_id)
        .all()
    )

    ranked_candidates = []
    for r in sorted(results, key=lambda x: x.final_score, reverse=True):
        resume = db.query(Resume).filter(Resume.id == r.resume_id).first()
        ranked_candidates.append(RankedCandidate(
            resume_id=str(r.resume_id),
            name=resume.name if resume else "Unknown",
            filename=resume.filename if resume else "",
            final_score=r.final_score,
            confidence=r.confidence,
            semantic_similarity=r.semantic_similarity,
            skill_match=r.skill_match,
            experience_match=r.experience_match,
            education_match=r.education_match,
            project_relevance=r.project_relevance,
            matching_skills=r.matching_skills or [],
            missing_skills=r.missing_skills or [],
            extra_skills=r.extra_skills or [],
            years_experience=resume.years_experience if resume else 0.0,
            education_level=resume.education_level if resume else None,
        ))

    return RankResponse(
        ranking_job_id=ranking_job_id,
        job_description_id=str(job.job_description_id),
        job_title=jd.title if jd else "",
        num_resumes=job.num_resumes,
        weights=RankingWeights(**job.weights),
        results=ranked_candidates,
        elapsed_seconds=0.0,
        cached=False,
    )
