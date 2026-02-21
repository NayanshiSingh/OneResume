"""Resume Assembler — builds the final resume structure from a ResumeDraft.

Combines scored sections, rewritten bullets, and ATS optimizations
into a structured output ready for rendering.
"""

import json
from app.domain.resume_draft import ResumeDraft


def assemble_resume(draft: ResumeDraft) -> dict:
    """Convert a finalized ResumeDraft into a structured resume dict.

    This dict is what gets passed to the LaTeX renderer.
    """
    resume = {
        "job_title": draft.job_title,
        "personal_info": draft.personal_info or {},
        "external_profiles": draft.external_profiles,
        "education": draft.education,
        "experience": [],
        "projects": [],
        "skills": draft.selected_skills,
        "certifications": draft.certifications,
        "achievements": draft.achievements,
        "skill_confidence": draft.skill_confidence,
        "keyword_coverage": draft.keyword_coverage,
    }

    # Experience sections
    for section in draft.experience_sections:
        entry = {
            "title": section.title,
            "subtitle": section.subtitle,
            "bullets": [
                b.rewritten_text or b.text for b in section.bullets
            ],
        }
        resume["experience"].append(entry)

    # Project sections
    for section in draft.project_sections:
        entry = {
            "title": section.title,
            "subtitle": section.subtitle,
            "bullets": [
                b.rewritten_text or b.text for b in section.bullets
            ],
        }
        resume["projects"].append(entry)

    return resume


def resume_to_sections_json(resume: dict) -> list[dict]:
    """Convert assembled resume into per-section JSON for DB storage."""
    sections = []

    if resume.get("personal_info"):
        sections.append({
            "section_type": "personal_info",
            "content": json.dumps(resume["personal_info"]),
            "confidence_flags": None,
        })

    if resume.get("education"):
        sections.append({
            "section_type": "education",
            "content": json.dumps(resume["education"]),
            "confidence_flags": None,
        })

    if resume.get("experience"):
        sections.append({
            "section_type": "experience",
            "content": json.dumps(resume["experience"]),
            "confidence_flags": None,
        })

    if resume.get("projects"):
        sections.append({
            "section_type": "projects",
            "content": json.dumps(resume["projects"]),
            "confidence_flags": None,
        })

    if resume.get("skills"):
        sections.append({
            "section_type": "skills",
            "content": json.dumps(resume["skills"]),
            "confidence_flags": json.dumps(resume.get("skill_confidence", {})),
        })

    if resume.get("certifications"):
        sections.append({
            "section_type": "certifications",
            "content": json.dumps(resume["certifications"]),
            "confidence_flags": None,
        })

    if resume.get("achievements"):
        sections.append({
            "section_type": "achievements",
            "content": json.dumps(resume["achievements"]),
            "confidence_flags": None,
        })

    return sections
