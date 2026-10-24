"""Orchestrator — end-to-end resume generation pipeline.

Flow:
  JD text → JD Analysis → Embedding → Profile scoring →
  Relevance selection → LLM rewriting → ATS optimization →
  Assembly → Rendering → Storage
"""

import json
import logging

import numpy as np
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import JDAnalysisRepo, ResumeRepo
from app.services import profile_service
from app.services.jd_analyzer import analyze_jd, jd_to_dict
from app.services.embedding_service import (
    generate_embedding, generate_embeddings, embedding_to_json,
)
from app.services.relevance_selector import select_relevant_content
from app.services.llm_service import rewrite_draft_bullets
from app.services.ats_optimizer import optimize
from app.services.resume_assembler import assemble_resume, resume_to_sections_json
from app.services.pdf_renderer import render_resume_pdf
from app.services.export_service import export_to_docx, store_artifact

logger = logging.getLogger(__name__)

VERSION_ATTEMPTS = 3


def _ensure_embeddings(db: Session, profile):
    """Generate and store embeddings for profile bullets that lack them."""
    changed = False

    for exp in profile.experience:
        for bullet in exp.bullets:
            if not bullet.embedding:
                emb = generate_embedding(bullet.bullet_text)
                bullet.embedding = embedding_to_json(emb)
                changed = True
        # Section-level embedding (average of bullets)
        if not exp.experience_embedding and exp.bullets:
            texts = [b.bullet_text for b in exp.bullets]
            embs = generate_embeddings(texts)
            avg = np.mean(embs, axis=0).tolist()
            exp.experience_embedding = embedding_to_json(avg)
            changed = True

    for proj in profile.projects:
        for bullet in proj.bullets:
            if not bullet.embedding:
                emb = generate_embedding(bullet.bullet_text)
                bullet.embedding = embedding_to_json(emb)
                changed = True

    if changed:
        db.commit()


def _create_resume_record(db: Session, profile_id: str, jd_id: str, job_title: str):
    """Create the resume with the next free version, retrying if a concurrent run took it."""
    for _ in range(VERSION_ATTEMPTS):
        version = ResumeRepo.get_next_version(db, profile_id, job_title)
        try:
            return ResumeRepo.create(db, profile_id=profile_id, jd_id=jd_id, job_title=job_title, version=version)
        except IntegrityError:
            db.rollback()
    raise RuntimeError("Could not allocate a resume version")


def _render_and_store(db: Session, user: User, resume, resume_data: dict) -> list[str]:
    """Render each format; a format that fails is left out rather than mislabelled."""
    renderers = {"pdf": render_resume_pdf, "docx": export_to_docx}
    formats = []
    for format, render in renderers.items():
        try:
            data = render(resume_data)
        except Exception:
            logger.exception("%s rendering failed for resume %s", format.upper(), resume.id)
            continue
        store_artifact(db, user.id, resume, format, data)
        formats.append(format)
    return formats


def generate_resume(db: Session, user: User, jd_text: str) -> dict:
    """Run the full resume generation pipeline for the signed-in user."""
    # 1. Get profile
    profile = profile_service.get_profile(db, user)

    # 2. Analyze JD
    logger.info("Step 1: Analyzing job description...")
    jd_data = analyze_jd(jd_text)

    # 3. Store JD analysis
    jd_record = JDAnalysisRepo.create(
        db, user_id=user.id, raw_text=jd_text,
        structured_data=json.dumps(jd_to_dict(jd_data)),
    )

    # 4. Generate JD embedding
    logger.info("Step 2: Generating embeddings...")
    jd_combined = f"{jd_data.role_title} {' '.join(jd_data.must_have_skills)} {' '.join(jd_data.keywords)}"
    jd_embedding = generate_embedding(jd_combined)

    # Store JD embedding
    jd_record.embedding = embedding_to_json(jd_embedding)
    db.commit()

    # 5. Ensure profile has embeddings
    _ensure_embeddings(db, profile)
    db.refresh(profile)

    # 6. Select relevant content
    logger.info("Step 3: Selecting relevant content...")
    draft = select_relevant_content(db, profile, jd_data, jd_embedding)
    draft.jd_id = jd_record.id

    # 7. LLM rewriting
    logger.info("Step 4: Rewriting bullets...")
    draft = rewrite_draft_bullets(draft)

    # 8. ATS optimization
    logger.info("Step 5: ATS optimization...")
    draft = optimize(draft)

    # 9. Assemble resume
    logger.info("Step 6: Assembling resume...")
    resume_data = assemble_resume(draft)

    # 10. Store resume record with its version
    resume = _create_resume_record(db, profile.id, jd_record.id, jd_data.role_title)
    draft.version = resume.version

    # 11. Render to private storage
    formats = _render_and_store(db, user, resume, resume_data)

    # 12. Store resume sections
    for sec in resume_to_sections_json(resume_data):
        ResumeRepo.add_section(
            db, resume.id,
            section_type=sec["section_type"],
            content=sec["content"],
            confidence_flags=sec.get("confidence_flags"),
        )

    return {
        "resume_id": resume.id,
        "job_title": jd_data.role_title,
        "version": resume.version,
        "formats": formats,
        "jd_analysis": jd_to_dict(jd_data),
        "skill_confidence": draft.skill_confidence,
        "keyword_coverage": draft.keyword_coverage,
    }
