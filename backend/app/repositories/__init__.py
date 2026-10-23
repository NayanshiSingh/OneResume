"""Data access for job descriptions and resumes, always scoped to an owner."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models.jd import JDAnalysis
from app.models.profile import Profile
from app.models.resume import ExportArtifact, Resume, ResumeSection


# ═══════════════════════════════════════════════════════════════
#  JD Analysis Repository
# ═══════════════════════════════════════════════════════════════


class JDAnalysisRepo:
    @staticmethod
    def create(db: Session, user_id: str, raw_text: str, structured_data: str,
               analysis_mode: str, warnings: str) -> JDAnalysis:
        jd = JDAnalysis(user_id=user_id, raw_text=raw_text, structured_data=structured_data,
                        analysis_mode=analysis_mode, warnings=warnings)
        db.add(jd)
        db.commit()
        db.refresh(jd)
        return jd

    @staticmethod
    def get_owned(db: Session, user_id: str, jd_id: str) -> JDAnalysis:
        jd = db.query(JDAnalysis).filter(JDAnalysis.id == jd_id, JDAnalysis.user_id == user_id).first()
        if not jd:
            raise NotFoundError("Job description not found")
        return jd

    @staticmethod
    def list_owned(db: Session, user_id: str) -> list[JDAnalysis]:
        return (
            db.query(JDAnalysis).filter(JDAnalysis.user_id == user_id)
            .order_by(JDAnalysis.created_at.desc()).all()
        )


# ═══════════════════════════════════════════════════════════════
#  Resume Repository
# ═══════════════════════════════════════════════════════════════


class ResumeRepo:
    @staticmethod
    def create(db: Session, profile_id: str, jd_id: str | None, job_title: str, version: int,
               draft_id: str, draft_revision: int) -> Resume:
        resume = Resume(profile_id=profile_id, jd_id=jd_id, job_title=job_title, version=version,
                        draft_id=draft_id, draft_revision=draft_revision)
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume

    @staticmethod
    def _owned_query(db: Session, user_id: str):
        return db.query(Resume).join(Profile, Resume.profile_id == Profile.id).filter(Profile.user_id == user_id)

    @staticmethod
    def get_owned(db: Session, user_id: str, resume_id: str) -> Resume:
        resume = ResumeRepo._owned_query(db, user_id).filter(Resume.id == resume_id).first()
        if not resume:
            raise NotFoundError("Resume not found")
        return resume

    @staticmethod
    def list_owned(db: Session, user_id: str) -> list[Resume]:
        return ResumeRepo._owned_query(db, user_id).order_by(Resume.created_at.desc()).all()

    @staticmethod
    def get_next_version(db: Session, profile_id: str, job_title: str) -> int:
        latest = db.query(func.max(Resume.version)).filter(
            Resume.profile_id == profile_id,
            Resume.job_title == job_title,
        ).scalar()
        return (latest or 0) + 1

    @staticmethod
    def add_section(db: Session, resume_id: str, section_type: str,
                    content: str, confidence_flags: str = None) -> ResumeSection:
        section = ResumeSection(
            resume_id=resume_id, section_type=section_type,
            content=content, confidence_flags=confidence_flags,
        )
        db.add(section)
        db.commit()
        db.refresh(section)
        return section


class ArtifactRepo:
    @staticmethod
    def create(db: Session, resume_id: str, format: str, storage_key: str,
               checksum: str, size_bytes: int) -> ExportArtifact:
        artifact = ExportArtifact(
            resume_id=resume_id, format=format, storage_key=storage_key,
            checksum=checksum, size_bytes=size_bytes,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        return artifact

    @staticmethod
    def get_for_resume(db: Session, resume: Resume, format: str) -> ExportArtifact:
        artifact = next((a for a in resume.artifacts if a.format == format), None)
        if not artifact:
            raise NotFoundError(f"No {format.upper()} file for this resume")
        return artifact
