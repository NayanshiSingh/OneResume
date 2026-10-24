"""Pydantic schemas for all entities."""

from datetime import datetime
from typing import ClassVar, Optional
from pydantic import BaseModel, EmailStr, Field, model_validator


class PatchModel(BaseModel):
    """Partial update: only fields sent are applied; required fields cannot be cleared."""

    required_fields: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _reject_clearing_required(self):
        for name in self.required_fields:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be empty")
        return self

    def changes(self) -> dict:
        return self.model_dump(exclude_unset=True)


# ═══════════════════════════════════════════════════════════════
#  Accounts
# ═══════════════════════════════════════════════════════════════


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    email: str
    created_at: datetime
    model_config = {"from_attributes": True}


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=10, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=128)


class ReorderRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1)


# ═══════════════════════════════════════════════════════════════
#  Personal Info
# ═══════════════════════════════════════════════════════════════


class PersonalInfoCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=30)


class PersonalInfoOut(PersonalInfoCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Education
# ═══════════════════════════════════════════════════════════════


class EducationCreate(BaseModel):
    institution: str = Field(..., min_length=1, max_length=255)
    degree: str = Field(..., min_length=1, max_length=255)
    field_of_study: Optional[str] = Field(None, max_length=255)
    start_year: Optional[int] = Field(None, ge=1950, le=2100)
    end_year: Optional[int] = Field(None, ge=1950, le=2100)
    end_month: Optional[int] = Field(None, ge=1, le=12)
    grade: Optional[str] = Field(None, max_length=50)


class EducationUpdate(PatchModel):
    required_fields = ("institution", "degree")
    institution: Optional[str] = Field(None, min_length=1, max_length=255)
    degree: Optional[str] = Field(None, min_length=1, max_length=255)
    field_of_study: Optional[str] = Field(None, max_length=255)
    start_year: Optional[int] = Field(None, ge=1950, le=2100)
    end_year: Optional[int] = Field(None, ge=1950, le=2100)
    end_month: Optional[int] = Field(None, ge=1, le=12)
    grade: Optional[str] = Field(None, max_length=50)


class EducationOut(EducationCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Skill
# ═══════════════════════════════════════════════════════════════


class SkillCreate(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=100)
    skill_category: Optional[str] = Field(None, max_length=100)


class SkillUpdate(PatchModel):
    required_fields = ("skill_name",)
    skill_name: Optional[str] = Field(None, min_length=1, max_length=100)
    skill_category: Optional[str] = Field(None, max_length=100)


class SkillOut(SkillCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Bullets (shared by experience and projects)
# ═══════════════════════════════════════════════════════════════


class BulletCreate(BaseModel):
    bullet_text: str = Field(..., min_length=1, max_length=1000)


class BulletOut(BulletCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Experience
# ═══════════════════════════════════════════════════════════════


class ExperienceCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    start_date: Optional[str] = Field(None, max_length=20)
    end_date: Optional[str] = Field(None, max_length=20)
    bullets: list[BulletCreate] = []


class ExperienceUpdate(PatchModel):
    required_fields = ("company", "role")
    company: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[str] = Field(None, max_length=20)
    end_date: Optional[str] = Field(None, max_length=20)


class ExperienceOut(BaseModel):
    id: str
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: list[BulletOut] = []
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Project
# ═══════════════════════════════════════════════════════════════


class ProjectCreate(BaseModel):
    project_title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    tech_stack: Optional[str] = Field(None, max_length=1000)
    bullets: list[BulletCreate] = []


class ProjectUpdate(PatchModel):
    required_fields = ("project_title",)
    project_title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    tech_stack: Optional[str] = Field(None, max_length=1000)


class ProjectOut(BaseModel):
    id: str
    project_title: str
    description: Optional[str] = None
    tech_stack: Optional[str] = None
    bullets: list[BulletOut] = []
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Certification
# ═══════════════════════════════════════════════════════════════


class CertificationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    issuing_organization: Optional[str] = Field(None, max_length=255)
    year: Optional[int] = Field(None, ge=1950, le=2100)


class CertificationUpdate(PatchModel):
    required_fields = ("name",)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    issuing_organization: Optional[str] = Field(None, max_length=255)
    year: Optional[int] = Field(None, ge=1950, le=2100)


class CertificationOut(CertificationCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Achievement
# ═══════════════════════════════════════════════════════════════


class AchievementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=100)


class AchievementUpdate(PatchModel):
    required_fields = ("title",)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=100)


class AchievementOut(AchievementCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  External Profile
# ═══════════════════════════════════════════════════════════════


class ExternalProfileCreate(BaseModel):
    platform: str = Field(..., min_length=1, max_length=100)
    profile_url: str = Field(..., min_length=1, max_length=500)


class ExternalProfileUpdate(PatchModel):
    required_fields = ("platform", "profile_url")
    platform: Optional[str] = Field(None, min_length=1, max_length=100)
    profile_url: Optional[str] = Field(None, min_length=1, max_length=500)


class ExternalProfileOut(ExternalProfileCreate):
    id: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Profile (aggregate)
# ═══════════════════════════════════════════════════════════════


class ProfileOut(BaseModel):
    id: str
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
    raw_text: str = Field(..., min_length=20, max_length=20000)


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
    jd_text: str = Field(..., min_length=20, max_length=20000)


class ResumeOut(BaseModel):
    id: str
    jd_id: Optional[str] = None
    job_title: str
    version: int
    formats: list[str] = []
    created_at: datetime


class GenerateOut(BaseModel):
    resume_id: str
    job_title: str
    version: int
    formats: list[str]
    jd_analysis: JDStructured
    skill_confidence: dict[str, str]
    keyword_coverage: dict[str, bool]
