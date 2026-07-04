"""001 initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("linkedin", sa.String(255)),
        sa.Column("github", sa.String(255)),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("sections", JSONB, default={}),
        sa.Column("skills", JSONB, default=[]),
        sa.Column("skills_by_category", JSONB, default={}),
        sa.Column("years_experience", sa.Float, default=0.0),
        sa.Column("education_level", sa.String(50)),
        sa.Column("education_rank", sa.Integer, default=0),
        sa.Column("vector_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "job_descriptions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("required_skills", JSONB, default=[]),
        sa.Column("skills_by_category", JSONB, default={}),
        sa.Column("min_experience_years", sa.Float, default=0.0),
        sa.Column("required_education", sa.String(50)),
        sa.Column("required_education_rank", sa.Integer, default=0),
        sa.Column("source", sa.String(50), default="custom"),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "ranking_jobs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("job_description_id", UUID(as_uuid=False),
                   sa.ForeignKey("job_descriptions.id")),
        sa.Column("weights", JSONB, default={}),
        sa.Column("num_resumes", sa.Integer, default=0),
        sa.Column("status", sa.String(20), default="completed"),
        sa.Column("created_at", sa.DateTime),
        sa.Column("completed_at", sa.DateTime),
    )

    op.create_table(
        "ranking_results",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("ranking_job_id", UUID(as_uuid=False),
                   sa.ForeignKey("ranking_jobs.id")),
        sa.Column("resume_id", UUID(as_uuid=False),
                   sa.ForeignKey("resumes.id")),
        sa.Column("final_score", sa.Float, nullable=False),
        sa.Column("confidence", sa.String(10)),
        sa.Column("semantic_similarity", sa.Float),
        sa.Column("skill_match", sa.Float),
        sa.Column("experience_match", sa.Float),
        sa.Column("education_match", sa.Float),
        sa.Column("project_relevance", sa.Float),
        sa.Column("matching_skills", JSONB, default=[]),
        sa.Column("missing_skills", JSONB, default=[]),
        sa.Column("extra_skills", JSONB, default=[]),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "feedback_records",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("resume_id", UUID(as_uuid=False),
                   sa.ForeignKey("resumes.id")),
        sa.Column("job_description_id", UUID(as_uuid=False),
                   sa.ForeignKey("job_descriptions.id")),
        sa.Column("strengths", JSONB, default=[]),
        sa.Column("weaknesses", JSONB, default=[]),
        sa.Column("suggestions", JSONB, default=[]),
        sa.Column("ats_score", sa.Float, default=0.0),
        sa.Column("ats_breakdown", JSONB, default={}),
        sa.Column("llm_generated", sa.Boolean, default=False),
        sa.Column("llm_feedback_text", sa.Text),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("created_at", sa.DateTime),
    )

    # Indexes for common query patterns
    op.create_index("ix_resumes_created_at", "resumes", ["created_at"])
    op.create_index("ix_jds_created_at", "job_descriptions", ["created_at"])
    op.create_index("ix_ranking_results_job", "ranking_results", ["ranking_job_id"])
    op.create_index("ix_ranking_results_resume", "ranking_results", ["resume_id"])
    op.create_index("ix_ranking_results_score", "ranking_results",
                     ["ranking_job_id", "final_score"])


def downgrade() -> None:
    op.drop_table("feedback_records")
    op.drop_table("ranking_results")
    op.drop_table("ranking_jobs")
    op.drop_table("job_descriptions")
    op.drop_table("resumes")
