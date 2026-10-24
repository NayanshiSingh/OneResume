"""Pydantic schemas for all entities."""

from datetime import datetime
from typing import Annotated, ClassVar, Literal, Optional
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


class ProfileImport(BaseModel):
    """Profile sections parsed from an uploaded resume, reviewed before saving."""
    personal_info: Optional[PersonalInfoCreate] = None
    education: list[EducationCreate] = []
    skills: list[SkillCreate] = []
    experience: list[ExperienceCreate] = []
    projects: list[ProjectCreate] = []
    certifications: list[CertificationCreate] = []
    achievements: list[AchievementCreate] = []
    external_profiles: list[ExternalProfileCreate] = []


class ImportPreview(BaseModel):
    mode: str
    warnings: list[str]
    profile: ProfileImport


# ═══════════════════════════════════════════════════════════════
#  JD Analysis
# ═══════════════════════════════════════════════════════════════


class JDSubmit(BaseModel):
    raw_text: str = Field(..., min_length=20, max_length=20000)


SkillTerm = Annotated[str, Field(min_length=1, max_length=200)]


class JDStructured(BaseModel):
    role_title: str = Field("", max_length=255)
    experience_level: str = Field("", max_length=50)
    must_have_skills: list[SkillTerm] = Field([], max_length=60)
    nice_to_have_skills: list[SkillTerm] = Field([], max_length=60)
    keywords: list[SkillTerm] = Field([], max_length=100)
    role_category: str = Field("", max_length=100)


class JDAnalysisOut(BaseModel):
    id: str
    structured_data: JDStructured
    analysis_mode: str
    warnings: list[str]
    reviewed: bool
    created_at: datetime


class EvidenceOut(BaseModel):
    id: str
    kind: str
    text: str


class CoverageItem(BaseModel):
    requirement: str
    importance: str
    label: str
    evidence: list[EvidenceOut]


class AIStatus(BaseModel):
    llm: bool
    embeddings: bool


# ═══════════════════════════════════════════════════════════════
#  Resume Generation
# ═══════════════════════════════════════════════════════════════


class ResumeOut(BaseModel):
    id: str
    jd_id: Optional[str] = None
    draft_id: Optional[str] = None
    job_title: str
    version: int
    formats: list[str] = []
    created_at: datetime


# ═══════════════════════════════════════════════════════════════
#  Jobs and drafts
# ═══════════════════════════════════════════════════════════════


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    result_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class DraftRequest(BaseModel):
    jd_id: str
    page_target: Literal[1, 2] = 1
    idempotency_key: str = Field(..., min_length=1, max_length=100)


DraftSection = Literal["experience", "projects", "education", "skills", "certifications", "achievements", "external_profiles"]


class DraftOp(BaseModel):
    op: Literal["set_included", "set_pinned", "edit_bullet", "revert_bullet"]
    section: DraftSection
    item_id: str
    bullet_id: Optional[str] = None
    value: Optional[bool] = None
    text: Optional[str] = Field(None, max_length=1000)


class DraftEditRequest(BaseModel):
    revision: int
    ops: list[DraftOp] = Field(..., min_length=1, max_length=50)


class ApproveRequest(BaseModel):
    revision: int


class DraftSummary(BaseModel):
    id: str
    jd_id: Optional[str] = None
    job_title: str
    status: str
    revision: int
    matching_mode: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class DraftCoverageItem(CoverageItem):
    in_draft: bool


class EditedBullet(BaseModel):
    section: str
    item_id: str
    bullet_id: str
    original_text: str
    text: str


class DraftOut(DraftSummary):
    page_target: int
    approved_revision: Optional[int] = None
    content: dict
    coverage: list[DraftCoverageItem]
    warnings: list[str]
    edited_bullets: list[EditedBullet]
    exported_resume_id: Optional[str] = None
