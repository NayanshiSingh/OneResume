"""Records used to enforce per-user limits and to slow down password guessing."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UsageEvent(Base):
    """One counted action (JD analysis, resume import, draft) by a user."""

    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_user_action_time", "user_id", "action", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AuthAttempt(Base):
    """A failed sign-in or a password reset request, keyed by a hash of the email."""

    __tablename__ = "auth_attempts"
    __table_args__ = (Index("ix_auth_attempts_email_kind_time", "email_hash", "kind", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email_hash: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(20))  # login_failure | reset_request
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
