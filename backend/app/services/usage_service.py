"""Per-user limits on AI-heavy actions, and throttling of password guessing.

Limits use a rolling window: each counted action expires 24 hours after it
happened. Failed sign-ins are counted per email (hashed), whether or not the
account exists, so the limit reveals nothing about which emails are registered.
"""

import hashlib
import math
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.errors import RateLimitedError
from app.models.usage import AuthAttempt, UsageEvent
from app.models.user import User
from app.clock import utcnow

WINDOW = timedelta(hours=24)
JD_ANALYSIS, RESUME_IMPORT, DRAFT = "jd_analysis", "resume_import", "draft"
LOGIN_FAILURE, RESET_REQUEST = "login_failure", "reset_request"

_LIMITS = {
    JD_ANALYSIS: ("DAILY_JD_ANALYSES", "job description analyses"),
    RESUME_IMPORT: ("DAILY_RESUME_IMPORTS", "resume imports"),
    DRAFT: ("DAILY_DRAFTS", "drafts"),
}


def _wait_text(seconds: int) -> str:
    if seconds >= 3600:
        return f"about {math.ceil(seconds / 3600)} hour(s)"
    return f"about {max(1, math.ceil(seconds / 60))} minute(s)"


def consume(db: Session, user: User, action: str) -> None:
    """Count one use of `action`, or raise RateLimitedError if today's limit is reached."""
    setting, label = _LIMITS[action]
    limit = getattr(settings, setting)
    recent = (
        db.query(UsageEvent)
        .filter(UsageEvent.user_id == user.id, UsageEvent.action == action, UsageEvent.created_at >= utcnow() - WINDOW)
        .order_by(UsageEvent.created_at)
    )
    if recent.count() >= limit:
        retry = int((recent.first().created_at + WINDOW - utcnow()).total_seconds()) + 1
        raise RateLimitedError(f"You have reached today's limit of {limit} {label}. Try again in {_wait_text(retry)}.", retry)
    db.add(UsageEvent(user_id=user.id, action=action))
    db.commit()


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def _recent_attempts(db: Session, email: str, kind: str, window: timedelta):
    return (
        db.query(AuthAttempt)
        .filter(AuthAttempt.email_hash == _email_hash(email), AuthAttempt.kind == kind,
                AuthAttempt.created_at >= utcnow() - window)
        .order_by(AuthAttempt.created_at)
    )


def check_login_allowed(db: Session, email: str) -> None:
    window = timedelta(minutes=settings.LOGIN_FAILURE_WINDOW_MINUTES)
    failures = _recent_attempts(db, email, LOGIN_FAILURE, window)
    if failures.count() >= settings.LOGIN_FAILURE_LIMIT:
        retry = int((failures.first().created_at + window - utcnow()).total_seconds()) + 1
        raise RateLimitedError(f"Too many failed sign-in attempts. Try again in {_wait_text(retry)}.", retry)


def record_login_failure(db: Session, email: str) -> None:
    db.add(AuthAttempt(email_hash=_email_hash(email), kind=LOGIN_FAILURE))
    db.commit()


def clear_login_failures(db: Session, email: str) -> None:
    db.query(AuthAttempt).filter(AuthAttempt.email_hash == _email_hash(email), AuthAttempt.kind == LOGIN_FAILURE).delete()
    db.commit()


def allow_reset_email(db: Session, email: str) -> bool:
    """Record a reset request; False once this email has had too many in the last hour."""
    if _recent_attempts(db, email, RESET_REQUEST, timedelta(hours=1)).count() >= settings.RESET_REQUESTS_PER_HOUR:
        return False
    db.add(AuthAttempt(email_hash=_email_hash(email), kind=RESET_REQUEST))
    db.commit()
    return True
