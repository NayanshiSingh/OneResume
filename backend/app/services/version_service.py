"""Resume versions: compare two exports, restore one as a new draft, mark when sent.

Each export stores the exact draft content it was rendered from, so a version
can be reproduced or restored later even after the profile has changed.
Restoring never overwrites anything: it creates a new draft.
"""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.errors import InvalidRequestError
from app.models.draft import Draft
from app.models.resume import Resume
from app.models.user import User
from app.repositories import JDAnalysisRepo
from app.services import evidence_service, profile_service
from app.services.jd_service import structured
from app.services.resume_assembler import assemble_resume


def assembled(resume: Resume) -> dict:
    if not resume.content_snapshot:
        raise InvalidRequestError(f"Version {resume.version} was exported before version history was kept")
    return assemble_resume(json.loads(resume.content_snapshot), resume.job_title)


def _entries(data: dict, section: str) -> dict[str, list[str]]:
    return {e["title"]: e["bullets"] for e in data[section]}


def compare(older: Resume, newer: Resume) -> dict:
    """What changed from one version to another: entries, bullets, and skills."""
    a, b = assembled(older), assembled(newer)
    changes = []
    for section in ("experience", "projects"):
        before, after = _entries(a, section), _entries(b, section)
        for title in after.keys() - before.keys():
            changes.append({"section": section, "entry": title, "kind": "added_entry", "text": title})
        for title in before.keys() - after.keys():
            changes.append({"section": section, "entry": title, "kind": "removed_entry", "text": title})
        for title in before.keys() & after.keys():
            changes += [{"section": section, "entry": title, "kind": "added_bullet", "text": t}
                        for t in after[title] if t not in before[title]]
            changes += [{"section": section, "entry": title, "kind": "removed_bullet", "text": t}
                        for t in before[title] if t not in after[title]]
    changes += [{"section": "skills", "entry": None, "kind": "added_skill", "text": s} for s in b["skills"] if s not in a["skills"]]
    changes += [{"section": "skills", "entry": None, "kind": "removed_skill", "text": s} for s in a["skills"] if s not in b["skills"]]
    return {"from_version": older.version, "to_version": newer.version, "changes": changes}


def restore(db: Session, user: User, resume: Resume) -> Draft:
    """Start a new draft from exactly what this version contained."""
    assembled(resume)  # fails clearly for versions without a snapshot
    source = resume.draft
    coverage = json.loads(source.coverage) if source else []
    if resume.jd_id:
        record = JDAnalysisRepo.get_owned(db, user.id, resume.jd_id)
        coverage = [m.to_dict() for m in evidence_service.coverage(profile_service.get_profile(db, user), structured(record))]
    draft = Draft(
        profile_id=resume.profile_id, jd_id=resume.jd_id, job_title=resume.job_title,
        page_target=source.page_target if source else 1,
        matching_mode=source.matching_mode if source else "basic",
        content=resume.content_snapshot, coverage=json.dumps(coverage),
        warnings=json.dumps([
            f"Restored from version {resume.version}. Entries are exactly as they were then; "
            "later profile changes are not included."
        ]),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def set_sent(db: Session, resume: Resume, sent_at: datetime | None) -> Resume:
    resume.sent_at = sent_at
    db.commit()
    db.refresh(resume)
    return resume
