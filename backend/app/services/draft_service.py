"""Drafts: build from the profile and reviewed JD, edit, approve one revision, export it.

Drafts use the user's own bullet wording. Matching runs with embeddings when
Pinecone is configured and falls back to labelled exact-word matching when
it is not or when the call fails.
"""

import json
import logging

import numpy as np
from sqlalchemy.orm import Session

from app.errors import ConflictError, InvalidRequestError, NotFoundError
from app.models.draft import Draft, GenerationJob
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User
from app.repositories import JDAnalysisRepo, ResumeRepo
from app.services import evidence_service, job_service, profile_service, rewrite_service, usage_service
from app.services.ai_status import AI, BASIC, embeddings_available
from app.services.embedding_service import embedding_from_json, embedding_to_json, generate_embedding, generate_embeddings
from app.services import output_check
from app.services.export_service import create_resume_record, render_and_store
from app.services.pdf_renderer import render_resume_pdf
from app.services.jd_service import structured
from app.services.relevance_selector import select_content
from app.services.resume_assembler import assemble_resume, resume_to_sections_json

logger = logging.getLogger(__name__)

DRAFT_JOB = "draft"
BULLET_SECTIONS = {"experience", "projects"}
MATCHING_OFF = "Semantic matching is off, so only exact words were compared. Related experience written differently may be missed."
MATCHING_FAILED = "Semantic matching failed, so only exact words were compared. Related experience written differently may be missed."


# ── Building ─────────────────────────────────────────────────


def request_draft(db: Session, user: User, jd_id: str, page_target: int, idempotency_key: str) -> GenerationJob:
    JDAnalysisRepo.get_owned(db, user.id, jd_id)  # fail now rather than inside the job
    existing = job_service.find(db, user, idempotency_key)
    if existing:
        return existing
    usage_service.consume(db, user, usage_service.DRAFT)
    payload = {"jd_id": jd_id, "page_target": page_target}
    return job_service.enqueue(db, user, DRAFT_JOB, payload, idempotency_key)


@job_service.register(DRAFT_JOB)
def _build_from_job(db: Session, job: GenerationJob) -> str:
    payload = json.loads(job.payload)
    return build_draft(db, db.get(User, job.user_id), payload["jd_id"], payload["page_target"]).id


def _ensure_profile_embeddings(profile: Profile) -> None:
    bullets = [b for section in profile.experience + profile.projects for b in section.bullets if not b.embedding]
    for bullet, vector in zip(bullets, generate_embeddings([b.bullet_text for b in bullets])):
        bullet.embedding = embedding_to_json(vector)
    for exp in profile.experience:
        if not exp.experience_embedding and exp.bullets:
            vectors = [embedding_from_json(b.embedding) for b in exp.bullets]
            exp.experience_embedding = embedding_to_json(np.mean(vectors, axis=0).tolist())


def _embeddings(db: Session, profile: Profile, record, jd) -> tuple[str, list[float] | None, list[str]]:
    if not embeddings_available():
        return BASIC, None, [MATCHING_OFF]
    try:
        if not record.embedding:
            jd_text = " ".join([jd.role_title, *jd.must_have_skills, *jd.nice_to_have_skills, *jd.keywords])
            record.embedding = embedding_to_json(generate_embedding(jd_text))
        _ensure_profile_embeddings(profile)
        db.commit()
        return AI, embedding_from_json(record.embedding), []
    except Exception:  # provider boundary: any failure falls back to labelled basic matching
        logger.exception("Embedding provider failed; using basic matching")
        db.rollback()
        return BASIC, None, [MATCHING_FAILED]


def _profile_warnings(profile: Profile, record, coverage: list[evidence_service.RequirementMatch]) -> list[str]:
    warnings = []
    if record.reviewed_at is None:
        warnings.append("The job description analysis was not reviewed. Check the requirements on the job description page.")
    if profile.personal_info is None:
        warnings.append("Add your name and contact details on the profile page.")
    elif not profile.personal_info.phone_number:
        warnings.append("No phone number. That is fine, but some applications ask for one.")
    listed_only = sum(1 for m in coverage if m.label == evidence_service.NEEDS_CONFIRMATION)
    if listed_only:
        warnings.append(f"{listed_only} requirement(s) appear only in your skills list. Add an example to an experience or project, or confirm you have them.")
    return warnings


