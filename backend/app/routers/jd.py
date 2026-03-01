"""Job Description API routes."""

import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import JDSubmit, JDAnalysisOut, JDStructured
from app.services.jd_analyzer import analyze_jd
from app.repositories import JDAnalysisRepo

router = APIRouter()


@router.post("/analyze", response_model=JDAnalysisOut, status_code=201)
def analyze_job_description(payload: JDSubmit, db: Session = Depends(get_db)):
    """Analyze a raw job description and return structured data."""
    jd_data = analyze_jd(payload.raw_text)

    structured = {
        "role_title": jd_data.role_title,
        "experience_level": jd_data.experience_level,
        "must_have_skills": jd_data.must_have_skills,
        "nice_to_have_skills": jd_data.nice_to_have_skills,
        "keywords": jd_data.keywords,
        "role_category": jd_data.role_category,
    }

    record = JDAnalysisRepo.create(
        db, raw_text=payload.raw_text,
        structured_data=json.dumps(structured),
    )

    return JDAnalysisOut(
        id=record.id,
        structured_data=JDStructured(**structured),
        created_at=record.created_at,
    )


@router.get("/{jd_id}", response_model=JDAnalysisOut)
def get_jd_analysis(jd_id: str, db: Session = Depends(get_db)):
    """Get a stored JD analysis by ID."""
    record = JDAnalysisRepo.get(db, jd_id)
    structured = json.loads(record.structured_data)
    return JDAnalysisOut(
        id=record.id,
        structured_data=JDStructured(**structured),
        created_at=record.created_at,
    )
