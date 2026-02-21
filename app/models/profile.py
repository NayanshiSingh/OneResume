"""Profile and all profile-section models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


# ── Profile ───────────────────────────────────────────────────


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    user = relationship("User", back_populates="profiles")
    education = relationship("Education", back_populates="profile", cascade="all, delete-orphan")
    skills = relationship("Skill", back_populates="profile", cascade="all, delete-orphan")
    experience = relationship("Experience", back_populates="profile", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="profile", cascade="all, delete-orphan")
    certifications = relationship("Certification", back_populates="profile", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="profile", cascade="all, delete-orphan")
    external_profiles = relationship("ExternalProfile", back_populates="profile", cascade="all, delete-orphan")
    personal_info = relationship("PersonalInfo", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="profile", cascade="all, delete-orphan")


# ── Education ─────────────────────────────────────────────────


class Education(Base):
    __tablename__ = "education"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    institution: Mapped[str] = mapped_column(String(255))
    degree: Mapped[str] = mapped_column(String(255))
    field_of_study: Mapped[str] = mapped_column(String(255), nullable=True)
    start_year: Mapped[int] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int] = mapped_column(Integer, nullable=True)
    grade: Mapped[str] = mapped_column(String(50), nullable=True)

    profile = relationship("Profile", back_populates="education")


# ── Skills ────────────────────────────────────────────────────


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    skill_name: Mapped[str] = mapped_column(String(100))
    skill_category: Mapped[str] = mapped_column(String(100), nullable=True)

    profile = relationship("Profile", back_populates="skills")


# ── Experience ────────────────────────────────────────────────


class Experience(Base):
    __tablename__ = "experience"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    company: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[str] = mapped_column(String(20), nullable=True)  # YYYY-MM
    end_date: Mapped[str] = mapped_column(String(20), nullable=True)  # YYYY-MM or "Present"
    experience_embedding: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array

    profile = relationship("Profile", back_populates="experience")
    bullets = relationship("ExperienceBullet", back_populates="experience", cascade="all, delete-orphan")


class ExperienceBullet(Base):
    __tablename__ = "experience_bullets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experience_id: Mapped[str] = mapped_column(ForeignKey("experience.id", ondelete="CASCADE"))
    bullet_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of floats

    experience = relationship("Experience", back_populates="bullets")


# ── Projects ──────────────────────────────────────────────────


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    project_title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[str] = mapped_column(Text, nullable=True)  # comma-separated

    profile = relationship("Profile", back_populates="projects")
    bullets = relationship("ProjectBullet", back_populates="project", cascade="all, delete-orphan")


class ProjectBullet(Base):
    __tablename__ = "project_bullets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    bullet_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of floats

    project = relationship("Project", back_populates="bullets")


# ── Certifications ────────────────────────────────────────────


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    issuing_organization: Mapped[str] = mapped_column(String(255), nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=True)

    profile = relationship("Profile", back_populates="certifications")


# ── Achievements ──────────────────────────────────────────────


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)

    profile = relationship("Profile", back_populates="achievements")


# ── External Profiles ─────────────────────────────────────────


class ExternalProfile(Base):
    __tablename__ = "external_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String(100))
    profile_url: Mapped[str] = mapped_column(String(500))

    profile = relationship("Profile", back_populates="external_profiles")


# ── Personal Info ─────────────────────────────────────────────


class PersonalInfo(Base):
    __tablename__ = "personal_info"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), unique=True
    )
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(30), nullable=True)

    profile = relationship("Profile", back_populates="personal_info")
