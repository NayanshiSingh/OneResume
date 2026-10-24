"""Suggested rewrites: claim checks, the two-step check, and accepting in drafts."""

import io
import zipfile

import pytest

from app.config import settings
from app.domain.resume_draft import JDData
from app.services import jd_analyzer, rewrite_service
from app.services.claim_checks import check_rewrite
from tests.conftest import make_draft


# ── Claim checks ─────────────────────────────────────────────

@pytest.mark.parametrize("original,rewrite,context,blocked_by", [
    ("Optimized queries", "Optimized queries, cutting latency by 40%", "", "number"),
    ("Served 10K+ daily users", "Served 10K+ daily active users", "", None),
    ("Cut a report from 9s to 1.2s", "Reduced report time from 9s to 1.2s", "", None),
    ("Deployed services", "Deployed services to Kubernetes", "", "Kubernetes"),
    ("Built a task queue", "Built a Redis-backed task queue", "Python, Redis", None),
    ("Helped the team with the deployment", "Led the team's deployment", "", "responsibility"),
    ("Led migration to microservices", "Led the migration to microservices", "", None),
    ("Built an ML model", "Built an expert-level ML model", "", "seniority"),
    ("Built APIs", "Built APIs " + "with careful attention to detail " * 6, "", "longer"),
    ("worked on the website", "Maintained the company website", "", None),
    # Same verb, different tense (seen with Groq in the evaluation run).
    ("Lead weekly lab sections of 30 students", "Led weekly lab sections for 30 students", "", None),
    ("Mentor two junior engineers", "Mentored two junior engineers", "", None),
    # Base words that are not the verb must not excuse a stronger claim.
    ("Built my own CLI", "Owned the CLI", "", "responsibility"),
    ("Fixed the hard drive backup", "Drove the backup project", "", "responsibility"),
    ("Found and fixed bugs", "Founded the bug-fix effort", "", "responsibility"),
    ("Helped mentor students", "Led mentoring for students", "", "responsibility"),
    # "30+" and "over 30" are the same claim; adding a "+" is not.
    ("Trained 30+ new associates", "Trained over 30 new associates", "", None),
    ("Trained 30 new associates", "Trained 30+ new associates", "", "number"),
])
def test_claim_checks(original, rewrite, context, blocked_by):
    reasons = check_rewrite(original, rewrite, context, ["Kubernetes", "Redis", "Python"])
    if blocked_by is None:
        assert reasons == []
    else:
        assert any(blocked_by.lower() in r.lower() for r in reasons), reasons


def test_java_does_not_count_as_javascript_in_checks():
    assert check_rewrite("Built JavaScript apps", "Built JavaScript applications", "", ["Java"]) == []


# ── Suggestion flow with a fake Gemini ───────────────────────

def content_with(*bullets, included=True):
    return {"experience": [{"id": "e1", "title": "Engineer", "subtitle": "Acme", "included": True, "bullets": [
        {"id": f"b{i}", "text": text, "original_text": text, "included": included, "user_edited": False,
         "ai_accepted": False, "suggestion": None}
        for i, text in enumerate(bullets)
    ]}], "projects": []}


class FakeGemini:
    def __init__(self, rewrites, verdicts=None, fail=()):
        self.rewrites, self.verdicts, self.fail, self.check_pairs = rewrites, verdicts or {}, set(fail), None

    def __call__(self, prompt, schema, purpose, max_wait_seconds=0):
        if purpose in self.fail:
            raise RuntimeError("provider down")
        if purpose == "rewrite":
            return schema(rewrites=[{"id": k, "text": v} for k, v in self.rewrites.items()])
        if purpose == "rewrite_check":
            self.check_pairs = prompt
            ids = [k for k in self.rewrites if f'"id": "{k}"' in prompt]
            return schema(verdicts=[{"id": k, "same_facts": self.verdicts.get(k, (True, ""))[0],
                                     "issue": self.verdicts.get(k, (True, ""))[1]} for k in ids])
        if purpose == "jd_analysis":
            return jd_analyzer._JDExtraction(role_title="Backend Engineer", experience_level="mid",
                                             must_have_skills=["Python", "PostgreSQL"], nice_to_have_skills=["Docker"],
                                             keywords=["Python"], role_category="Software Engineering")
        raise AssertionError(purpose)


