"""Relevance Selector — builds draft content from the profile for one job description.

Every profile entry is kept in the draft so the user can restore it; scores
decide which entries and bullets start out included. Entries keep the
user's profile order (normally reverse-chronological): relevance changes
what is shown, never where it sits. Bullet wording is the user's own.

Page budget: experience and project bullets share BULLETS_PER_PAGE per page.
Each included job keeps its best bullet so the timeline stays readable;
the rest of the budget goes to the highest-scoring bullets anywhere, and a
project left with no bullets is left out.
"""

from app.config import settings
from app.domain.resume_draft import JDData
from app.models.profile import Profile
from app.services.embedding_service import embedding_from_json
from app.services.evidence_service import alternatives, contains_term, tokens
from app.services.scoring_engine import score_bullet, score_section


def _top_ids(scored: list[tuple[str, float]], limit: int) -> set[str]:
    return {item_id for item_id, _ in sorted(scored, key=lambda s: s[1], reverse=True)[:limit]}


def _bullets(bullets, jd: JDData, jd_embedding: list[float] | None, section_type: str, end_date) -> list[dict]:
    return [
        {"id": b.id, "text": b.bullet_text, "original_text": b.bullet_text,
         "score": score_bullet(b.bullet_text, embedding_from_json(b.embedding) if jd_embedding else None,
                               jd_embedding or [], jd, section_type, end_date),
         "included": False, "pinned": False, "user_edited": False, "ai_accepted": False, "suggestion": None}
        for b in bullets
    ]


def _select_entries(entries: list[dict], limit: int) -> None:
    included = _top_ids([(e["id"], e["score"]) for e in entries], limit)
    for entry in entries:
        entry["included"] = entry["id"] in included


def _allocate_bullets(experience: list[dict], projects: list[dict], page_target: int) -> None:
    budget = settings.BULLETS_PER_PAGE * page_target
    per_entry = settings.MAX_BULLETS_PER_SECTION + (page_target - 1) * 2
    counts: dict[str, int] = {}

    def take(entry: dict, bullet: dict) -> None:
        nonlocal budget
        bullet["included"] = True
        counts[entry["id"]] = counts.get(entry["id"], 0) + 1
        budget -= 1

    for entry in sorted((e for e in experience if e["included"] and e["bullets"]), key=lambda e: e["score"], reverse=True):
        if budget > 0:
            take(entry, max(entry["bullets"], key=lambda b: b["score"]))
    remaining = sorted(
        ((b["score"], e, b) for e in experience + projects if e["included"] for b in e["bullets"] if not b["included"]),
        key=lambda item: item[0], reverse=True,
    )
    for _, entry, bullet in remaining:
        if budget <= 0:
            break
        if counts.get(entry["id"], 0) < per_entry:
            take(entry, bullet)
    for project in projects:
        project["included"] = project["included"] and counts.get(project["id"], 0) > 0


def select_content(profile: Profile, jd: JDData, jd_embedding: list[float] | None, page_target: int = 1) -> dict:

    experience = [
        {
            "id": exp.id, "title": exp.role,
            "subtitle": f"{exp.company} | {exp.start_date or ''} – {exp.end_date or 'Present'}",
            "score": score_section(f"{exp.role} at {exp.company} " + " ".join(b.bullet_text for b in exp.bullets),
                                   embedding_from_json(exp.experience_embedding) if jd_embedding else None,
                                   jd_embedding or [], jd, "experience", exp.end_date),
            "pinned": False,
            "bullets": _bullets(exp.bullets, jd, jd_embedding, "experience", exp.end_date),
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
            "bullets": _bullets(proj.bullets, jd, jd_embedding, "project", None),
        }
        for proj in profile.projects
    ]

    _select_entries(experience, settings.MAX_EXPERIENCE_SECTIONS * page_target)
    _select_entries(projects, settings.MAX_PROJECT_SECTIONS * page_target)
    _allocate_bullets(experience, projects, page_target)

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
        "experience": experience,
        "projects": projects,
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
