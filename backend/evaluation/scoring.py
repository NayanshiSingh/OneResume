"""Scoring a built draft against a task's answer key. Pure functions, no I/O."""

import re

from app.services.evidence_service import contains_term, tokens
from app.services.jd_analyzer import TECH_TERMS

# Words in a forbidden claim that signal an ownership or seniority claim.
_CLAIM_WORDS = re.compile(r"\b(?:led|lead|managed|mentored|owned|senior|expert|principal|staff)\b", re.IGNORECASE)
_YEARS = re.compile(r"\b\d+\+?\s+years?\b", re.IGNORECASE)


def reviewed_requirements(jd: dict) -> tuple[list[str], list[str], dict[str, str]]:
    """Answer-key skill requirements as the user would type them after review.

    Returns (required, preferred, requirement text → requirement id). Requirements
    without concrete terms (experience, education) are not matched by evidence
    terms and are reported separately.
    """
    required, preferred, ids = [], [], {}
    for req in jd["requirements"]:
        if req["kind"] != "skill" or not req.get("any_of"):
            continue
        text = " or ".join(req["any_of"])
        (required if req["type"] == "required" else preferred).append(text)
        ids[text] = req["id"]
    return required, preferred, ids


def label_agreement(task: dict, coverage: list[dict], requirement_ids: dict[str, str]) -> dict:
    """Compare matcher labels with the task's expected label (or an accepted alternative)."""
    results = []
    for item in coverage:
        req_id = requirement_ids.get(item["requirement"])
        expected = task["labels"].get(req_id)
        if expected is None:
            continue
        ok = item["label"] == expected["label"] or item["label"] in expected.get("accept", [])
        results.append({"requirement": req_id, "got": item["label"], "expected": expected["label"], "ok": ok})
    return {"checked": len(results), "agreed": sum(r["ok"] for r in results),
            "disagreements": [r for r in results if not r["ok"]]}


def included_ids(content: dict) -> set[str]:
    ids = set()
    for section in ["education", "certifications", "achievements", "skills", "external_profiles"]:
        ids |= {i["id"] for i in content[section] if i["included"]}
    for section in ["experience", "projects"]:
        for entry in content[section]:
            if entry["included"]:
                ids.add(entry["id"])
                ids |= {b["id"] for b in entry["bullets"] if b["included"]}
    return ids


def selection(task: dict, content: dict, db_ids: dict[str, str]) -> dict:
    included = included_ids(content)
    missing = [pid for pid in task["must_include"] if db_ids[pid] not in included]
    unwanted = [pid for pid in task["should_omit"] if db_ids[pid] in included]
    return {"must_include": len(task["must_include"]), "missing": missing,
            "should_omit": len(task["should_omit"]), "unwanted": unwanted}


def claim_terms(claim: str) -> list[str]:
    """Concrete terms a forbidden claim would introduce (tools, years, ownership words)."""
    return list(dict.fromkeys(TECH_TERMS.findall(claim) + _YEARS.findall(claim) + _CLAIM_WORDS.findall(claim)))


def suggestion_violations(task: dict, content: dict) -> list[dict]:
    """Safe suggestions that introduce a forbidden claim's terms absent from the original bullet."""
    violations = []
    for section in ["experience", "projects"]:
        for entry in content[section]:
            for bullet in entry["bullets"]:
                suggestion = bullet.get("suggestion")
                if not suggestion or suggestion["status"] != "safe":
                    continue
                new, old = tokens(suggestion["text"]), tokens(bullet["original_text"])
                for claim in task["forbidden_claims"]:
                    added = [t for t in claim_terms(claim) if contains_term(new, t) and not contains_term(old, t)]
                    if added:
                        violations.append({"bullet": bullet["id"], "claim": claim, "terms": added,
                                           "original": bullet["original_text"], "suggestion": suggestion["text"]})
    return violations


_REASON_KINDS = [
    ("Adds a number", "new number"),
    ("Adds a seniority", "seniority"),
    ("Claims more responsibility", "stronger verb"),
    ("Much longer", "too long"),
    ("Checker:", "checker: meaning changed"),
    ("Could not double-check", "checker unavailable"),
    ("Adds ", "new tool or skill"),
]


def reason_kind(reason: str) -> str:
    return next((kind for prefix, kind in _REASON_KINDS if reason.startswith(prefix)), "other")


def suggestion_counts(content: dict) -> dict:
    counts = {"safe": 0, "blocked": 0, "none": 0, "blocked_reasons": {}}
    for section in ["experience", "projects"]:
        for entry in content[section]:
            for bullet in entry["bullets"]:
                if not (entry["included"] and bullet["included"]):
                    continue
                suggestion = bullet.get("suggestion")
                if suggestion is None:
                    counts["none"] += 1
                    continue
                counts[suggestion["status"]] += 1
                for kind in {reason_kind(r) for r in suggestion["reasons"]}:
                    counts["blocked_reasons"][kind] = counts["blocked_reasons"].get(kind, 0) + 1
    return counts


def extraction_recall(jd: dict, extracted: list[str]) -> dict:
    """How many answer-key skill requirements the analysis found (any alternative counts)."""
    found_tokens = [tokens(e) for e in extracted]
    results = []
    for req in jd["requirements"]:
        if req["kind"] != "skill" or not req.get("any_of"):
            continue
        hit = any(contains_term(ft, term) for ft in found_tokens for term in req["any_of"])
        results.append({"requirement": req["id"], "found": hit})
    return {"checked": len(results), "found": sum(r["found"] for r in results),
            "missed": [r["requirement"] for r in results if not r["found"]]}
