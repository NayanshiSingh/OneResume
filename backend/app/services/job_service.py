"""Background jobs stored in the database and run by app.worker.

A job moves queued → running → succeeded | failed. Submitting again with
the same idempotency key returns the existing job instead of doing the work
twice. Jobs left running by a crashed worker are picked up again after
STALE_AFTER.
"""

import json
import logging
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import InvalidRequestError, NotFoundError
from app.models.draft import GenerationJob
from app.models.user import User
from app.services.auth_service import utcnow

logger = logging.getLogger(__name__)

QUEUED, RUNNING, SUCCEEDED, FAILED = "queued", "running", "succeeded", "failed"
STALE_AFTER = timedelta(minutes=10)
FAILURE_MESSAGE = "Something went wrong while building this. Try again."

# kind → handler(db, job) returning the ID of what it created
HANDLERS: dict[str, Callable[[Session, GenerationJob], str]] = {}


def register(kind: str):
    def decorator(handler: Callable[[Session, GenerationJob], str]):
        HANDLERS[kind] = handler
        return handler
    return decorator


def enqueue(db: Session, user: User, kind: str, payload: dict, idempotency_key: str) -> GenerationJob:
    existing = db.query(GenerationJob).filter_by(user_id=user.id, idempotency_key=idempotency_key).first()
    if existing:
        return existing
    job = GenerationJob(user_id=user.id, kind=kind, payload=json.dumps(payload), idempotency_key=idempotency_key)
    db.add(job)
    try:
        db.commit()
    except IntegrityError:  # a concurrent request with the same key won
        db.rollback()
        return db.query(GenerationJob).filter_by(user_id=user.id, idempotency_key=idempotency_key).one()
    db.refresh(job)
    return job


def get_owned(db: Session, user: User, job_id: str) -> GenerationJob:
    job = db.query(GenerationJob).filter_by(id=job_id, user_id=user.id).first()
    if not job:
        raise NotFoundError("Job not found")
    return job


def retry(db: Session, user: User, job_id: str) -> GenerationJob:
    job = get_owned(db, user, job_id)
    if job.status != FAILED:
        raise InvalidRequestError("Only failed jobs can be retried")
    job.status, job.error, job.finished_at = QUEUED, None, None
    db.commit()
    return job


def claim_next(db: Session) -> GenerationJob | None:
    query = (
        db.query(GenerationJob)
        .filter(or_(
            GenerationJob.status == QUEUED,
            and_(GenerationJob.status == RUNNING, GenerationJob.started_at < utcnow() - STALE_AFTER),
        ))
        .order_by(GenerationJob.created_at)
    )
    if db.bind.dialect.name == "postgresql":
        # Several workers can poll safely: each skips rows another worker has locked.
        query = query.with_for_update(skip_locked=True)
    job = query.first()
    if not job:
        db.rollback()
        return None
    job.status, job.started_at, job.attempts = RUNNING, utcnow(), job.attempts + 1
    db.commit()
    return job


def run(db: Session, job: GenerationJob) -> None:
    job_id = job.id
    try:
        result_id = HANDLERS[job.kind](db, job)
    except Exception:
        logger.exception("Job %s (%s) failed", job_id, job.kind)
        db.rollback()
        job = db.get(GenerationJob, job_id)
        job.status, job.error, job.finished_at = FAILED, FAILURE_MESSAGE, utcnow()
        db.commit()
        return
    job.status, job.result_id, job.finished_at = SUCCEEDED, result_id, utcnow()
    db.commit()


def process_next(db: Session) -> bool:
    """Run one waiting job. Returns False when there was nothing to do."""
    job = claim_next(db)
    if job is None:
        return False
    run(db, job)
    return True
