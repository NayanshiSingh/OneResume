"""Relevance Selector — picks top-N sections and top-K bullets.

Implements must-have skill handling with graceful degradation:
  1. Direct match → "strong"
  2. Semantic equivalent → "inferred"
  3. Weak match / fallback → "weak"

Resume generation NEVER fails due to missing skills.
"""

import json
import logging
from sqlalchemy.orm import Session

from app.config import settings
from app.models.profile import (
    Profile, Experience, ExperienceBullet, Project, ProjectBullet,
    Skill, Education, Certification, Achievement, ExternalProfile, PersonalInfo,
)
from app.domain.resume_draft import ResumeDraft, JDData, ScoredSection, ScoredBullet
from app.services.embedding_service import (
    generate_embedding, embedding_from_json, cosine_similarity,
)
from app.services.scoring_engine import score_bullet, score_section

logger = logging.getLogger(__name__)


def _check_skill_confidence(
    skill: str,
    profile_skills: list[str],
    all_bullet_texts: list[str],
    jd_embedding: list[float],
) -> str:
    """Determine confidence level for a must-have skill."""
    skill_lower = skill.lower()

    # 1. Direct match
    for ps in profile_skills:
        if skill_lower == ps.lower():
            return "strong"
        if skill_lower in ps.lower() or ps.lower() in skill_lower:
            return "strong"

    # 2. Semantic inference from bullet texts
    for bullet in all_bullet_texts:
        if skill_lower in bullet.lower():
            return "inferred"

    # 3. Semantic similarity check
    try:
        skill_emb = generate_embedding(skill)
        for bullet in all_bullet_texts[:20]:  # limit for performance
            bullet_emb = generate_embedding(bullet)
            sim = cosine_similarity(skill_emb, bullet_emb)
            if sim > 0.6:
                return "inferred"
    except Exception:
        pass

    return "weak"


def select_relevant_content(
    db: Session,
    profile: Profile,
    jd_data: JDData,
    jd_embedding: list[float],
) -> ResumeDraft:
    """Select and score the most relevant profile content for a JD."""
    draft = ResumeDraft(profile_id=profile.id)
    draft.jd_data = jd_data
    draft.jd_embedding = jd_embedding
    draft.job_title = jd_data.role_title

    # ── Gather all profile data ───────────────────────────────
    profile_skills = [s.skill_name for s in profile.skills]
    all_bullet_texts = []

    # ── Score Experience Sections ─────────────────────────────
    scored_exp_sections: list[ScoredSection] = []

    for exp in profile.experience:
        section_text = f"{exp.role} at {exp.company}"
        section_emb = embedding_from_json(exp.experience_embedding)

        sec_score = score_section(
            section_text, section_emb, jd_embedding,
            jd_data, "experience", exp.end_date,
        )

        scored_bullets: list[ScoredBullet] = []
        for bullet in exp.bullets:
            all_bullet_texts.append(bullet.bullet_text)
            b_emb = embedding_from_json(bullet.embedding)
            b_score = score_bullet(
                bullet.bullet_text, b_emb, jd_embedding,
                jd_data, "experience", exp.end_date,
            )
            scored_bullets.append(ScoredBullet(
                id=bullet.id, text=bullet.bullet_text,
                score=b_score, confidence="strong",
            ))

        # Sort bullets by score, keep top K
        scored_bullets.sort(key=lambda b: b.score, reverse=True)
        scored_bullets = scored_bullets[:settings.MAX_BULLETS_PER_SECTION]

        scored_exp_sections.append(ScoredSection(
            id=exp.id,
            title=f"{exp.role}",
            subtitle=f"{exp.company} | {exp.start_date or ''} – {exp.end_date or 'Present'}",
            section_type="experience",
            score=sec_score,
            bullets=scored_bullets,
        ))

    # Sort and keep top N experience sections
    scored_exp_sections.sort(key=lambda s: s.score, reverse=True)
    draft.experience_sections = scored_exp_sections[:settings.MAX_EXPERIENCE_SECTIONS]

    # ── Score Project Sections ────────────────────────────────
    scored_proj_sections: list[ScoredSection] = []

    for proj in profile.projects:
        section_text = f"{proj.project_title}: {proj.description or ''}"
        sec_score = score_section(
            section_text, None, jd_embedding,
            jd_data, "project", None,
        )

        scored_bullets: list[ScoredBullet] = []
        for bullet in proj.bullets:
            all_bullet_texts.append(bullet.bullet_text)
            b_emb = embedding_from_json(bullet.embedding)
            b_score = score_bullet(
                bullet.bullet_text, b_emb, jd_embedding,
                jd_data, "project", None,
            )
            scored_bullets.append(ScoredBullet(
                id=bullet.id, text=bullet.bullet_text,
                score=b_score, confidence="strong",
            ))

        scored_bullets.sort(key=lambda b: b.score, reverse=True)
        scored_bullets = scored_bullets[:settings.MAX_BULLETS_PER_SECTION]

        scored_proj_sections.append(ScoredSection(
            id=proj.id,
            title=proj.project_title,
            subtitle=proj.tech_stack or "",
            section_type="project",
            score=sec_score,
            bullets=scored_bullets,
        ))

    scored_proj_sections.sort(key=lambda s: s.score, reverse=True)
    draft.project_sections = scored_proj_sections[:settings.MAX_PROJECT_SECTIONS]

    # ── Select Skills (dedup + limit) ─────────────────────────
    all_jd_skills = jd_data.must_have_skills + jd_data.nice_to_have_skills
    selected = []
    seen = set()
    # Prioritize JD-matching skills
    for skill in profile_skills:
        skill_lower = skill.lower()
        if skill_lower in seen:
            continue
        for jd_skill in all_jd_skills:
            if jd_skill.lower() in skill_lower or skill_lower in jd_skill.lower():
                selected.append(skill)
                seen.add(skill_lower)
                break
    # Fill remaining with other profile skills
    for skill in profile_skills:
        if skill.lower() not in seen:
            selected.append(skill)
            seen.add(skill.lower())
    draft.selected_skills = selected[:settings.MAX_SKILLS]

    # ── Must-Have Skill Confidence ────────────────────────────
    for skill in jd_data.must_have_skills:
        confidence = _check_skill_confidence(
            skill, profile_skills, all_bullet_texts, jd_embedding,
        )
        draft.skill_confidence[skill] = confidence

    # ── Education, Certs, Achievements, etc. ──────────────────
    draft.education = [
        {"institution": e.institution, "degree": e.degree,
         "field_of_study": e.field_of_study or "",
         "start_year": e.start_year, "end_year": e.end_year,
         "grade": e.grade or ""}
        for e in profile.education
    ]

    draft.certifications = [
        {"name": c.name, "issuing_organization": c.issuing_organization or "",
         "year": c.year}
        for c in profile.certifications
    ]

    draft.achievements = [
        {"title": a.title, "description": a.description or "",
         "category": a.category or ""}
        for a in profile.achievements
    ]

    if profile.personal_info:
        pi = profile.personal_info
        draft.personal_info = {
            "full_name": pi.full_name,
            "email": pi.email or "",
            "phone_number": pi.phone_number or "",
        }

    draft.external_profiles = [
        {"platform": ep.platform, "profile_url": ep.profile_url}
        for ep in profile.external_profiles
    ]

    return draft
