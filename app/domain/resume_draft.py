"""ResumeDraft — core domain object passed through the generation pipeline."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScoredBullet:
    """A bullet point with its relevance score and confidence."""
    id: str
    text: str
    score: float = 0.0
    confidence: str = "strong"  # strong | inferred | weak
    rewritten_text: str = ""


@dataclass
class ScoredSection:
    """A profile section (experience or project) with scored bullets."""
    id: str
    title: str  # role@company or project title
    subtitle: str = ""  # dates or tech stack
    section_type: str = ""  # "experience" or "project"
    score: float = 0.0
    bullets: list[ScoredBullet] = field(default_factory=list)


@dataclass
class JDData:
    """Structured job description data."""
    role_title: str = ""
    experience_level: str = ""
    must_have_skills: list[str] = field(default_factory=list)
    nice_to_have_skills: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    role_category: str = ""


@dataclass
class ResumeDraft:
    """Single object threaded through the entire resume generation pipeline.

    Contains: profile ref, JD analysis, selected sections/bullets,
    scores, confidence flags, and version metadata.
    """
    profile_id: str
    jd_id: str = ""
    jd_data: Optional[JDData] = None
    jd_embedding: list[float] = field(default_factory=list)

    # Selected & scored content
    experience_sections: list[ScoredSection] = field(default_factory=list)
    project_sections: list[ScoredSection] = field(default_factory=list)
    selected_skills: list[str] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    certifications: list[dict] = field(default_factory=list)
    achievements: list[dict] = field(default_factory=list)
    personal_info: Optional[dict] = None
    external_profiles: list[dict] = field(default_factory=list)

    # Confidence tracking
    skill_confidence: dict[str, str] = field(default_factory=dict)
    # must-have skill → strong/inferred/weak

    # Metadata
    job_title: str = ""
    version: int = 1

    # ATS info
    keyword_coverage: dict[str, bool] = field(default_factory=dict)
