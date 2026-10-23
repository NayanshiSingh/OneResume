"""Resume Assembler — builds the final resume structure from approved draft content.

Only included entries and bullets are kept, in draft order, using each
bullet's current text (the user's own wording or their edit).
"""

import json


def _included(items: list[dict]) -> list[dict]:
    return [item for item in items if item.get("included")]


def _entries(items: list[dict]) -> list[dict]:
    return [
        {"title": e["title"], "subtitle": e["subtitle"], "bullets": [b["text"] for b in _included(e["bullets"])]}
        for e in _included(items)
    ]


def assemble_resume(content: dict, job_title: str) -> dict:
    """Convert draft content into the structured dict the PDF and DOCX renderers use."""
    return {
        "job_title": job_title,
        "personal_info": content.get("personal_info") or {},
        "external_profiles": _included(content["external_profiles"]),
        "education": _included(content["education"]),
        "experience": _entries(content["experience"]),
        "projects": _entries(content["projects"]),
        "skills": [s["name"] for s in _included(content["skills"])],
        "certifications": _included(content["certifications"]),
        "achievements": _included(content["achievements"]),
    }


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
            "confidence_flags": None,
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
