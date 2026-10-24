"""Run the synthetic evaluation set against the real pipeline.

    cd backend
    python -m evaluation.run_eval --max-cost 1.50
    python -m evaluation.run_eval --rpm 4           # stay under the Gemini free tier (5 per minute)
    python -m evaluation.run_eval --offline        # no API calls (fakes), for checking the harness

Uses a throwaway in-memory database and storage directory, never the app
database. Live runs call Gemini (JD analysis, rewrite, rewrite check) and
Pinecone (embeddings) using the keys in backend/.env, and stop early if the
Gemini cost passes --max-cost.

Writes results/<timestamp>.json and results/<timestamp>-calibration.md.
"""

import argparse
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers every model on Base.metadata
from app.config import settings
from app.database import Base
from app.models.draft import Draft
from app.models.profile import (
    Achievement, Certification, Education, Experience, ExternalProfile, Project, Skill,
)
from app.repositories import JDAnalysisRepo
from app.services import auth_service, draft_service, llm_client, profile_service
from app.services.jd_analyzer import analyze_jd, jd_to_dict
from app.domain.resume_draft import JDData
from evaluation import scoring
from tests.eval_fixtures import load_jds, load_personas, load_tasks

RESULTS_DIR = Path(__file__).parent / "results"
CALIBRATION_TASKS = ["T01", "T03", "T06", "T08", "T12", "T15", "T23", "T28", "T31", "T33"]
SECTIONS = [
    ("education", Education), ("skills", Skill), ("experience", Experience), ("projects", Project),
    ("certifications", Certification), ("achievements", Achievement), ("external_profiles", ExternalProfile),
]

logger = logging.getLogger("evaluation")


class BudgetExceeded(Exception):
    pass


def check_budget(max_cost: float) -> None:
    spent = llm_client.usage_log.total.cost_usd
    if spent > max_cost:
        raise BudgetExceeded(f"Gemini spend ${spent:.3f} passed the ${max_cost:.2f} cap")


def load_persona(db, persona: dict):
    """Create a user and profile for a persona; return the user and a persona-ID → database-ID map."""
    user = auth_service.register(db, f"{persona['id'].lower()}@eval.example.com", "evaluation-password")
    data = persona["profile"]
    ids = {}
    if data.get("personal_info"):
        profile_service.upsert_personal_info(db, user, data["personal_info"])
    for key, model in SECTIONS:
        for item in data.get(key, []):
            fields = {k: v for k, v in item.items() if k not in {"id", "bullets"}}
            bullets = item.get("bullets", [])
            created = profile_service.create_item(db, user, model, fields, [b["bullet_text"] for b in bullets])
            ids[item["id"]] = created.id
            for source, stored in zip(bullets, getattr(created, "bullets", [])):
                ids[source["id"]] = stored.id
    return user, ids


def evaluate_extraction(jds: dict, max_cost: float) -> list[dict]:
    results = []
    for jd in jds.values():
        check_budget(max_cost)
        analysis = analyze_jd(jd["text"])
        extracted = analysis.data.must_have_skills + analysis.data.nice_to_have_skills
        recall = scoring.extraction_recall(jd, extracted)
        results.append({"jd": jd["id"], "mode": analysis.mode, "warnings": analysis.warnings,
                        "extracted": extracted, **recall})
        logger.info("%s extraction: %d/%d found (%s)", jd["id"], recall["found"], recall["checked"], analysis.mode)
    return results


