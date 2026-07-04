"""
app/api/routes/resumes.py
---------------------------
Resume management endpoints:
  POST   /resumes/upload   – Upload one or more resume files
  GET    /resumes           – List all stored resumes
  GET    /resumes/{id}      – Get full resume detail
  DELETE /resumes/{id}      – Remove a resume
"""

from __future__ import annotations
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.orm_models import Resume
from app.schemas.schemas import ResumeOut, ResumeDetailOut
from app.services.parser_service import parse_resume
from app.services.skill_service import extract_skills
from app.services.embedding_service import EmbeddingService
from app.services.search_service import (
    upsert_resume_embedding,
    delete_resume_embedding,
)
from app.services.cache_service import invalidate_ranking

logger = get_logger(__name__)
router = APIRouter(prefix="/resumes", tags=["Resumes"])





@router.post(
    "/upload",
    response_model=list[ResumeOut],
    status_code=status.HTTP_201_CREATED,
    summary="Upload one or more resume files (PDF / DOCX / TXT)",
)
async def upload_resumes(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    created: list[ResumeOut] = []

    for upload in files:
        ext = (upload.filename or "").lower().rsplit(".", 1)[-1]
        if ext not in settings.ALLOWED_RESUME_EXTENSIONS:
            raise HTTPException(
                status_code=422,
                detail=f"File '{upload.filename}' has unsupported extension .{ext}.",
            )

        raw_bytes = await upload.read()
        if len(raw_bytes) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File '{upload.filename}' exceeds {settings.MAX_UPLOAD_MB} MB limit.",
            )

        try:
            parsed = parse_resume(upload.filename, raw_bytes)
        except Exception as exc:
            logger.error(f"Failed to parse {upload.filename}: {exc}")
            raise HTTPException(status_code=422, detail=f"Could not parse '{upload.filename}': {exc}")

        skill_data = extract_skills(parsed.raw_text)
        resume_id  = str(uuid.uuid4())

        # Embed and index in Chroma
        embedding = EmbeddingService.encode_single(parsed.raw_text).tolist()
        upsert_resume_embedding(
            doc_id=resume_id,
            text=parsed.raw_text,
            embedding=embedding,
            metadata={"resume_db_id": resume_id, "filename": parsed.filename},
        )

        # Persist to Postgres
        orm = Resume(
            id=resume_id,
            filename=parsed.filename,
            name=parsed.name,
            email=parsed.email,
            phone=parsed.phone,
            linkedin=parsed.linkedin,
            github=parsed.github,
            raw_text=parsed.raw_text,
            sections=parsed.sections,
            skills=skill_data["all_skills"],
            skills_by_category=skill_data["by_category"],
            years_experience=parsed.years_experience,
            education_level=parsed.education_level,
            education_rank=parsed.education_rank,
            vector_id=resume_id,
            created_at=datetime.utcnow(),
        )
        db.add(orm)
        db.commit()
        db.refresh(orm)

        created.append(ResumeOut.model_validate(orm))
        logger.info(f"Uploaded resume: {upload.filename} → id={resume_id}")

    # Rebuild BM25 with updated corpus
    created.append(ResumeOut.model_validate(orm))
    logger.info(f"Uploaded resume: {upload.filename} → id={resume_id}")

    return created


@router.get("", response_model=list[ResumeOut], summary="List all resumes")
def list_resumes(db: Session = Depends(get_db)):
    resumes = db.query(Resume).order_by(Resume.created_at.desc()).all()
    return [ResumeOut.model_validate(r) for r in resumes]


@router.get(
    "/{resume_id}",
    response_model=ResumeDetailOut,
    summary="Get full resume details",
)
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return ResumeDetailOut.model_validate(resume)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resume",
)
def delete_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    delete_resume_embedding(resume_id)
    db.delete(resume)
    db.commit()

    logger.info(f"Deleted resume {resume_id}. Cache will expire at TTL.")
  # Generate embedding and store in LanceDB
    logger.info(f"Deleted resume {resume_id}. Cache will expire at TTL.")
