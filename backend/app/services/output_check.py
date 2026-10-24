"""Checks that an exported file really contains the approved resume.

Text is extracted back out of each PDF or DOCX (as an applicant tracking
system would) and compared with the assembled resume: every heading, entry
title, and bullet must be present, and bullets must come out in order. A
format that fails is not offered for download.
"""

import io
import re
import unicodedata
from dataclasses import dataclass, field

from docx import Document
from pypdf import PdfReader


@dataclass
class CheckResult:
    ok: bool
    pages: int | None = None
    missing: list[str] = field(default_factory=list)
    out_of_order: bool = False


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)  # splits ligatures such as "ﬁ"
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def expected_text(resume_data: dict) -> list[str]:
    """Snippets that must appear, in reading order."""
    snippets = []
    if name := (resume_data.get("personal_info") or {}).get("full_name"):
        snippets.append(name)
    for section, heading in [("education", "Education"), ("experience", "Experience"), ("projects", "Projects"),
                             ("skills", "Skills"), ("certifications", "Certifications"), ("achievements", "Achievements")]:
        items = resume_data.get(section) or []
        if not items:
            continue
        snippets.append(heading)
        if section in ("experience", "projects"):
            for entry in items:
                snippets.append(entry["title"])
                snippets.extend(entry["bullets"])
        elif section == "skills":
            snippets.extend(items)
        elif section == "education":
            snippets.extend(e["institution"] for e in items)
        else:
            snippets.extend(i.get("name") or i.get("title") for i in items)
    return [s for s in snippets if s]


def extract_pdf(data: bytes) -> tuple[str, int]:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages), len(reader.pages)


def extract_docx(data: bytes) -> str:
    return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)


def verify(format: str, data: bytes, resume_data: dict) -> CheckResult:
    if format == "pdf":
        text, pages = extract_pdf(data)
    else:
        text, pages = extract_docx(data), None
    haystack = _normalise(text)
    position, missing, out_of_order = 0, [], False
    for snippet in expected_text(resume_data):
        needle = _normalise(snippet)
        found = haystack.find(needle, position)
        if found == -1:
            if needle in haystack:
                out_of_order = True
            else:
                missing.append(snippet)
            continue
        position = found + len(needle)
    return CheckResult(ok=not missing and not out_of_order, pages=pages, missing=missing, out_of_order=out_of_order)
