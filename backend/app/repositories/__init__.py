"""CRUD repositories for all entities."""

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.profile import (
    Profile, Education, Skill, Experience, ExperienceBullet,
    Project, ProjectBullet, Certification, Achievement,
    ExternalProfile, PersonalInfo,
)
from app.models.jd import JDAnalysis
from app.models.resume import Resume, ResumeSection


# ═══════════════════════════════════════════════════════════════
#  Generic helpers
# ═══════════════════════════════════════════════════════════════


def _get_or_404(db: Session, model, id: str):
    obj = db.query(model).filter(model.id == id).first()
    if not obj:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


# ═══════════════════════════════════════════════════════════════
#  User Repository
# ═══════════════════════════════════════════════════════════════


class UserRepository:
    @staticmethod
    def create(db: Session, username: str, email: str, password_hash: str) -> User:
        user = User(username=username, email=email, password_hash=password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get(db: Session, user_id: str) -> User:
        return _get_or_404(db, User, user_id)

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def list_all(db: Session) -> list[User]:
        return db.query(User).all()

    @staticmethod
    def delete(db: Session, user_id: str):
        user = _get_or_404(db, User, user_id)
        db.delete(user)
        db.commit()


# ═══════════════════════════════════════════════════════════════
#  Profile Repository
# ═══════════════════════════════════════════════════════════════


class ProfileRepository:
    @staticmethod
    def create(db: Session, user_id: str) -> Profile:
        _get_or_404(db, User, user_id)  # ensure user exists
        profile = Profile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get(db: Session, profile_id: str) -> Profile:
        return _get_or_404(db, Profile, profile_id)

    @staticmethod
    def get_by_user(db: Session, user_id: str) -> list[Profile]:
        return db.query(Profile).filter(Profile.user_id == user_id).all()

    @staticmethod
    def delete(db: Session, profile_id: str):
        profile = _get_or_404(db, Profile, profile_id)
        db.delete(profile)
        db.commit()


# ═══════════════════════════════════════════════════════════════
#  Section Repositories (generic factory)
# ═══════════════════════════════════════════════════════════════


def _make_section_repo(ModelClass, parent_fk_name="profile_id"):
    """Creates a standard CRUD repository class for a profile section."""

    class Repo:
        @staticmethod
        def create(db: Session, parent_id: str, **kwargs):
            kwargs[parent_fk_name] = parent_id
            obj = ModelClass(**kwargs)
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return obj

        @staticmethod
        def get(db: Session, id: str):
            return _get_or_404(db, ModelClass, id)

        @staticmethod
        def list_by_parent(db: Session, parent_id: str):
            return db.query(ModelClass).filter(
                getattr(ModelClass, parent_fk_name) == parent_id
            ).all()

        @staticmethod
        def update(db: Session, id: str, **kwargs):
            obj = _get_or_404(db, ModelClass, id)
            for k, v in kwargs.items():
                if v is not None:
                    setattr(obj, k, v)
            db.commit()
            db.refresh(obj)
            return obj

        @staticmethod
        def delete(db: Session, id: str):
            obj = _get_or_404(db, ModelClass, id)
            db.delete(obj)
            db.commit()

    Repo.__name__ = f"{ModelClass.__name__}Repository"
    return Repo


EducationRepo = _make_section_repo(Education)
SkillRepo = _make_section_repo(Skill)
ExperienceRepo = _make_section_repo(Experience)
ExperienceBulletRepo = _make_section_repo(ExperienceBullet, "experience_id")
ProjectRepo = _make_section_repo(Project)
ProjectBulletRepo = _make_section_repo(ProjectBullet, "project_id")
CertificationRepo = _make_section_repo(Certification)
AchievementRepo = _make_section_repo(Achievement)
ExternalProfileRepo = _make_section_repo(ExternalProfile)


class PersonalInfoRepo:
    @staticmethod
    def upsert(db: Session, profile_id: str, **kwargs) -> PersonalInfo:
        existing = db.query(PersonalInfo).filter(
            PersonalInfo.profile_id == profile_id
        ).first()
        if existing:
            for k, v in kwargs.items():
                if v is not None:
                    setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing
        obj = PersonalInfo(profile_id=profile_id, **kwargs)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def get_by_profile(db: Session, profile_id: str):
        return db.query(PersonalInfo).filter(
            PersonalInfo.profile_id == profile_id
        ).first()


# ═══════════════════════════════════════════════════════════════
#  JD Analysis Repository
# ═══════════════════════════════════════════════════════════════


class JDAnalysisRepo:
    @staticmethod
    def create(db: Session, raw_text: str, structured_data: str, embedding: str = None) -> JDAnalysis:
        jd = JDAnalysis(raw_text=raw_text, structured_data=structured_data, embedding=embedding)
        db.add(jd)
        db.commit()
        db.refresh(jd)
        return jd

    @staticmethod
    def get(db: Session, jd_id: str) -> JDAnalysis:
        return _get_or_404(db, JDAnalysis, jd_id)

    @staticmethod
    def list_all(db: Session) -> list[JDAnalysis]:
        return db.query(JDAnalysis).all()


# ═══════════════════════════════════════════════════════════════
#  Resume Repository
# ═══════════════════════════════════════════════════════════════


class ResumeRepo:
    @staticmethod
    def create(db: Session, profile_id: str, jd_id: str, job_title: str,
               version: int = 1, file_path: str = None) -> Resume:
        resume = Resume(
            profile_id=profile_id, jd_id=jd_id,
            job_title=job_title, version=version, file_path=file_path,
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume

    @staticmethod
    def get(db: Session, resume_id: str) -> Resume:
        return _get_or_404(db, Resume, resume_id)

    @staticmethod
    def list_by_profile(db: Session, profile_id: str) -> list[Resume]:
        return db.query(Resume).filter(Resume.profile_id == profile_id).all()

    @staticmethod
    def get_next_version(db: Session, profile_id: str, job_title: str) -> int:
        existing = db.query(Resume).filter(
            Resume.profile_id == profile_id,
            Resume.job_title == job_title,
        ).count()
        return existing + 1

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
