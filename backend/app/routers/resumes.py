"""Resume generation and management routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Literal

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories import ArtifactRepo, ResumeRepo
from app.schemas import ResumeOut
from app.services.export_service import MEDIA_TYPES, artifact_path, delete_resume_files, download_filename

router = APIRouter()


def resume_out(resume) -> ResumeOut:
    return ResumeOut(
        id=resume.id, jd_id=resume.jd_id, draft_id=resume.draft_id, job_title=resume.job_title,
        version=resume.version, created_at=resume.created_at,
        formats=sorted(a.format for a in resume.artifacts),
    )


@router.get("", response_model=list[ResumeOut])
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List the signed-in user's resumes, newest first."""
    return [resume_out(r) for r in ResumeRepo.list_owned(db, user.id)]


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return resume_out(ResumeRepo.get_owned(db, user.id, resume_id))


@router.get("/{resume_id}/download")
def download_resume(
    resume_id: str, format: Literal["pdf", "docx"] = "pdf",
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Download a generated resume file in the requested format."""
    resume = ResumeRepo.get_owned(db, user.id, resume_id)
    artifact = ArtifactRepo.get_for_resume(db, resume, format)
    return FileResponse(
        artifact_path(artifact),
        media_type=MEDIA_TYPES[format],
        filename=download_filename(resume, format),
    )


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = ResumeRepo.get_owned(db, user.id, resume_id)
    delete_resume_files(user.id, resume.id)
    db.delete(resume)
    db.commit()
