"""Optional suggestions for making a profile more useful. Nothing here blocks generation.

The checks ask questions instead of guessing: a vague bullet gets questions
the user can answer in their own words; the AI never fills the gap.
"""

import re
from datetime import date

from app.models.profile import Profile
from app.services.evidence_service import collect_evidence, match_requirement

WARNING, INFO = "warning", "info"
MIN_BULLET_WORDS = 5
_VAGUE = re.compile(
    r"\b(?:stuff|things|various|misc(?:ellaneous)?|etc|worked on|helped with|did (?:some|various)|responsible for|tasks?)\b",
    re.IGNORECASE,
)
_QUESTIONS = [
    "What exactly did you build, change, or fix?",
    "Which tools or technologies did you use?",
    "What was the result? A number helps if you have one.",
]


def _bullet_issue(text: str) -> str | None:
    if len(text.split()) < MIN_BULLET_WORDS:
        return "is very short"
    if _VAGUE.search(text):
        return "is vague"
    return None


def run_checks(profile: Profile) -> list[dict]:
    checks = []
    info = profile.personal_info
    if info is None:
        checks.append({"kind": "contact", "severity": WARNING, "message": "Add your name and an email address or phone number."})
    elif not info.email and not info.phone_number:
        checks.append({"kind": "contact", "severity": WARNING, "message": "Add an email address or phone number so employers can reach you."})
    elif not info.phone_number:
        checks.append({"kind": "contact", "severity": INFO, "message": "No phone number. That is fine, but some applications ask for one."})

    if not (profile.experience or profile.projects or profile.education):
        checks.append({"kind": "empty", "severity": WARNING,
                       "message": "Add at least one experience, project, or education entry, or import an existing resume."})

    this_year = date.today().year
    for edu in profile.education:
        if edu.end_year and edu.end_year >= this_year and not edu.end_month:
            checks.append({"kind": "graduation_month", "severity": INFO, "section": "education", "item_id": edu.id,
                           "message": f"Add the expected graduation month for {edu.degree} at {edu.institution}. "
                                      "New-grad and internship postings often ask for a month range."})

    for section, entries, title in [("experience", profile.experience, lambda e: f"{e.role} at {e.company}"),
                                    ("projects", profile.projects, lambda p: p.project_title)]:
        for entry in entries:
            for bullet in entry.bullets:
                issue = _bullet_issue(bullet.bullet_text)
                if issue:
                    checks.append({"kind": "vague_bullet", "severity": INFO, "section": section, "item_id": entry.id,
                                   "bullet_id": bullet.id, "message": f"\"{bullet.bullet_text}\" ({title(entry)}) {issue}.",
                                   "questions": _QUESTIONS})

    evidence = collect_evidence(profile)
    listed_only = [s.skill_name for s in profile.skills
                   if all(e.kind == "skill" for e in match_requirement(s.skill_name, "required", evidence).evidence)]
    if listed_only:
        checks.append({"kind": "listed_only_skills", "severity": INFO, "skills": listed_only,
                       "message": f"{len(listed_only)} skill(s) appear only in your skills list: {', '.join(listed_only)}. "
                                  "Mention where you used them in an experience or project so they count as evidence."})
    return checks
