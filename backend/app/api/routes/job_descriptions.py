"""
app/api/routes/job_descriptions.py
------------------------------------
Job Description management endpoints:
  POST   /jds           – Create JD from pasted text
  POST   /jds/upload    – Create JD from uploaded file
  GET    /jds            – List all JDs
  GET    /jds/{id}       – Get full JD detail
  DELETE /jds/{id}       – Delete a JD
"""

from __future__ import annotations
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.orm_models import JobDescription
from app.schemas.schemas import (
    JobDescriptionCreate, JobDescriptionOut, JobDescriptionDetailOut
)
from app.services.jd_service import process_jd
from app.services.parser_service import extract_text

logger = get_logger(__name__)
router = APIRouter(prefix="/jds", tags=["Job Descriptions"])


def _persist_jd(parsed, source: str, db: Session) -> JobDescription:
    jd_id = str(uuid.uuid4())
    orm = JobDescription(
        id=jd_id,
        title=parsed.title,
        raw_text=parsed.raw_text,
        required_skills=parsed.required_skills,
        skills_by_category=parsed.skills_by_category,
        min_experience_years=parsed.min_experience_years,
        required_education=parsed.required_education,
        required_education_rank=parsed.required_education_rank,
        source=source,
        created_at=datetime.utcnow(),
    )
    db.add(orm)
    db.commit()
    db.refresh(orm)
    logger.info(f"Created JD id={jd_id} title='{orm.title}'")
    return orm


@router.post(
    "",
    response_model=JobDescriptionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create JD from pasted text",
)
def create_jd(payload: JobDescriptionCreate, db: Session = Depends(get_db)):
    parsed = process_jd(payload.text, source=payload.source)
    if payload.title:
        parsed.title = payload.title
    orm = _persist_jd(parsed, payload.source, db)
    return JobDescriptionOut.model_validate(orm)


@router.post(
    "/upload",
    response_model=JobDescriptionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload JD file (PDF / DOCX / TXT)",
)
async def upload_jd(
    file: UploadFile = File(...),
    source: str = "custom",
    db: Session = Depends(get_db),
):
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    raw_bytes = await file.read()
    if len(raw_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large.")

    ext = (file.filename or "").lower().rsplit(".", 1)[-1]
    if ext not in settings.ALLOWED_RESUME_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported file type .{ext}")

    try:
        text = extract_text(file.filename, raw_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}")

    parsed = process_jd(text, source=source)
    orm = _persist_jd(parsed, source, db)
    return JobDescriptionOut.model_validate(orm)


@router.get("", response_model=list[JobDescriptionOut], summary="List all job descriptions")
def list_jds(db: Session = Depends(get_db)):
    jds = db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()
    return [JobDescriptionOut.model_validate(j) for j in jds]


@router.get(
    "/{jd_id}",
    response_model=JobDescriptionDetailOut,
    summary="Get full JD detail",
)
def get_jd(jd_id: str, db: Session = Depends(get_db)):
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found.")
    return JobDescriptionDetailOut.model_validate(jd)


@router.delete(
    "/{jd_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job description",
)
def delete_jd(jd_id: str, db: Session = Depends(get_db)):
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found.")
    db.delete(jd)
    db.commit()
    logger.info(f"Deleted JD {jd_id}")
