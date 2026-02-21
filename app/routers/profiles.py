"""Profile and section CRUD routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ProfileOut, EducationCreate, EducationOut,
    SkillCreate, SkillOut, ExperienceCreate, ExperienceOut,
    ProjectCreate, ProjectOut, CertificationCreate, CertificationOut,
    AchievementCreate, AchievementOut, ExternalProfileCreate, ExternalProfileOut,
    PersonalInfoCreate, PersonalInfoOut,
)
from app.repositories import (
    ProfileRepository, EducationRepo, SkillRepo, ExperienceRepo,
    ExperienceBulletRepo, ProjectRepo, ProjectBulletRepo,
    CertificationRepo, AchievementRepo, ExternalProfileRepo, PersonalInfoRepo,
)

router = APIRouter()


# ── Profile ───────────────────────────────────────────────────


@router.post("/{user_id}", response_model=ProfileOut, status_code=201)
def create_profile(user_id: str, db: Session = Depends(get_db)):
    return ProfileRepository.create(db, user_id)


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    return ProfileRepository.get(db, profile_id)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    ProfileRepository.delete(db, profile_id)


# ── Personal Info ─────────────────────────────────────────────


@router.put("/{profile_id}/personal-info", response_model=PersonalInfoOut)
def upsert_personal_info(
    profile_id: str, payload: PersonalInfoCreate, db: Session = Depends(get_db)
):
    return PersonalInfoRepo.upsert(db, profile_id, **payload.model_dump())


# ── Education ─────────────────────────────────────────────────


@router.post("/{profile_id}/education", response_model=EducationOut, status_code=201)
def add_education(profile_id: str, payload: EducationCreate, db: Session = Depends(get_db)):
    return EducationRepo.create(db, profile_id, **payload.model_dump())


@router.get("/{profile_id}/education", response_model=list[EducationOut])
def list_education(profile_id: str, db: Session = Depends(get_db)):
    return EducationRepo.list_by_parent(db, profile_id)


@router.delete("/education/{edu_id}", status_code=204)
def delete_education(edu_id: str, db: Session = Depends(get_db)):
    EducationRepo.delete(db, edu_id)


# ── Skills ────────────────────────────────────────────────────


@router.post("/{profile_id}/skills", response_model=SkillOut, status_code=201)
def add_skill(profile_id: str, payload: SkillCreate, db: Session = Depends(get_db)):
    return SkillRepo.create(db, profile_id, **payload.model_dump())


@router.get("/{profile_id}/skills", response_model=list[SkillOut])
def list_skills(profile_id: str, db: Session = Depends(get_db)):
    return SkillRepo.list_by_parent(db, profile_id)


@router.delete("/skills/{skill_id}", status_code=204)
def delete_skill(skill_id: str, db: Session = Depends(get_db)):
    SkillRepo.delete(db, skill_id)


# ── Experience ────────────────────────────────────────────────


@router.post("/{profile_id}/experience", response_model=ExperienceOut, status_code=201)
def add_experience(profile_id: str, payload: ExperienceCreate, db: Session = Depends(get_db)):
    exp = ExperienceRepo.create(
        db, profile_id,
        company=payload.company, role=payload.role,
        start_date=payload.start_date, end_date=payload.end_date,
    )
    for b in payload.bullets:
        ExperienceBulletRepo.create(db, exp.id, bullet_text=b.bullet_text)
    db.refresh(exp)
    return exp


@router.get("/{profile_id}/experience", response_model=list[ExperienceOut])
def list_experience(profile_id: str, db: Session = Depends(get_db)):
    return ExperienceRepo.list_by_parent(db, profile_id)


@router.delete("/experience/{exp_id}", status_code=204)
def delete_experience(exp_id: str, db: Session = Depends(get_db)):
    ExperienceRepo.delete(db, exp_id)


# ── Projects ──────────────────────────────────────────────────


@router.post("/{profile_id}/projects", response_model=ProjectOut, status_code=201)
def add_project(profile_id: str, payload: ProjectCreate, db: Session = Depends(get_db)):
    proj = ProjectRepo.create(
        db, profile_id,
        project_title=payload.project_title,
        description=payload.description,
        tech_stack=payload.tech_stack,
    )
    for b in payload.bullets:
        ProjectBulletRepo.create(db, proj.id, bullet_text=b.bullet_text)
    db.refresh(proj)
    return proj


@router.get("/{profile_id}/projects", response_model=list[ProjectOut])
def list_projects(profile_id: str, db: Session = Depends(get_db)):
    return ProjectRepo.list_by_parent(db, profile_id)


@router.delete("/projects/{proj_id}", status_code=204)
def delete_project(proj_id: str, db: Session = Depends(get_db)):
    ProjectRepo.delete(db, proj_id)


# ── Certifications ────────────────────────────────────────────


@router.post("/{profile_id}/certifications", response_model=CertificationOut, status_code=201)
def add_certification(profile_id: str, payload: CertificationCreate, db: Session = Depends(get_db)):
    return CertificationRepo.create(db, profile_id, **payload.model_dump())


@router.get("/{profile_id}/certifications", response_model=list[CertificationOut])
def list_certifications(profile_id: str, db: Session = Depends(get_db)):
    return CertificationRepo.list_by_parent(db, profile_id)


@router.delete("/certifications/{cert_id}", status_code=204)
def delete_certification(cert_id: str, db: Session = Depends(get_db)):
    CertificationRepo.delete(db, cert_id)


# ── Achievements ──────────────────────────────────────────────


@router.post("/{profile_id}/achievements", response_model=AchievementOut, status_code=201)
def add_achievement(profile_id: str, payload: AchievementCreate, db: Session = Depends(get_db)):
    return AchievementRepo.create(db, profile_id, **payload.model_dump())


@router.get("/{profile_id}/achievements", response_model=list[AchievementOut])
def list_achievements(profile_id: str, db: Session = Depends(get_db)):
    return AchievementRepo.list_by_parent(db, profile_id)


@router.delete("/achievements/{ach_id}", status_code=204)
def delete_achievement(ach_id: str, db: Session = Depends(get_db)):
    AchievementRepo.delete(db, ach_id)


# ── External Profiles ─────────────────────────────────────────


@router.post("/{profile_id}/external-profiles", response_model=ExternalProfileOut, status_code=201)
def add_external_profile(profile_id: str, payload: ExternalProfileCreate, db: Session = Depends(get_db)):
    return ExternalProfileRepo.create(db, profile_id, **payload.model_dump())


@router.get("/{profile_id}/external-profiles", response_model=list[ExternalProfileOut])
def list_external_profiles(profile_id: str, db: Session = Depends(get_db)):
    return ExternalProfileRepo.list_by_parent(db, profile_id)


@router.delete("/external-profiles/{ep_id}", status_code=204)
def delete_external_profile(ep_id: str, db: Session = Depends(get_db)):
    ExternalProfileRepo.delete(db, ep_id)
