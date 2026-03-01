"""Pydantic schemas for all entities."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ═══════════════════════════════════════════════════════════════
#  User
# ═══════════════════════════════════════════════════════════════


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)


class LoginOrRegister(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Personal Info
# ═══════════════════════════════════════════════════════════════


class PersonalInfoCreate(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None


class PersonalInfoOut(PersonalInfoCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Education
# ═══════════════════════════════════════════════════════════════


class EducationCreate(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade: Optional[str] = None


class EducationOut(EducationCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Skill
# ═══════════════════════════════════════════════════════════════


class SkillCreate(BaseModel):
    skill_name: str
    skill_category: Optional[str] = None


class SkillOut(SkillCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Experience
# ═══════════════════════════════════════════════════════════════


class ExperienceBulletCreate(BaseModel):
    bullet_text: str


class ExperienceBulletOut(ExperienceBulletCreate):
    id: str
    model_config = {"from_attributes": True}


class ExperienceCreate(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: list[ExperienceBulletCreate] = []


class ExperienceOut(BaseModel):
    id: str
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: list[ExperienceBulletOut] = []
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Project
# ═══════════════════════════════════════════════════════════════


class ProjectBulletCreate(BaseModel):
    bullet_text: str


class ProjectBulletOut(ProjectBulletCreate):
    id: str
    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    project_title: str
    description: Optional[str] = None
    tech_stack: Optional[str] = None
    bullets: list[ProjectBulletCreate] = []


class ProjectOut(BaseModel):
    id: str
    project_title: str
    description: Optional[str] = None
    tech_stack: Optional[str] = None
    bullets: list[ProjectBulletOut] = []
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Certification
# ═══════════════════════════════════════════════════════════════


class CertificationCreate(BaseModel):
    name: str
    issuing_organization: Optional[str] = None
    year: Optional[int] = None


class CertificationOut(CertificationCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Achievement
# ═══════════════════════════════════════════════════════════════


class AchievementCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None


class AchievementOut(AchievementCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  External Profile
# ═══════════════════════════════════════════════════════════════


class ExternalProfileCreate(BaseModel):
    platform: str
    profile_url: str


class ExternalProfileOut(ExternalProfileCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Profile (aggregate)
# ═══════════════════════════════════════════════════════════════


class ProfileCreate(BaseModel):
    """Create profile for a user (user_id set via URL)."""
    pass


class ProfileOut(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    personal_info: Optional[PersonalInfoOut] = None
    education: list[EducationOut] = []
    skills: list[SkillOut] = []
    experience: list[ExperienceOut] = []
    projects: list[ProjectOut] = []
    certifications: list[CertificationOut] = []
    achievements: list[AchievementOut] = []
    external_profiles: list[ExternalProfileOut] = []
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  JD Analysis
# ═══════════════════════════════════════════════════════════════


class JDSubmit(BaseModel):
    raw_text: str = Field(..., min_length=20)


class JDStructured(BaseModel):
    role_title: str = ""
    experience_level: str = ""
    must_have_skills: list[str] = []
    nice_to_have_skills: list[str] = []
    keywords: list[str] = []
    role_category: str = ""


class JDAnalysisOut(BaseModel):
    id: str
    structured_data: JDStructured
    created_at: datetime
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Resume Generation
# ═══════════════════════════════════════════════════════════════


class ResumeGenerateRequest(BaseModel):
    profile_id: str
    jd_text: str = Field(..., min_length=20)


class ResumeOut(BaseModel):
    id: str
    profile_id: str
    jd_id: Optional[str] = None
    job_title: str
    version: int
    file_path: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}
