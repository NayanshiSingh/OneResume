"""Relevance Selector — builds draft content from the profile for one job description.

Every profile entry is kept in the draft so the user can restore it; scores
decide which entries and bullets start out included. Entries keep the
user's profile order (normally reverse-chronological): relevance changes
what is shown, never where it sits. Bullet wording is the user's own.
"""

from app.config import settings
from app.domain.resume_draft import JDData
from app.models.profile import Profile
from app.services.embedding_service import embedding_from_json
from app.services.evidence_service import alternatives, contains_term, tokens
from app.services.scoring_engine import score_bullet, score_section


def _top_ids(scored: list[tuple[str, float]], limit: int) -> set[str]:
    return {item_id for item_id, _ in sorted(scored, key=lambda s: s[1], reverse=True)[:limit]}


def _bullets(bullets, jd: JDData, jd_embedding: list[float] | None, section_type: str, end_date, limit: int) -> list[dict]:
    scored = [
        (b.id, score_bullet(b.bullet_text, embedding_from_json(b.embedding) if jd_embedding else None,
                            jd_embedding or [], jd, section_type, end_date))
        for b in bullets
    ]
    included = _top_ids(scored, limit)
    return [
        {"id": b.id, "text": b.bullet_text, "original_text": b.bullet_text, "score": score,
         "included": b.id in included, "pinned": False, "user_edited": False,
         "ai_accepted": False, "suggestion": None}
        for b, (_, score) in zip(bullets, scored)
    ]


def _select_entries(entries: list[dict], limit: int) -> list[dict]:
    included = _top_ids([(e["id"], e["score"]) for e in entries], limit)
    for entry in entries:
        entry["included"] = entry["id"] in included
    return entries


def select_content(profile: Profile, jd: JDData, jd_embedding: list[float] | None, page_target: int = 1) -> dict:
    max_bullets = settings.MAX_BULLETS_PER_SECTION + (page_target - 1) * 2

    experience = [
        {
            "id": exp.id, "title": exp.role,
            "subtitle": f"{exp.company} | {exp.start_date or ''} – {exp.end_date or 'Present'}",
            "score": score_section(f"{exp.role} at {exp.company} " + " ".join(b.bullet_text for b in exp.bullets),
                                   embedding_from_json(exp.experience_embedding) if jd_embedding else None,
                                   jd_embedding or [], jd, "experience", exp.end_date),
            "pinned": False,
            "bullets": _bullets(exp.bullets, jd, jd_embedding, "experience", exp.end_date, max_bullets),
        }
        for exp in profile.experience
    ]
    projects = [
        {
            "id": proj.id, "title": proj.project_title, "subtitle": proj.tech_stack or "",
            "score": score_section(" ".join([proj.project_title, proj.description or "", proj.tech_stack or ""]
                                            + [b.bullet_text for b in proj.bullets]),
                                   None, [], jd, "project", None),
            "pinned": False,
            "bullets": _bullets(proj.bullets, jd, jd_embedding, "project", None, max_bullets),
        }
        for proj in profile.projects
    ]

    jd_terms = jd.must_have_skills + jd.nice_to_have_skills
    skills = []
    for skill in profile.skills:
        skill_tokens = tokens(skill.skill_name)
        matches = any(contains_term(skill_tokens, t) or contains_term(tokens(t), skill.skill_name)
                      for req in jd_terms for t in alternatives(req))
        skills.append({"id": skill.id, "name": skill.skill_name, "matches_jd": matches})
    # JD-relevant skills first, then the rest, each group in profile order.
    skills.sort(key=lambda s: not s["matches_jd"])
    for i, skill in enumerate(skills):
        skill["included"] = i < settings.MAX_SKILLS * page_target

    pi = profile.personal_info
    return {
        "personal_info": {"full_name": pi.full_name, "email": pi.email or "", "phone_number": pi.phone_number or ""} if pi else None,
        "external_profiles": [
            {"id": ep.id, "platform": ep.platform, "profile_url": ep.profile_url, "included": True}
            for ep in profile.external_profiles
        ],
        "education": [
            {"id": e.id, "institution": e.institution, "degree": e.degree, "field_of_study": e.field_of_study or "",
             "start_year": e.start_year, "end_year": e.end_year, "end_month": e.end_month,
             "grade": e.grade or "", "included": True}
            for e in profile.education
        ],
        "experience": _select_entries(experience, settings.MAX_EXPERIENCE_SECTIONS * page_target),
        "projects": _select_entries(projects, settings.MAX_PROJECT_SECTIONS * page_target),
        "skills": skills,
        "certifications": [
            {"id": c.id, "name": c.name, "issuing_organization": c.issuing_organization or "", "year": c.year, "included": True}
            for c in profile.certifications
        ],
        "achievements": [
            {"id": a.id, "title": a.title, "description": a.description or "", "category": a.category or "", "included": True}
            for a in profile.achievements
        ],
    }