def build_draft(db: Session, user: User, jd_id: str, page_target: int) -> Draft:
    profile = profile_service.get_profile(db, user)
    record = JDAnalysisRepo.get_owned(db, user.id, jd_id)
    jd = structured(record)
    mode, jd_embedding, warnings = _embeddings(db, profile, record, jd)
    coverage = evidence_service.coverage(profile, jd)
    content = select_content(profile, jd, jd_embedding, page_target)
    warnings += rewrite_service.add_suggestions(content, jd, [s.skill_name for s in profile.skills])
    draft = Draft(
        profile_id=profile.id, jd_id=record.id, job_title=jd.role_title or "Untitled role",
        page_target=page_target, matching_mode=mode,
        content=json.dumps(content),
        coverage=json.dumps([m.to_dict() for m in coverage]),
        warnings=json.dumps(warnings + _profile_warnings(profile, record, coverage)),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


# ── Reading ──────────────────────────────────────────────────


def get_owned(db: Session, user: User, draft_id: str) -> Draft:
    draft = (
        db.query(Draft).join(Profile, Draft.profile_id == Profile.id)
        .filter(Draft.id == draft_id, Profile.user_id == user.id).first()
    )
    if not draft:
        raise NotFoundError("Draft not found")
    return draft


def list_owned(db: Session, user: User) -> list[Draft]:
    return (
        db.query(Draft).join(Profile, Draft.profile_id == Profile.id)
        .filter(Profile.user_id == user.id).order_by(Draft.created_at.desc()).all()
    )


def _included_ids(content: dict) -> set[str]:
    ids = set()
    for section in ["education", "certifications", "achievements", "skills", "external_profiles"]:
        ids |= {item["id"] for item in content[section] if item["included"]}
    for section in BULLET_SECTIONS:
        for entry in content[section]:
            if entry["included"]:
                ids.add(entry["id"])
                ids |= {b["id"] for b in entry["bullets"] if b["included"]}
    return ids


def view(draft: Draft) -> dict:
    content = json.loads(draft.content)
    included = _included_ids(content)
    coverage = [
        {**item, "in_draft": any(e["id"] in included for e in item["evidence"])}
        for item in json.loads(draft.coverage)
    ]
    def changed(flag: str) -> list[dict]:
        return [
            {"section": section, "item_id": entry["id"], "bullet_id": b["id"], "original_text": b["original_text"], "text": b["text"]}
            for section in sorted(BULLET_SECTIONS) for entry in content[section] for b in entry["bullets"] if b.get(flag)
        ]

    exported = next((r.id for r in draft.resumes if r.draft_revision == draft.revision), None)
    return {
        "id": draft.id, "jd_id": draft.jd_id, "job_title": draft.job_title, "page_target": draft.page_target,
        "matching_mode": draft.matching_mode, "status": draft.status, "revision": draft.revision,
        "approved_revision": draft.approved_revision, "created_at": draft.created_at, "updated_at": draft.updated_at,
        "content": content, "coverage": coverage, "warnings": json.loads(draft.warnings),
        "edited_bullets": changed("user_edited"), "accepted_suggestions": changed("ai_accepted"),
        "exported_resume_id": exported,
    }


# ── Editing and approval ─────────────────────────────────────


def _target(content: dict, op) -> dict:
    item = next((i for i in content.get(op.section, []) if i["id"] == op.item_id), None)
    if item is None:
        raise InvalidRequestError(f"No {op.section} item {op.item_id} in this draft")
    if op.bullet_id is None:
        return item
    if op.section not in BULLET_SECTIONS:
        raise InvalidRequestError(f"{op.section} entries have no bullets")
    bullet = next((b for b in item["bullets"] if b["id"] == op.bullet_id), None)
    if bullet is None:
        raise InvalidRequestError(f"No bullet {op.bullet_id} in this entry")
    return bullet


def _apply(content: dict, op) -> None:
    target = _target(content, op)
    if op.op in {"set_included", "set_pinned"} and op.value is None:
        raise InvalidRequestError(f"{op.op} needs a value")
    if op.op in {"edit_bullet", "revert_bullet", "accept_suggestion"} and op.bullet_id is None:
        raise InvalidRequestError(f"{op.op} needs a bullet_id")
    if op.op == "set_included":
        target["included"] = op.value
        if not op.value:
            target["pinned"] = False
    elif op.op == "set_pinned":
        target["pinned"] = op.value
        target["included"] = target["included"] or op.value
    elif op.op == "edit_bullet":
        if not op.text or not op.text.strip():
            raise InvalidRequestError("Bullet text cannot be empty")
        target["text"] = op.text.strip()
        target["user_edited"] = target["text"] != target["original_text"]
        target["ai_accepted"] = False
    elif op.op == "accept_suggestion":
        suggestion = target.get("suggestion")
        if not suggestion or suggestion["status"] != rewrite_service.SAFE:
            raise InvalidRequestError("Only suggestions that passed every check can be accepted")
        target["text"], target["user_edited"], target["ai_accepted"] = suggestion["text"], False, True
    elif op.op == "revert_bullet":
        target["text"], target["user_edited"], target["ai_accepted"] = target["original_text"], False, False


def _check_revision(draft: Draft, revision: int) -> None:
    if revision != draft.revision:
        raise ConflictError("This draft changed since you loaded it. Reload and try again.")


def edit(db: Session, user: User, draft_id: str, revision: int, ops: list) -> Draft:
    draft = get_owned(db, user, draft_id)
    _check_revision(draft, revision)
    content = json.loads(draft.content)
    for op in ops:
        _apply(content, op)
    draft.content = json.dumps(content)
    draft.revision += 1
    draft.status, draft.approved_revision = "draft", None
    db.commit()
    db.refresh(draft)
    return draft


def approve(db: Session, user: User, draft_id: str, revision: int) -> Draft:
    draft = get_owned(db, user, draft_id)
    _check_revision(draft, revision)
    draft.status, draft.approved_revision = "approved", revision
    db.commit()
    db.refresh(draft)
    return draft


def export(db: Session, user: User, draft_id: str) -> Resume:
    """Render the approved revision. Exporting the same revision again returns the same resume."""
    draft = get_owned(db, user, draft_id)
    if draft.status != "approved" or draft.approved_revision != draft.revision:
        raise ConflictError("Approve the current revision before exporting")
    existing = next((r for r in draft.resumes if r.draft_revision == draft.revision), None)
    if existing:
        return existing

    resume_data = assemble_resume(json.loads(draft.content), draft.job_title)
    resume = create_resume_record(db, draft.profile_id, draft.jd_id, draft.job_title, draft.id, draft.revision)
    resume.content_snapshot = draft.content
    render_and_store(db, user, resume, resume_data, draft.page_target)
    for section in resume_to_sections_json(resume_data):
        ResumeRepo.add_section(db, resume.id, section_type=section["section_type"],
                               content=section["content"], confidence_flags=section.get("confidence_flags"))
    db.refresh(resume)
    return resume


MAX_REMOVAL_CANDIDATES = 5


def layout(draft: Draft) -> dict:
    """Render the current revision to count pages; when it overflows, suggest what to cut.

    Candidates are included, unpinned bullets, least useful first: bullets that
    support no requirement come before ones that do, then lower relevance first.
    """
    content = json.loads(draft.content)
    try:
        _, pages = output_check.extract_pdf(render_resume_pdf(assemble_resume(content, draft.job_title)))
    except Exception:  # renderer boundary: the length check is optional
        logger.exception("Layout check failed for draft %s", draft.id)
        return {"available": False, "pages": None, "page_target": draft.page_target, "fits": None, "candidates": []}

    covers: dict[str, list[str]] = {}
    for item in json.loads(draft.coverage):
        for evidence in item["evidence"]:
            covers.setdefault(evidence["id"], []).append(item["requirement"])
    candidates = sorted(
        (
            {"section": section, "item_id": entry["id"], "bullet_id": b["id"], "entry": entry["title"],
             "text": b["text"], "covers": covers.get(b["id"], []), "score": b["score"]}
            for section in sorted(BULLET_SECTIONS) for entry in content[section] if entry["included"]
            for b in entry["bullets"] if b["included"] and not b["pinned"] and not entry["pinned"]
        ),
        key=lambda c: (bool(c["covers"]), c["score"]),
    )
    fits = pages <= draft.page_target
    return {"available": True, "pages": pages, "page_target": draft.page_target, "fits": fits,
            "candidates": [] if fits else candidates[:MAX_REMOVAL_CANDIDATES]}


def delete(db: Session, user: User, draft_id: str) -> None:
    db.delete(get_owned(db, user, draft_id))
    db.commit()
