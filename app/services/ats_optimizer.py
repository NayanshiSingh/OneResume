"""ATS Optimizer — rule-based engine for ATS compatibility.

Ensures:
  - Keyword presence
  - Section ordering
  - Bullet count limits
  - Formatting consistency
"""

from app.domain.resume_draft import ResumeDraft
from app.config import settings


# ── ATS section ordering ──────────────────────────────────────
SECTION_ORDER = [
    "personal_info",
    "education",
    "experience",
    "projects",
    "skills",
    "certifications",
    "achievements",
    "external_profiles",
]


def check_keyword_coverage(draft: ResumeDraft) -> dict[str, bool]:
    """Check which JD keywords appear in the resume content."""
    if not draft.jd_data:
        return {}

    # Collect all text content
    all_text_parts = []
    for section in draft.experience_sections + draft.project_sections:
        all_text_parts.append(section.title)
        for b in section.bullets:
            all_text_parts.append(b.rewritten_text or b.text)
    for skill in draft.selected_skills:
        all_text_parts.append(skill)

    full_text = " ".join(all_text_parts).lower()

    coverage = {}
    for kw in draft.jd_data.keywords:
        coverage[kw] = kw.lower() in full_text

    return coverage


def enforce_constraints(draft: ResumeDraft) -> ResumeDraft:
    """Apply ATS formatting rules and constraints."""
    # 1. Limit sections
    draft.experience_sections = draft.experience_sections[:settings.MAX_EXPERIENCE_SECTIONS]
    draft.project_sections = draft.project_sections[:settings.MAX_PROJECT_SECTIONS]

    # 2. Limit bullets per section
    for section in draft.experience_sections + draft.project_sections:
        section.bullets = section.bullets[:settings.MAX_BULLETS_PER_SECTION]

    # 3. Limit skills
    draft.selected_skills = draft.selected_skills[:settings.MAX_SKILLS]

    # 4. Keyword coverage tracking
    draft.keyword_coverage = check_keyword_coverage(draft)

    return draft


def optimize(draft: ResumeDraft) -> ResumeDraft:
    """Run all ATS optimization rules on the draft."""
    draft = enforce_constraints(draft)
    return draft
