"""Orchestrator — end-to-end resume generation pipeline.

Flow:
  JD text → JD Analysis → Embedding → Profile scoring →
  Relevance selection → LLM rewriting → ATS optimization →
  Assembly → Rendering → Storage
"""

import json
import os
import logging
from sqlalchemy.orm import Session

from app.config import settings
from app.repositories import ProfileRepository, JDAnalysisRepo, ResumeRepo
from app.services.jd_analyzer import analyze_jd
from app.services.embedding_service import (
    generate_embedding, generate_embeddings, embedding_to_json, embedding_from_json,
)
from app.services.relevance_selector import select_relevant_content
from app.services.llm_service import rewrite_draft_bullets
from app.services.ats_optimizer import optimize
from app.services.resume_assembler import assemble_resume, resume_to_sections_json
from app.services.latex_renderer import render_resume_to_pdf
from app.services.export_service import export_to_docx

logger = logging.getLogger(__name__)


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
            import numpy as np
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


def generate_resume(
    db: Session,
    profile_id: str,
    jd_text: str,
) -> dict:
    """Run the full resume generation pipeline.

    Returns:
        dict with keys: resume_id, job_title, version, pdf_path, docx_path, resume_data
    """
    # 1. Get profile
    profile = ProfileRepository.get(db, profile_id)

    # 2. Analyze JD
    logger.info("Step 1: Analyzing job description...")
    jd_data = analyze_jd(jd_text)

    # 3. Store JD analysis
    jd_record = JDAnalysisRepo.create(
        db, raw_text=jd_text,
        structured_data=json.dumps({
            "role_title": jd_data.role_title,
            "experience_level": jd_data.experience_level,
            "must_have_skills": jd_data.must_have_skills,
            "nice_to_have_skills": jd_data.nice_to_have_skills,
            "keywords": jd_data.keywords,
            "role_category": jd_data.role_category,
        }),
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

    # 10. Determine version
    version = ResumeRepo.get_next_version(db, profile_id, jd_data.role_title)
    draft.version = version

    # 11. Render to files
    output_dir = settings.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in jd_data.role_title)
    base_name = f"{safe_title}_v{version}".replace(" ", "_")

    pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
    docx_path = os.path.join(output_dir, f"{base_name}.docx")

    # Try PDF (requires pdflatex)
    try:
        render_resume_to_pdf(resume_data, pdf_path)
        logger.info("PDF generated: %s", pdf_path)
    except Exception as e:
        logger.warning("PDF generation failed: %s", e)
        pdf_path = None

    # Always generate DOCX
    try:
        export_to_docx(resume_data, docx_path)
        logger.info("DOCX generated: %s", docx_path)
    except Exception as e:
        logger.warning("DOCX generation failed: %s", e)
        docx_path = None

    # 12. Store resume record
    file_path = pdf_path or docx_path or ""
    resume_record = ResumeRepo.create(
        db, profile_id=profile_id, jd_id=jd_record.id,
        job_title=jd_data.role_title, version=version,
        file_path=file_path,
    )

    # 13. Store resume sections
    for sec in resume_to_sections_json(resume_data):
        ResumeRepo.add_section(
            db, resume_record.id,
            section_type=sec["section_type"],
            content=sec["content"],
            confidence_flags=sec.get("confidence_flags"),
        )

    return {
        "resume_id": resume_record.id,
        "job_title": jd_data.role_title,
        "version": version,
        "pdf_path": pdf_path,
        "docx_path": docx_path,
        "resume_data": resume_data,
        "jd_analysis": {
            "role_title": jd_data.role_title,
            "experience_level": jd_data.experience_level,
            "must_have_skills": jd_data.must_have_skills,
            "nice_to_have_skills": jd_data.nice_to_have_skills,
            "keywords": jd_data.keywords,
            "role_category": jd_data.role_category,
        },
        "skill_confidence": draft.skill_confidence,
        "keyword_coverage": draft.keyword_coverage,
    }
