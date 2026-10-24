"""Draft routes: request, review, edit, approve, and export."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.routers.resumes import resume_out
from app.schemas import ApproveRequest, DraftEditRequest, DraftOut, DraftRequest, DraftSummary, JobOut, ResumeOut
from app.services import draft_service

router = APIRouter()


@router.post("", response_model=JobOut, status_code=202)
def request_draft(payload: DraftRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Queue a draft for a job description. Poll /api/jobs/{id} until it finishes."""
    return draft_service.request_draft(db, user, payload.jd_id, payload.page_target, payload.idempotency_key)


@router.get("", response_model=list[DraftSummary])
def list_drafts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return draft_service.list_owned(db, user)


@router.get("/{draft_id}", response_model=DraftOut)
def get_draft(draft_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return draft_service.view(draft_service.get_owned(db, user, draft_id))


@router.patch("/{draft_id}", response_model=DraftOut)
def edit_draft(draft_id: str, payload: DraftEditRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Apply edits to the given revision. Any edit creates a new revision and clears approval."""
    return draft_service.view(draft_service.edit(db, user, draft_id, payload.revision, payload.ops))


@router.post("/{draft_id}/approve", response_model=DraftOut)
def approve_draft(draft_id: str, payload: ApproveRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return draft_service.view(draft_service.approve(db, user, draft_id, payload.revision))


@router.post("/{draft_id}/export", response_model=ResumeOut, status_code=201)
def export_draft(draft_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Render the approved revision to PDF and DOCX."""
    return resume_out(draft_service.export(db, user, draft_id))


@router.delete("/{draft_id}", status_code=204)
def delete_draft(draft_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    draft_service.delete(db, user, draft_id)
