"""Resume generation and management routes."""

import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ResumeGenerateRequest, ResumeOut
from app.services.orchestrator import generate_resume
from app.repositories import ResumeRepo

router = APIRouter()


@router.post("/generate", status_code=201)
def generate(payload: ResumeGenerateRequest, db: Session = Depends(get_db)):
    """Generate a role-specific resume from a job description.

    This is the main endpoint — runs the full AI pipeline:
    JD analysis → embeddings → scoring → selection → rewriting →
    ATS optimization → assembly → rendering.
    """
    result = generate_resume(db, payload.profile_id, payload.jd_text)
    return {
        "resume_id": result["resume_id"],
        "job_title": result["job_title"],
        "version": result["version"],
        "pdf_path": result["pdf_path"],
        "docx_path": result["docx_path"],
        "jd_analysis": result["jd_analysis"],
        "skill_confidence": result["skill_confidence"],
        "keyword_coverage": result["keyword_coverage"],
    }


@router.get("/", response_model=list[ResumeOut])
def list_resumes(profile_id: str, db: Session = Depends(get_db)):
    """List all resumes for a profile."""
    return ResumeRepo.list_by_profile(db, profile_id)


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    """Get resume metadata by ID."""
    return ResumeRepo.get(db, resume_id)


@router.get("/{resume_id}/download")
def download_resume(resume_id: str, format: str = "pdf", db: Session = Depends(get_db)):
    """Download a generated resume file."""
    resume = ResumeRepo.get(db, resume_id)

    if format == "docx":
        path = resume.file_path
        if path and path.endswith(".pdf"):
            path = path.replace(".pdf", ".docx")
    else:
        path = resume.file_path

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Resume file not found")

    media_type = "application/pdf" if format == "pdf" else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path,
        media_type=media_type,
        filename=os.path.basename(path),
    )