def evaluate_task(db, task: dict, jd: dict, user, ids: dict) -> dict:
    required, preferred, requirement_ids = scoring.reviewed_requirements(jd)
    reviewed = JDData(role_title=jd["title"], must_have_skills=required, nice_to_have_skills=preferred,
                      keywords=required + preferred)
    record = JDAnalysisRepo.create(db, user_id=user.id, raw_text=jd["text"],
                                   structured_data=json.dumps(jd_to_dict(reviewed)),
                                   analysis_mode="reviewed", warnings="[]")
    record.reviewed_at = auth_service.utcnow()
    db.commit()

    draft: Draft = draft_service.build_draft(db, user, record.id, 1)
    view = draft_service.view(draft)
    content = view["content"]
    reverse = {v: k for k, v in ids.items()}
    return {
        "task": task["id"], "persona": task["persona"], "jd": task["jd"], "purpose": task["purpose"],
        "matching_mode": draft.matching_mode, "warnings": view["warnings"],
        "labels": scoring.label_agreement(task, view["coverage"], requirement_ids),
        "selection": scoring.selection(task, content, ids),
        "suggestions": scoring.suggestion_counts(content),
        "violations": scoring.suggestion_violations(task, content),
        "bullets": [
            {"id": reverse.get(b["id"], b["id"]), "entry": e["title"], "included": e["included"] and b["included"],
             "original": b["original_text"], "suggestion": b.get("suggestion")}
            for section in ["experience", "projects"] for e in content[section] for b in e["bullets"]
        ],
        "coverage": [{"requirement": requirement_ids.get(c["requirement"], c["requirement"]), "text": c["requirement"],
                      "label": c["label"], "in_draft": c["in_draft"]} for c in view["coverage"]],
    }


def summarise(extraction: list[dict], tasks: list[dict]) -> dict:
    labels_checked = sum(t["labels"]["checked"] for t in tasks)
    labels_agreed = sum(t["labels"]["agreed"] for t in tasks)
    must = sum(t["selection"]["must_include"] for t in tasks)
    missing = sum(len(t["selection"]["missing"]) for t in tasks)
    omit = sum(t["selection"]["should_omit"] for t in tasks)
    unwanted = sum(len(t["selection"]["unwanted"]) for t in tasks)
    safe = sum(t["suggestions"]["safe"] for t in tasks)
    blocked = sum(t["suggestions"]["blocked"] for t in tasks)
    reasons: dict[str, int] = {}
    for t in tasks:
        for k, v in t["suggestions"]["blocked_reasons"].items():
            reasons[k] = reasons.get(k, 0) + v
    usage = llm_client.usage_log
    return {
        "tasks_run": len(tasks),
        "extraction_recall": f"{sum(e['found'] for e in extraction)}/{sum(e['checked'] for e in extraction)}",
        "label_agreement": f"{labels_agreed}/{labels_checked}",
        "label_agreement_pct": round(100 * labels_agreed / labels_checked, 1) if labels_checked else None,
        "must_include_found": f"{must - missing}/{must}",
        "should_omit_respected": f"{omit - unwanted}/{omit}",
        "suggestions_safe": safe,
        "suggestions_blocked": blocked,
        "blocked_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
        "factuality_violations": sum(len(t["violations"]) for t in tasks),
        "matching_modes": sorted({t["matching_mode"] for t in tasks}),
        "gemini": {purpose: {"calls": u.calls, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                             "cost_usd": round(u.cost_usd, 4)}
                   for purpose, u in usage.by_purpose.items()},
        "gemini_cost_usd": round(usage.total.cost_usd, 4),
    }


def calibration_markdown(tasks: list[dict], jds: dict) -> str:
    lines = ["# Calibration sheet", "",
             "Score each draft with the rubric in docs/evaluation/rubric.md. Bullets show the original wording,",
             "the suggestion, and whether it was offered (safe) or blocked.", ""]
    for t in (t for t in tasks if t["task"] in CALIBRATION_TASKS):
        lines += [f"## {t['task']} · {t['persona']} → {jds[t['jd']]['title']}", "", f"_{t['purpose']}_", "",
                  "**Requirements**", ""]
        lines += [f"- {c['text']}: {c['label']}{' (in draft)' if c['in_draft'] else ''}" for c in t["coverage"]]
        lines += ["", "**Included bullets**", ""]
        for b in (b for b in t["bullets"] if b["included"]):
            s = b["suggestion"]
            lines.append(f"- {b['original']}")
            if s:
                status = "offered" if s["status"] == "safe" else "blocked: " + "; ".join(s["reasons"])
                lines.append(f"  - suggestion ({status}): {s['text']}")
        lines += ["", "| Factuality | Coverage | Selection | Wording | Notes |", "|---|---|---|---|---|", "| | | | | |", ""]
    return "\n".join(lines)


