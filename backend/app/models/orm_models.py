"""
app/models/orm_models.py
--------------------------
SQLAlchemy ORM models persisted to Postgres:
  - Resume: parsed resume metadata + extracted fields
  - JobDescription: parsed JD metadata + requirements
  - RankingJob: a single "rank these resumes against this JD" run
  - RankingResult: per-resume score for a given RankingJob
  - FeedbackRecord: cached LLM/rule-based feedback for a resume+JD pair
"""

from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, JSON, Text, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    filename = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    linkedin = Column(String(255), nullable=True)
    github = Column(String(255), nullable=True)
    raw_text = Column(Text, nullable=False)
    sections = Column(JSON, default=dict)
    skills = Column(JSON, default=list)
    skills_by_category = Column(JSON, default=dict)
    years_experience = Column(Float, default=0.0)
    education_level = Column(String(50), nullable=True)
    education_rank = Column(Integer, default=0)
    vector_id = Column(String(64), nullable=True)  # Chroma document id
    created_at = Column(DateTime, default=datetime.utcnow)

    results = relationship("RankingResult", back_populates="resume",
                            cascade="all, delete-orphan")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    required_skills = Column(JSON, default=list)
    skills_by_category = Column(JSON, default=dict)
    min_experience_years = Column(Float, default=0.0)
    required_education = Column(String(50), nullable=True)
    required_education_rank = Column(Integer, default=0)
    source = Column(String(50), default="custom")  # custom | linkedin | naukri
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("RankingJob", back_populates="job_description",
                         cascade="all, delete-orphan")


class RankingJob(Base):
    """Represents one ranking run: N resumes scored against one JD."""
    __tablename__ = "ranking_jobs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_description_id = Column(UUID(as_uuid=False), ForeignKey("job_descriptions.id"))
    weights = Column(JSON, default=dict)
    num_resumes = Column(Integer, default=0)
    status = Column(String(20), default="completed")  # pending|running|completed|failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    job_description = relationship("JobDescription", back_populates="jobs")
    results = relationship("RankingResult", back_populates="ranking_job",
                            cascade="all, delete-orphan")


class RankingResult(Base):
    __tablename__ = "ranking_results"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    ranking_job_id = Column(UUID(as_uuid=False), ForeignKey("ranking_jobs.id"))
    resume_id = Column(UUID(as_uuid=False), ForeignKey("resumes.id"))

    final_score = Column(Float, nullable=False)
    confidence = Column(String(10))  # High | Medium | Low
    semantic_similarity = Column(Float)
    skill_match = Column(Float)
    experience_match = Column(Float)
    education_match = Column(Float)
    project_relevance = Column(Float)

    matching_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    extra_skills = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)

    ranking_job = relationship("RankingJob", back_populates="results")
    resume = relationship("Resume", back_populates="results")


class FeedbackRecord(Base):
    """Cached resume feedback (rule-based and/or LLM-generated)."""
    __tablename__ = "feedback_records"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    resume_id = Column(UUID(as_uuid=False), ForeignKey("resumes.id"))
    job_description_id = Column(UUID(as_uuid=False), ForeignKey("job_descriptions.id"))

    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    ats_score = Column(Float, default=0.0)
    ats_breakdown = Column(JSON, default=dict)

    llm_generated = Column(Boolean, default=False)
    llm_feedback_text = Column(Text, nullable=True)
    llm_model = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
