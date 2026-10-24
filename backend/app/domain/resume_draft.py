"""Domain objects shared by the analysis and drafting services."""

from dataclasses import dataclass, field


@dataclass
class JDData:
    """Structured job description data."""
    role_title: str = ""
    experience_level: str = ""
    must_have_skills: list[str] = field(default_factory=list)
    nice_to_have_skills: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    role_category: str = ""
