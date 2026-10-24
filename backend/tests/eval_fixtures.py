"""Loaders for the synthetic evaluation set in tests/fixtures/eval."""

import json
from pathlib import Path

EVAL_DIR = Path(__file__).parent / "fixtures" / "eval"
LABELS = {"supported", "needs_confirmation", "not_found"}


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jds() -> dict[str, dict]:
    return {jd["id"]: jd for jd in _read(EVAL_DIR / "jds.json")["jds"]}


def load_personas() -> dict[str, dict]:
    docs = (_read(p) for p in sorted((EVAL_DIR / "personas").glob("P*.json")))
    return {doc["id"]: doc for doc in docs}


def load_tasks() -> list[dict]:
    return _read(EVAL_DIR / "tasks.json")["tasks"]


def labelled_requirements(jd: dict) -> list[dict]:
    """Requirements that tasks must label; eligibility is never labelled."""
    return [r for r in jd["requirements"] if r["kind"] != "eligibility"]


def evidence_ids(persona: dict) -> dict[str, str]:
    """Map every evidence ID in a persona profile to its section name."""
    ids = {}
    for section, items in persona["profile"].items():
        if not isinstance(items, list):
            continue
        for item in items:
            ids[item["id"]] = section
            for bullet in item.get("bullets", []):
                ids[bullet["id"]] = section
    return ids


def _strip_ids(value):
    if isinstance(value, list):
        return [_strip_ids(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip_ids(v) for k, v in value.items() if k != "id"}
    return value


def profile_api_payload(persona: dict) -> dict:
    """Profile in the shape the profile API accepts, without evaluation IDs."""
    return _strip_ids(persona["profile"])
