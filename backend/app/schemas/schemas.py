"""
app/schemas/schemas.py
------------------------
Pydantic models defining the FastAPI request/response contracts.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# --------------------------------------------------------------------------
# Resume
# --------------------------------------------------------------------------
class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    skills: list[str] = Field(default_factory=list)
    skills_by_category: dict[str, list[str]] = Field(default_factory=dict)
    years_experience: float = 0.0
    education_level: str | None = None
    created_at: datetime | None = None


class ResumeDetailOut(ResumeOut):
    raw_text: str
    sections: dict[str, str] = Field(default_factory=dict)


# --------------------------------------------------------------------------
# Job Description
# --------------------------------------------------------------------------
class JobDescriptionCreate(BaseModel):
    text: str = Field(..., min_length=20, description="Raw job description text")
    title: str | None = None
    source: str = Field(default="custom", description="custom | linkedin | naukri")


class JobDescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    required_skills: list[str] = Field(default_factory=list)
    skills_by_category: dict[str, list[str]] = Field(default_factory=dict)
    min_experience_years: float = 0.0
    required_education: str | None = None
    source: str = "custom"
    created_at: datetime | None = None


class JobDescriptionDetailOut(JobDescriptionOut):
    raw_text: str


# --------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------
class RankingWeights(BaseModel):
    semantic_similarity: float = 0.40
    skill_match: float = 0.25
    experience_match: float = 0.20
    education_match: float = 0.10
    project_relevance: float = 0.05


class RankRequest(BaseModel):
    job_description_id: str
    resume_ids: list[str] | None = Field(
        default=None,
        description="If omitted, ranks ALL resumes currently stored.",
    )
    weights: RankingWeights | None = None
    top_k: int | None = None
    use_hybrid_search: bool = Field(
        default=True,
        description="Combine vector similarity (Chroma) with BM25 keyword search.",
    )


class RankedCandidate(BaseModel):
    resume_id: str
    name: str
    filename: str
    final_score: float
    confidence: str
    semantic_similarity: float
    skill_match: float
    experience_match: float
    education_match: float
    project_relevance: float
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    extra_skills: list[str] = Field(default_factory=list)
    years_experience: float = 0.0
    education_level: str | None = None


class RankResponse(BaseModel):
    ranking_job_id: str
    job_description_id: str
    job_title: str
    num_resumes: int
    weights: RankingWeights
    results: list[RankedCandidate]
    elapsed_seconds: float
    cached: bool = False


# --------------------------------------------------------------------------
# Recommendation / Feedback
# --------------------------------------------------------------------------
class FeedbackOut(BaseModel):
    resume_id: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    ats_score: float
    ats_breakdown: dict[str, float] = Field(default_factory=dict)
    llm_generated: bool = False
    llm_feedback_text: str | None = None


class LLMFeedbackRequest(BaseModel):
    resume_id: str
    job_description_id: str
    regenerate: bool = False


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------
class EvaluationRequest(BaseModel):
    ranking_job_id: str
    relevant_resume_ids: list[str]
    k_values: list[int] = Field(default_factory=lambda: [3, 5, 10])


class EvaluationResponse(BaseModel):
    mrr: float
    metrics: dict[str, float]
    average_cosine_similarity: float


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------
class CompareRequest(BaseModel):
    ranking_job_id: str
    resume_id_a: str
    resume_id_b: str


class CompareResponse(BaseModel):
    candidate_a: RankedCandidate
    candidate_b: RankedCandidate
    only_a_skills: list[str]
    only_b_skills: list[str]
    common_skills: list[str]
    winner_resume_id: str


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    database: bool
    redis: bool
    chroma: bool
    embedding_model_loaded: bool