def install_offline_fakes() -> None:
    """Replace providers with deterministic fakes so the harness runs without keys."""
    from app.services import embedding_service, jd_analyzer, rewrite_service
    from tests.conftest import fake_embed_batch

    settings.GEMINI_API_KEY = settings.PINECONE_API_KEY = "offline"
    embedding_service._embed_batch = fake_embed_batch

    def fake_json(prompt, schema, purpose, max_wait_seconds=0):
        llm_client.usage_log.record(purpose, len(prompt) // 4, 50)
        if purpose == "jd_analysis":
            data = jd_analyzer.analyze_jd_rules(prompt.split("Job description:", 1)[-1])
            return schema(**jd_to_dict(data))
        if purpose == "rewrite":
            items = json.loads(prompt.split("belongs to):\n", 1)[1].split("\n\nReturn", 1)[0])
            return schema(rewrites=[{"id": i["id"], "text": i["text"][:1].upper() + i["text"][1:]} for i in items])
        pairs = json.loads(prompt.split("Pairs (JSON):\n", 1)[1].split("\n\nReturn", 1)[0])
        return schema(verdicts=[{"id": p["id"], "same_facts": True, "issue": ""} for p in pairs])

    jd_analyzer.generate_json = fake_json
    rewrite_service.generate_json = fake_json


def run(max_cost: float, offline: bool, only: list[str] | None = None, rpm: float = 0) -> dict:
    if rpm:
        llm_client.min_interval_seconds = 60 / rpm
    if offline:
        install_offline_fakes()
    elif not (settings.GEMINI_API_KEY and settings.PINECONE_API_KEY):
        raise SystemExit("Live runs need GEMINI_API_KEY and PINECONE_API_KEY in backend/.env (or use --offline)")

    settings.STORAGE_DIR = tempfile.mkdtemp(prefix="oneresume-eval-")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    jds, personas = load_jds(), load_personas()
    tasks = [t for t in load_tasks() if not only or t["id"] in only]
    loaded = {pid: load_persona(db, p) for pid, p in personas.items()}

    extraction, results, stopped = [], [], None
    try:
        extraction = evaluate_extraction({k: v for k, v in jds.items() if not only or k in {t["jd"] for t in tasks}}, max_cost)
        for task in tasks:
            check_budget(max_cost)
            user, ids = loaded[task["persona"]]
            results.append(evaluate_task(db, task, jds[task["jd"]], user, ids))
            r = results[-1]
            logger.info("%s: labels %d/%d, suggestions %d safe / %d blocked, violations %d",
                        task["id"], r["labels"]["agreed"], r["labels"]["checked"],
                        r["suggestions"]["safe"], r["suggestions"]["blocked"], len(r["violations"]))
    except BudgetExceeded as exc:
        stopped = str(exc)
        logger.warning(stopped)

    report = {"run_at": datetime.now().isoformat(timespec="seconds"), "offline": offline, "stopped_early": stopped,
              "summary": summarise(extraction, results), "extraction": extraction, "tasks": results}
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S") + ("-offline" if offline else "")
    (RESULTS_DIR / f"{stamp}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (RESULTS_DIR / f"{stamp}-calibration.md").write_text(calibration_markdown(results, jds))
    report["files"] = [str(RESULTS_DIR / f"{stamp}.json"), str(RESULTS_DIR / f"{stamp}-calibration.md")]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-cost", type=float, default=1.50, help="stop when Gemini spend passes this (USD)")
    parser.add_argument("--offline", action="store_true", help="use fakes instead of Gemini and Pinecone")
    parser.add_argument("--only", nargs="*", help="task IDs to run, e.g. T01 T08")
    parser.add_argument("--rpm", type=float, default=0, help="max Gemini requests per minute (free tier: 5)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for noisy in ("httpx", "app.services.llm_client", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    report = run(args.max_cost, args.offline, args.only, args.rpm)
    print(json.dumps(report["summary"], indent=2))
    print("\n".join(report["files"]))


if __name__ == "__main__":
    main()
