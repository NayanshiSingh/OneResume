"""Background jobs and reviewable resume drafts."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _uuid():
    return str(uuid.uuid4())


class GenerationJob(Base):
    """Work done outside the request, such as building a draft. Polled by the frontend."""

    __tablename__ = "generation_jobs"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued | running | succeeded | failed
    payload: Mapped[str] = mapped_column(Text)  # JSON
    idempotency_key: Mapped[str] = mapped_column(String(100))
    result_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Draft(Base):
    """A proposed resume for one job description, edited and approved before export.

    Approval belongs to one revision; any edit creates a new revision and
    clears the approval.
    """

    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    jd_id: Mapped[str | None] = mapped_column(ForeignKey("jd_analysis.id", ondelete="SET NULL"), nullable=True)
    job_title: Mapped[str] = mapped_column(String(255))
    page_target: Mapped[int] = mapped_column(Integer, default=1)
    matching_mode: Mapped[str] = mapped_column(String(10))  # ai | basic
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | approved
    revision: Mapped[int] = mapped_column(Integer, default=1)
    approved_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text)  # JSON: sections with included/pinned/edited flags
    coverage: Mapped[str] = mapped_column(Text)  # JSON: requirement evidence at creation time
    warnings: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of strings
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    resumes = relationship("Resume", back_populates="draft")
