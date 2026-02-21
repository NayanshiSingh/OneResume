"""JD Analyzer — parses raw job description text into structured data.

Uses Google Gemini for intelligent extraction, with a rule-based
fallback if the API key is not set.
"""

import json
import re
import logging

from app.config import settings
from app.domain.resume_draft import JDData

logger = logging.getLogger(__name__)


def _clean_json_response(text: str) -> str:
    """Strip markdown code fences that Gemini sometimes wraps around JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def analyze_jd_with_gemini(raw_text: str) -> JDData:
    """Use Gemini to extract structured data from a raw JD."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    prompt = f"""Analyze the following job description and extract structured information.
Return ONLY valid JSON with these exact keys:
{{
  "role_title": "string",
  "experience_level": "string (e.g. entry, mid, senior)",
  "must_have_skills": ["list of required skills"],
  "nice_to_have_skills": ["list of preferred/optional skills"],
  "keywords": ["important keywords for ATS matching"],
  "role_category": "string (e.g. Software Engineering, Data Science, Product Management)"
}}

Job Description:
{raw_text}

Return ONLY the JSON object, no explanations."""

    response = model.generate_content(prompt)
    cleaned = _clean_json_response(response.text)
    data = json.loads(cleaned)

    return JDData(
        role_title=data.get("role_title", ""),
        experience_level=data.get("experience_level", ""),
        must_have_skills=data.get("must_have_skills", []),
        nice_to_have_skills=data.get("nice_to_have_skills", []),
        keywords=data.get("keywords", []),
        role_category=data.get("role_category", ""),
    )


def analyze_jd_rules(raw_text: str) -> JDData:
    """Simple rule-based JD analysis (fallback when Gemini is unavailable)."""
    text_lower = raw_text.lower()

    # Extract keywords by finding capitalized phrases and tech terms
    words = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", raw_text)
    tech_patterns = re.findall(
        r"\b(?:Python|Java|JavaScript|TypeScript|React|Angular|Node\.?js|SQL|"
        r"PostgreSQL|MongoDB|AWS|GCP|Azure|Docker|Kubernetes|Git|REST|GraphQL|"
        r"FastAPI|Django|Flask|Spring|TensorFlow|PyTorch|Scikit|Pandas|"
        r"Machine Learning|Deep Learning|NLP|CI/CD|Agile|Scrum)\b",
        raw_text, re.IGNORECASE,
    )

    keywords = list(set(w.strip() for w in tech_patterns if len(w) > 1))

    # Guess experience level
    experience_level = "mid"
    if any(w in text_lower for w in ["senior", "lead", "principal", "staff"]):
        experience_level = "senior"
    elif any(w in text_lower for w in ["junior", "entry", "intern", "graduate", "fresher"]):
        experience_level = "entry"

    # Extract role title from first line
    lines = [l.strip() for l in raw_text.strip().split("\n") if l.strip()]
    role_title = lines[0] if lines else "Unknown Role"

    return JDData(
        role_title=role_title[:100],
        experience_level=experience_level,
        must_have_skills=keywords[:10],
        nice_to_have_skills=[],
        keywords=keywords,
        role_category="General",
    )


def analyze_jd(raw_text: str) -> JDData:
    """Analyze a job description — uses Gemini if available, else rules."""
    if settings.GEMINI_API_KEY:
        try:
            return analyze_jd_with_gemini(raw_text)
        except Exception as e:
            logger.warning("Gemini JD analysis failed, falling back to rules: %s", e)
    return analyze_jd_rules(raw_text)
