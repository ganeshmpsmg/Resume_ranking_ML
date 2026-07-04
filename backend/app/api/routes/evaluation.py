"""
app/api/routes/evaluation.py
------------------------------
Evaluation and resume-comparison endpoints:
  POST /evaluation/metrics  – Compute Precision@K / Recall@K / MRR
  POST /evaluation/compare  – Side-by-side resume comparison
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.orm_models import Resume, RankingJob, RankingResult, JobDescription
from app.schemas.schemas import (
    EvaluationRequest, EvaluationResponse,
    CompareRequest, CompareResponse, RankedCandidate,
)
from app.services.evaluation_service import evaluate

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


@router.post("/metrics", response_model=EvaluationResponse, summary="Compute ranking quality metrics")
def compute_metrics(payload: EvaluationRequest, db: Session = Depends(get_db)):
    job = db.query(RankingJob).filter(RankingJob.id == payload.ranking_job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Ranking job not found.")

    results = (
        db.query(RankingResult)
        .filter(RankingResult.ranking_job_id == payload.ranking_job_id)
        .order_by(RankingResult.final_score.desc())
        .all()
    )
    ranked_ids   = [str(r.resume_id) for r in results]
    cosine_scores = [r.semantic_similarity for r in results]
    relevant_set  = set(payload.relevant_resume_ids)

    metrics = evaluate(
        ranked_ids=ranked_ids,
        relevant=relevant_set,
        k_values=payload.k_values,
        cosine_scores=cosine_scores,
    )
    return EvaluationResponse(
        mrr=metrics["mrr"],
        metrics=metrics["metrics"],
        average_cosine_similarity=metrics["average_cosine_similarity"],
    )


@router.post("/compare", response_model=CompareResponse, summary="Side-by-side resume comparison")
def compare_resumes(payload: CompareRequest, db: Session = Depends(get_db)):
    def _get_result(resume_id: str) -> RankingResult | None:
        return (
            db.query(RankingResult)
            .filter(
                RankingResult.ranking_job_id == payload.ranking_job_id,
                RankingResult.resume_id == resume_id,
            )
            .first()
        )

    def _build_candidate(result: RankingResult) -> RankedCandidate:
        resume = db.query(Resume).filter(Resume.id == result.resume_id).first()
        return RankedCandidate(
            resume_id=str(result.resume_id),
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

    result_a = _get_result(payload.resume_id_a)
    result_b = _get_result(payload.resume_id_b)

    if not result_a:
        raise HTTPException(status_code=404, detail=f"No result for resume_id_a in this ranking job.")
    if not result_b:
        raise HTTPException(status_code=404, detail=f"No result for resume_id_b in this ranking job.")

    cand_a = _build_candidate(result_a)
    cand_b = _build_candidate(result_b)

    skills_a = set(cand_a.matching_skills + cand_a.extra_skills)
    skills_b = set(cand_b.matching_skills + cand_b.extra_skills)

    winner = cand_a.resume_id if cand_a.final_score >= cand_b.final_score else cand_b.resume_id

    return CompareResponse(
        candidate_a=cand_a,
        candidate_b=cand_b,
        only_a_skills=sorted(skills_a - skills_b),
        only_b_skills=sorted(skills_b - skills_a),
        common_skills=sorted(skills_a & skills_b),
        winner_resume_id=winner,
    )
