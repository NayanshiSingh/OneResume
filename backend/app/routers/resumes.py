"""Exported resumes: list, download, compare, restore, mark as sent, delete."""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Literal

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories import ArtifactRepo, ResumeRepo
from app.schemas import DraftOut, ResumeOut, ResumeUpdate, VersionComparison
from app.services import draft_service, version_service
from app.services.export_service import MEDIA_TYPES, artifact_path, delete_resume_files, download_filename

router = APIRouter()


def resume_out(resume) -> ResumeOut:
    return ResumeOut(
        id=resume.id, jd_id=resume.jd_id, draft_id=resume.draft_id, job_title=resume.job_title,
        version=resume.version, created_at=resume.created_at, sent_at=resume.sent_at,
        formats=sorted(a.format for a in resume.artifacts),
        pdf_pages=next((a.page_count for a in resume.artifacts if a.format == "pdf"), None),
        warnings=json.loads(resume.warnings or "[]"), can_restore=resume.content_snapshot is not None,
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


@router.patch("/{resume_id}", response_model=ResumeOut)
def update_resume(resume_id: str, payload: ResumeUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Record when this version was sent (or clear it with null)."""
    return resume_out(version_service.set_sent(db, ResumeRepo.get_owned(db, user.id, resume_id), payload.sent_at))


@router.get("/{resume_id}/compare/{other_id}", response_model=VersionComparison)
def compare_versions(resume_id: str, other_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Changes from this version to another one."""
    return version_service.compare(ResumeRepo.get_owned(db, user.id, resume_id), ResumeRepo.get_owned(db, user.id, other_id))


@router.post("/{resume_id}/restore", response_model=DraftOut, status_code=201)
def restore_version(resume_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start a new draft from exactly what this version contained."""
    return draft_service.view(version_service.restore(db, user, ResumeRepo.get_owned(db, user.id, resume_id)))


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = ResumeRepo.get_owned(db, user.id, resume_id)
    delete_resume_files(user.id, resume.id)
    db.delete(resume)
    db.commit()