@pytest.fixture
def gemini_on(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")


def suggest(monkeypatch, fake, content):
    monkeypatch.setattr(rewrite_service, "generate_json", fake)
    warnings = rewrite_service.add_suggestions(content, JDData(role_title="Backend", must_have_skills=["Kubernetes"]), ["Python"])
    return warnings, {b["id"]: b["suggestion"] for b in content["experience"][0]["bullets"]}


def test_safe_suggestion_passes_both_checks(monkeypatch, gemini_on):
    fake = FakeGemini({"b0": "Developed REST APIs in Python"})
    warnings, result = suggest(monkeypatch, fake, content_with("built rest apis in python"))
    assert warnings == []
    assert result["b0"] == {"text": "Developed REST APIs in Python", "status": "safe", "reasons": []}


def test_checker_sees_the_entry_context(monkeypatch, gemini_on):
    # A project's tech stack is part of the source; the checker must see it like the rules do.
    fake = FakeGemini({"b0": "Developed REST APIs in Python"})
    suggest(monkeypatch, fake, content_with("built rest apis in python"))
    assert '"context": "Engineer Acme"' in fake.check_pairs


def test_rule_blocked_suggestion_is_not_sent_to_checker(monkeypatch, gemini_on):
    fake = FakeGemini({"b0": "Deployed services to Kubernetes", "b1": "Wrote clear docs"})
    _, result = suggest(monkeypatch, fake, content_with("Deployed services", "wrote docs"))
    assert result["b0"]["status"] == "blocked"
    assert "Kubernetes" in result["b0"]["reasons"][0]
    assert '"b0"' not in fake.check_pairs and '"b1"' in fake.check_pairs


def test_checker_can_block_meaning_drift(monkeypatch, gemini_on):
    # The rules cannot see this drift (no new numbers, tools, or ownership verbs); the checker can.
    fake = FakeGemini({"b0": "Approved every production release"}, verdicts={"b0": (False, "adds ownership of releases")})
    _, result = suggest(monkeypatch, fake, content_with("Reviewed pull requests before releases"))
    assert result["b0"]["status"] == "blocked"
    assert result["b0"]["reasons"] == ["Checker: adds ownership of releases"]


def test_checker_failure_blocks_everything_unverified(monkeypatch, gemini_on):
    fake = FakeGemini({"b0": "Developed REST APIs"}, fail={"rewrite_check"})
    _, result = suggest(monkeypatch, fake, content_with("built rest apis"))
    assert result["b0"]["status"] == "blocked"
    assert result["b0"]["reasons"] == [rewrite_service.CHECK_FAILED]


def test_rewrite_failure_keeps_wording_and_warns(monkeypatch, gemini_on):
    warnings, result = suggest(monkeypatch, FakeGemini({}, fail={"rewrite"}), content_with("built apis"))
    assert warnings == [rewrite_service.SUGGESTIONS_FAILED]
    assert result == {"b0": None}


def test_unchanged_rewrite_is_not_a_suggestion(monkeypatch, gemini_on):
    _, result = suggest(monkeypatch, FakeGemini({"b0": "Built APIs"}), content_with("Built APIs"))
    assert result["b0"] is None


def test_hidden_bullets_get_no_suggestion(monkeypatch, gemini_on):
    fake = FakeGemini({"b0": "Developed APIs"})
    _, result = suggest(monkeypatch, fake, content_with("built apis", included=False))
    assert result["b0"] is None


def test_suggestions_off_without_key(monkeypatch):
    warnings, result = suggest(monkeypatch, FakeGemini({"b0": "x"}), content_with("built apis"))
    assert warnings == [rewrite_service.SUGGESTIONS_OFF]
    assert result["b0"] is None


# ── Drafts ───────────────────────────────────────────────────

@pytest.fixture
def draft_with_suggestions(client, db, monkeypatch, gemini_on, sample_jd_text):
    client.post("/api/profile/experience", json={"company": "Acme", "role": "Engineer", "bullets": [
        {"bullet_text": "built rest apis in python"},
        {"bullet_text": "Helped with the deployment"},
    ]})
    fake = FakeGemini({})
    monkeypatch.setattr(jd_analyzer, "generate_json", fake)
    monkeypatch.setattr(rewrite_service, "generate_json", fake)
    bullets = client.get("/api/profile").json()["experience"][0]["bullets"]
    fake.rewrites = {bullets[0]["id"]: "Developed REST APIs in Python", bullets[1]["id"]: "Led the deployment"}
    return make_draft(client, db, sample_jd_text)


def _ops(client, draft, *ops):
    return client.patch(f"/api/drafts/{draft['id']}", json={"revision": draft["revision"], "ops": list(ops)})


def _bullet_op(draft, index, op, **extra):
    entry = draft["content"]["experience"][0]
    return {"op": op, "section": "experience", "item_id": entry["id"], "bullet_id": entry["bullets"][index]["id"], **extra}


def test_draft_keeps_original_wording_until_accepted(draft_with_suggestions):
    bullets = draft_with_suggestions["content"]["experience"][0]["bullets"]
    assert [b["text"] for b in bullets] == ["built rest apis in python", "Helped with the deployment"]
    assert bullets[0]["suggestion"]["status"] == "safe"
    assert bullets[1]["suggestion"]["status"] == "blocked"


def test_accept_safe_suggestion(client, draft_with_suggestions):
    resp = _ops(client, draft_with_suggestions, _bullet_op(draft_with_suggestions, 0, "accept_suggestion"))
    assert resp.status_code == 200
    draft = resp.json()
    bullet = draft["content"]["experience"][0]["bullets"][0]
    assert (bullet["text"], bullet["ai_accepted"], bullet["user_edited"]) == ("Developed REST APIs in Python", True, False)
    assert draft["accepted_suggestions"][0]["original_text"] == "built rest apis in python"
    assert draft["edited_bullets"] == []


def test_blocked_suggestion_cannot_be_accepted(client, draft_with_suggestions):
    assert _ops(client, draft_with_suggestions, _bullet_op(draft_with_suggestions, 1, "accept_suggestion")).status_code == 422


def test_revert_and_edit_clear_acceptance(client, draft_with_suggestions):
    accepted = _ops(client, draft_with_suggestions, _bullet_op(draft_with_suggestions, 0, "accept_suggestion")).json()
    reverted = _ops(client, accepted, _bullet_op(accepted, 0, "revert_bullet")).json()
    assert reverted["accepted_suggestions"] == []
    accepted = _ops(client, reverted, _bullet_op(reverted, 0, "accept_suggestion")).json()
    edited = _ops(client, accepted, _bullet_op(accepted, 0, "edit_bullet", text="Developed REST APIs in Python 3")).json()
    assert edited["accepted_suggestions"] == [] and len(edited["edited_bullets"]) == 1


def test_export_uses_accepted_wording(client, draft_with_suggestions):
    draft = _ops(client, draft_with_suggestions, _bullet_op(draft_with_suggestions, 0, "accept_suggestion")).json()
    client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": draft["revision"]})
    resume = client.post(f"/api/drafts/{draft['id']}/export").json()
    data = client.get(f"/api/resumes/{resume['id']}/download?format=docx").content
    text = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode()
    assert "Developed REST APIs in Python" in text
    assert "Led the deployment" not in text


# ── Rate limits ──────────────────────────────────────────────

from app.services import llm_client


def _rate_limit_error():
    return llm_client.RateLimited(3.0)


def test_background_calls_wait_out_rate_limits(monkeypatch):
    calls, sleeps = [], []
    def flaky(prompt, schema):
        calls.append(1)
        if len(calls) < 3:
            raise _rate_limit_error()
        return schema(rewrites=[]), 10, 5
    monkeypatch.setattr(llm_client, "_generate", flaky)
    monkeypatch.setattr(llm_client.time, "sleep", sleeps.append)
    llm_client.generate_json("p", rewrite_service._Rewrites, "rewrite", max_wait_seconds=60)
    assert len(calls) == 3 and sleeps == [3.0, 3.0]


def test_interactive_calls_fail_fast_on_rate_limits(monkeypatch):
    def limited(prompt, schema):
        raise _rate_limit_error()
    monkeypatch.setattr(llm_client, "_generate", limited)
    with pytest.raises(llm_client.RateLimited):
        llm_client.generate_json("p", rewrite_service._Rewrites, "rewrite")
