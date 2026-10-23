"""Resume, resume-section, and export artifact models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = (UniqueConstraint("profile_id", "job_title", "version"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    jd_id: Mapped[str] = mapped_column(ForeignKey("jd_analysis.id", ondelete="SET NULL"), nullable=True)
    job_title: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    profile = relationship("Profile", back_populates="resumes")
    sections = relationship("ResumeSection", back_populates="resume", cascade="all, delete-orphan")
    artifacts = relationship("ExportArtifact", back_populates="resume", cascade="all, delete-orphan")


class ResumeSection(Base):
    __tablename__ = "resume_sections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    resume_id: Mapped[str] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    section_type: Mapped[str] = mapped_column(String(50))  # education, experience, etc.
    content: Mapped[str] = mapped_column(Text)  # JSON
    confidence_flags: Mapped[str] = mapped_column(Text, nullable=True)  # JSON

    resume = relationship("Resume", back_populates="sections")


class ExportArtifact(Base):
    """A generated file for one resume in one format, held in private storage."""

    __tablename__ = "export_artifacts"
    __table_args__ = (UniqueConstraint("resume_id", "format"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    resume_id: Mapped[str] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    format: Mapped[str] = mapped_column(String(10))  # pdf | docx
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    checksum: Mapped[str] = mapped_column(String(64))  # sha256 hex
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    resume = relationship("Resume", back_populates="artifacts")
