"""Stored job descriptions: analysis, user review, and evidence coverage."""

import json

from sqlalchemy.orm import Session

from app.domain.resume_draft import JDData
from app.models.jd import JDAnalysis
from app.models.user import User
from app.repositories import JDAnalysisRepo
from app.services import evidence_service, profile_service
from app.services.auth_service import utcnow
from app.services.jd_analyzer import analyze_jd, jd_to_dict


def structured(record: JDAnalysis) -> JDData:
    return JDData(**json.loads(record.structured_data))


def analyze_and_store(db: Session, user: User, raw_text: str) -> JDAnalysis:
    result = analyze_jd(raw_text)
    return JDAnalysisRepo.create(
        db, user_id=user.id, raw_text=raw_text,
        structured_data=json.dumps(jd_to_dict(result.data)),
        analysis_mode=result.mode, warnings=json.dumps(result.warnings),
    )


def save_review(db: Session, user: User, jd_id: str, data: JDData) -> JDAnalysis:
    """Replace the analysis with the user's corrected version."""
    record = JDAnalysisRepo.get_owned(db, user.id, jd_id)
    record.structured_data = json.dumps(jd_to_dict(data))
    record.embedding = None  # the requirements changed, so any stored embedding is stale
    record.reviewed_at = utcnow()
    db.commit()
    db.refresh(record)
    return record


def coverage(db: Session, user: User, jd_id: str) -> list[evidence_service.RequirementMatch]:
    record = JDAnalysisRepo.get_owned(db, user.id, jd_id)
    return evidence_service.coverage(profile_service.get_profile(db, user), structured(record))
