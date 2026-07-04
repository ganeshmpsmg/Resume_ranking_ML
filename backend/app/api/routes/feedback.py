"""
app/api/routes/feedback.py
----------------------------
Resume recommendation/feedback endpoints:
  GET  /feedback/{resume_id}/{jd_id}   – Rule-based feedback (cached)
  POST /feedback/llm                   – LLM-enhanced feedback (bonus)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.orm_models import Resume, JobDescription, RankingResult, FeedbackRecord
from app.schemas.schemas import FeedbackOut, LLMFeedbackRequest, RankedCandidate, RankingWeights
from app.services.recommendation_service import generate_rule_based_feedback
from app.services.llm_service import generate_llm_feedback
from app.services.cache_service import get_feedback, set_feedback, delete_feedback

logger = get_logger(__name__)
router = APIRouter(prefix="/feedback", tags=["Feedback"])


def _get_ranked_candidate(resume_id: str, jd_id: str, db: Session) -> RankedCandidate | None:
    """
    Look up the most recent RankingResult for this resume+JD pair and
    reconstruct a RankedCandidate for the feedback generators.
    """
    result = (
        db.query(RankingResult)
        .join(RankingResult.ranking_job)
        .filter(
            RankingResult.resume_id == resume_id,
        )
        .order_by(RankingResult.created_at.desc())
        .first()
    )
    if result is None:
        return None
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    return RankedCandidate(
        resume_id=str(resume_id),
        name=resume.name if resume else "Unknown",
        filename=resume.filename if resume else "",
        final_score=result.final_score,
        confidence=result.confidence,
        semantic_similarity=result.semantic_similarity,
        skill_match=result.skill_match,
        experience_match=result.experience_match,
        education_match=result.education_match,
        project_relevance=result.project_relevance,
        matching_skills=result.matching_skills or [],
        missing_skills=result.missing_skills or [],
        extra_skills=result.extra_skills or [],
        years_experience=resume.years_experience if resume else 0.0,
        education_level=resume.education_level if resume else None,
    )


@router.get(
    "/{resume_id}/{jd_id}",
    response_model=FeedbackOut,
    summary="Get rule-based resume feedback (ATS score, strengths, weaknesses, suggestions)",
)
def get_feedback_endpoint(
    resume_id: str,
    jd_id: str,
    db: Session = Depends(get_db),
):
    # Cache check
    cached = get_feedback(resume_id, jd_id)
    if cached:
        return FeedbackOut(**cached)

    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found.")

    ranked = _get_ranked_candidate(resume_id, jd_id, db)
    if ranked is None:
        raise HTTPException(
            status_code=404,
            detail="No ranking result found for this resume+JD pair. Run /ranking/rank first.",
        )

    feedback = generate_rule_based_feedback(
        raw_text=resume.raw_text,
        sections=resume.sections or {},
        ranked=ranked,
        jd_min_experience=jd.min_experience_years or 0.0,
        jd_edu_rank=jd.required_education_rank or 0,
    )

    # Persist to DB
    record = FeedbackRecord(
        resume_id=resume_id,
        job_description_id=jd_id,
        strengths=feedback.strengths,
        weaknesses=feedback.weaknesses,
        suggestions=feedback.suggestions,
        ats_score=feedback.ats_score,
        ats_breakdown=feedback.ats_breakdown,
        llm_generated=False,
    )
    db.add(record)
    db.commit()

    set_feedback(resume_id, jd_id, feedback.model_dump())
    return feedback


@router.post(
    "/llm",
    response_model=FeedbackOut,
    summary="Generate LLM-enhanced feedback using OpenAI (bonus feature)",
)
async def get_llm_feedback(
    payload: LLMFeedbackRequest,
    db: Session = Depends(get_db),
):
    if not settings.LLM_FEEDBACK_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="LLM feedback is disabled. Set OPENAI_API_KEY in your .env file.",
        )

    # Optionally return cached version
    if not payload.regenerate:
        cached = get_feedback(payload.resume_id, payload.job_description_id)
        if cached and cached.get("llm_generated"):
            return FeedbackOut(**cached)

    resume = db.query(Resume).filter(Resume.id == payload.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    jd = db.query(JobDescription).filter(JobDescription.id == payload.job_description_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found.")

    ranked = _get_ranked_candidate(payload.resume_id, payload.job_description_id, db)
    if ranked is None:
        raise HTTPException(status_code=404, detail="Run /ranking/rank first.")

    # Generate rule-based first as fallback base
    base = generate_rule_based_feedback(
        raw_text=resume.raw_text,
        sections=resume.sections or {},
        ranked=ranked,
        jd_min_experience=jd.min_experience_years or 0.0,
        jd_edu_rank=jd.required_education_rank or 0,
    )

    feedback = await generate_llm_feedback(
        resume_id=payload.resume_id,
        resume_text=resume.raw_text,
        jd_text=jd.raw_text,
        ranked=ranked,
        base_feedback=base,
    )

    # Persist + cache
    record = FeedbackRecord(
        resume_id=payload.resume_id,
        job_description_id=payload.job_description_id,
        strengths=feedback.strengths,
        weaknesses=feedback.weaknesses,
        suggestions=feedback.suggestions,
        ats_score=feedback.ats_score,
        ats_breakdown=feedback.ats_breakdown,
        llm_generated=True,
        llm_feedback_text=feedback.llm_feedback_text,
        llm_model=settings.OPENAI_MODEL,
    )
    db.add(record)
    db.commit()

    delete_feedback(payload.resume_id, payload.job_description_id)
    set_feedback(payload.resume_id, payload.job_description_id, feedback.model_dump())
    return feedback
