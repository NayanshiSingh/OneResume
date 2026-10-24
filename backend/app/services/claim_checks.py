"""Deterministic checks that a suggested rewrite claims nothing new.

A suggestion is blocked when, compared with the original bullet (and its
entry's title and subtitle), it adds a number, a tool or skill, a stronger
verb of ownership, or a seniority word, or grows much longer. Each problem
comes back as a sentence the user can read.
"""

import re

from app.services.evidence_service import contains_term, tokens

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:%|k\b|m\b|x\b|\+)?", re.IGNORECASE)
_OWNERSHIP = {
    "led", "lead", "leading", "owned", "own", "owning", "managed", "manage", "managing",
    "spearheaded", "headed", "directed", "architected", "mentored", "mentoring", "supervised",
    "oversaw", "drove", "championed", "founded",
}
# Tenses of the same verb, so "Lead" becoming "Led" is not a stronger claim. Only verbs whose
# base form is unambiguous are listed: "my own", "hard drive", or "found a bug" must not excuse
# "owned", "drove", or "founded".
_SAME_VERB = {
    "led": "lead", "leading": "lead", "lead": "lead",
    "managed": "manage", "managing": "manage", "manage": "manage",
    "mentored": "mentor", "mentoring": "mentor", "mentor": "mentor",
    "supervised": "supervise", "supervise": "supervise",
    "oversaw": "oversee", "oversee": "oversee",
    "spearheaded": "spearhead", "spearhead": "spearhead",
    "architected": "architect", "architect": "architect",
}
_SENIORITY = {"senior", "principal", "staff", "expert", "expert-level", "chief", "head"}
MAX_GROWTH_CHARS = 120


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[\s,]", "", m.group(0)).lower() for m in _NUMBER.finditer(text)}


def _allowed_numbers(source: str) -> set[str]:
    """Numbers a rewrite may state: those in the source, and N for an "N+" ("30+" may become "over 30")."""
    numbers = _numbers(source)
    return numbers | {n[:-1] for n in numbers if n.endswith("+")}


def check_rewrite(original: str, rewrite: str, context: str, terms: list[str]) -> list[str]:
    """Return reasons to block the rewrite; an empty list means it passed."""
    reasons = []
    source = f"{original} {context}"
    source_tokens, rewrite_tokens = tokens(source), tokens(rewrite)
    source_words, rewrite_words = set(source_tokens), set(rewrite_tokens)

    for number in sorted(_numbers(rewrite) - _allowed_numbers(source)):
        reasons.append(f"Adds a number that is not in your original: {number}")

    added_terms = {t for t in terms if contains_term(rewrite_tokens, t) and not contains_term(source_tokens, t)}
    for term in sorted(added_terms, key=str.lower):
        reasons.append(f"Adds {term}, which your original does not mention")

    source_verbs = {_SAME_VERB.get(w, w) for w in source_words}
    for word in sorted((rewrite_words & _OWNERSHIP) - source_words):
        if _SAME_VERB.get(word, word) not in source_verbs:
            reasons.append(f"Claims more responsibility than your original (\"{word}\")")

    for word in sorted((rewrite_words & _SENIORITY) - source_words):
        reasons.append(f"Adds a seniority or expertise claim (\"{word}\")")

    if len(rewrite) > max(2 * len(original), len(original) + MAX_GROWTH_CHARS):
        reasons.append("Much longer than your original, so it may add detail")
    return reasons
