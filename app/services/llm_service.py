"""LLM Service — Gemini-based bullet rewriting.

The LLM acts as a REWRITER, not a decision-maker.
Constraints:
  - No fabrication of skills
  - No structural changes
  - Output must follow a predefined schema
"""

import json
import re
import logging

from app.config import settings
from app.domain.resume_draft import ResumeDraft, ScoredBullet

logger = logging.getLogger(__name__)


def _clean_json_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def rewrite_bullets_with_gemini(
    bullets: list[ScoredBullet],
    job_title: str,
    keywords: list[str],
) -> list[ScoredBullet]:
    """Rewrite bullet points using Gemini for ATS optimization."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    bullet_texts = [b.text for b in bullets]

    prompt = f"""You are a professional resume writer. Rewrite the following resume bullet points
to be more impactful, concise, and ATS-friendly for a "{job_title}" role.

RULES:
1. DO NOT invent or fabricate any skills, tools, or experiences
2. DO NOT add information not present in the original
3. Use strong action verbs
4. Include quantifiable results where they exist in the original
5. Naturally incorporate these keywords where relevant: {', '.join(keywords[:10])}
6. Keep each bullet to 1-2 lines max

Original bullets:
{json.dumps(bullet_texts)}

Return ONLY a JSON array of rewritten strings, same length as input.
Example: ["Rewritten bullet 1", "Rewritten bullet 2"]"""

    response = model.generate_content(prompt)
    cleaned = _clean_json_response(response.text)
    rewritten = json.loads(cleaned)

    if len(rewritten) != len(bullets):
        logger.warning("LLM returned %d bullets, expected %d. Using originals.",
                      len(rewritten), len(bullets))
        return bullets

    for i, bullet in enumerate(bullets):
        bullet.rewritten_text = rewritten[i]

    return bullets


def rewrite_bullets_simple(
    bullets: list[ScoredBullet],
    job_title: str,
    keywords: list[str],
) -> list[ScoredBullet]:
    """Simple rule-based rewriting (fallback when Gemini is unavailable)."""
    action_verbs = [
        "Developed", "Implemented", "Designed", "Engineered", "Built",
        "Optimized", "Led", "Managed", "Created", "Deployed",
    ]

    for i, bullet in enumerate(bullets):
        text = bullet.text.strip()
        # Ensure starts with action verb
        first_word = text.split()[0] if text.split() else ""
        if not first_word[0].isupper() or first_word.endswith("ing"):
            verb = action_verbs[i % len(action_verbs)]
            text = f"{verb} {text[0].lower()}{text[1:]}" if text else text
        # Remove trailing period inconsistency
        text = text.rstrip(".")
        bullet.rewritten_text = text

    return bullets


def rewrite_draft_bullets(draft: ResumeDraft) -> ResumeDraft:
    """Rewrite all bullets in the draft using the best available method."""
    keywords = draft.jd_data.keywords if draft.jd_data else []
    job_title = draft.job_title

    all_bullets = []
    for section in draft.experience_sections + draft.project_sections:
        all_bullets.extend(section.bullets)

    if not all_bullets:
        return draft

    if settings.GEMINI_API_KEY:
        try:
            rewrite_bullets_with_gemini(all_bullets, job_title, keywords)
        except Exception as e:
            logger.warning("Gemini rewriting failed, using fallback: %s", e)
            rewrite_bullets_simple(all_bullets, job_title, keywords)
    else:
        rewrite_bullets_simple(all_bullets, job_title, keywords)

    # Ensure all bullets have rewritten text
    for bullet in all_bullets:
        if not bullet.rewritten_text:
            bullet.rewritten_text = bullet.text

    return draft
