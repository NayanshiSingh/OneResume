"""Scoring Engine — composite relevance scoring for profile items.

Formula (conceptual):
  final_score = semantic_similarity
                × skill_importance_weight
                × section_priority_weight
                × recency_weight
                + keyword_bonus
"""

import re
from datetime import datetime

from app.domain.resume_draft import JDData
from app.services.embedding_service import cosine_similarity


# ── Weight configuration ──────────────────────────────────────

SECTION_PRIORITY = {
    "experience": 1.0,
    "project": 0.85,
    "skill": 0.7,
    "education": 0.6,
    "certification": 0.5,
}

SKILL_IMPORTANCE = {
    "must_have": 1.5,
    "nice_to_have": 1.0,
}

KEYWORD_BONUS = 0.05  # per matching keyword


# ── Scoring functions ─────────────────────────────────────────


def compute_recency_weight(end_date: str | None) -> float:
    """Compute a recency weight (1.0 for current/recent, decaying for older).

    Expects end_date in 'YYYY-MM' format or 'Present'.
    """
    if not end_date or end_date.lower() == "present":
        return 1.0
    try:
        year = int(end_date.split("-")[0])
        current_year = datetime.now().year
        years_ago = max(0, current_year - year)
        # Decay: 1.0 for current, 0.6 minimum for very old
        return max(0.6, 1.0 - (years_ago * 0.05))
    except (ValueError, IndexError):
        return 0.8


def compute_keyword_bonus(text: str, jd_data: JDData) -> float:
    """Count how many JD keywords appear in the text."""
    text_lower = text.lower()
    bonus = 0.0
    for kw in jd_data.keywords:
        if kw.lower() in text_lower:
            bonus += KEYWORD_BONUS
    return min(bonus, 0.3)  # cap at 0.3


def compute_skill_importance(bullet_text: str, jd_data: JDData) -> float:
    """Check if the bullet mentions must-have or nice-to-have skills."""
    text_lower = bullet_text.lower()

    for skill in jd_data.must_have_skills:
        if skill.lower() in text_lower:
            return SKILL_IMPORTANCE["must_have"]

    for skill in jd_data.nice_to_have_skills:
        if skill.lower() in text_lower:
            return SKILL_IMPORTANCE["nice_to_have"]

    return 1.0  # neutral


def score_bullet(
    bullet_text: str,
    bullet_embedding: list[float] | None,
    jd_embedding: list[float],
    jd_data: JDData,
    section_type: str = "experience",
    end_date: str | None = None,
) -> float:
    """Compute composite score for a single bullet point."""
    # Semantic similarity
    if bullet_embedding and jd_embedding:
        semantic = cosine_similarity(bullet_embedding, jd_embedding)
    else:
        semantic = 0.3  # default if no embeddings

    # Weights
    importance = compute_skill_importance(bullet_text, jd_data)
    priority = SECTION_PRIORITY.get(section_type, 0.7)
    recency = compute_recency_weight(end_date)
    kw_bonus = compute_keyword_bonus(bullet_text, jd_data)

    final = semantic * importance * priority * recency + kw_bonus
    return round(final, 4)


def score_section(
    section_text: str,
    section_embedding: list[float] | None,
    jd_embedding: list[float],
    jd_data: JDData,
    section_type: str = "experience",
    end_date: str | None = None,
) -> float:
    """Compute a section-level score (used for ranking sections)."""
    if section_embedding and jd_embedding:
        semantic = cosine_similarity(section_embedding, jd_embedding)
    else:
        semantic = 0.3

    priority = SECTION_PRIORITY.get(section_type, 0.7)
    recency = compute_recency_weight(end_date)
    kw_bonus = compute_keyword_bonus(section_text, jd_data)

    return round(semantic * priority * recency + kw_bonus, 4)
