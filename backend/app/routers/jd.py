"""Job Description API routes."""

import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import JDSubmit, JDAnalysisOut, JDStructured
from app.services.jd_analyzer import analyze_jd, jd_to_dict
from app.repositories import JDAnalysisRepo

router = APIRouter()


def _to_out(record) -> JDAnalysisOut:
    return JDAnalysisOut(
        id=record.id,
        structured_data=JDStructured(**json.loads(record.structured_data)),
        created_at=record.created_at,
    )


@router.post("/analyze", response_model=JDAnalysisOut, status_code=201)
def analyze_job_description(
    payload: JDSubmit, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Analyze a raw job description and return structured data."""
    jd_data = analyze_jd(payload.raw_text)
    record = JDAnalysisRepo.create(
        db, user_id=user.id, raw_text=payload.raw_text,
        structured_data=json.dumps(jd_to_dict(jd_data)),
    )
    return _to_out(record)


@router.get("", response_model=list[JDAnalysisOut])
def list_jd_analyses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_to_out(r) for r in JDAnalysisRepo.list_owned(db, user.id)]


@router.get("/{jd_id}", response_model=JDAnalysisOut)
def get_jd_analysis(jd_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a stored JD analysis by ID."""
    return _to_out(JDAnalysisRepo.get_owned(db, user.id, jd_id))
