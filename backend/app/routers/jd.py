"""Job Description API routes."""

import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.domain.resume_draft import JDData
from app.models.user import User
from app.repositories import JDAnalysisRepo
from app.schemas import CoverageItem, JDAnalysisOut, JDStructured, JDSubmit
from app.services import jd_service

router = APIRouter()


def _to_out(record) -> JDAnalysisOut:
    return JDAnalysisOut(
        id=record.id,
        structured_data=JDStructured(**json.loads(record.structured_data)),
        analysis_mode=record.analysis_mode,
        warnings=json.loads(record.warnings),
        reviewed=record.reviewed_at is not None,
        created_at=record.created_at,
    )


@router.post("/analyze", response_model=JDAnalysisOut, status_code=201)
def analyze_job_description(
    payload: JDSubmit, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Analyze a raw job description and return structured data for review."""
    return _to_out(jd_service.analyze_and_store(db, user, payload.raw_text))


@router.get("", response_model=list[JDAnalysisOut])
def list_jd_analyses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_to_out(r) for r in JDAnalysisRepo.list_owned(db, user.id)]


@router.get("/{jd_id}", response_model=JDAnalysisOut)
def get_jd_analysis(jd_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a stored JD analysis by ID."""
    return _to_out(JDAnalysisRepo.get_owned(db, user.id, jd_id))


@router.put("/{jd_id}", response_model=JDAnalysisOut)
def save_reviewed_analysis(
    jd_id: str, payload: JDStructured, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Save the user's corrected requirements; drafts use this reviewed version."""
    return _to_out(jd_service.save_review(db, user, jd_id, JDData(**payload.model_dump())))


@router.get("/{jd_id}/coverage", response_model=list[CoverageItem])
def get_coverage(jd_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Which requirements the profile supports, needs to confirm, or lacks."""
    return [m.to_dict() for m in jd_service.coverage(db, user, jd_id)]
