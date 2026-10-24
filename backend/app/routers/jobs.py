"""Background job status."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import JobOut
from app.services import job_service

router = APIRouter()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return job_service.get_owned(db, user, job_id)


@router.post("/{job_id}/retry", response_model=JobOut)
def retry_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return job_service.retry(db, user, job_id)
