"""Evaluation scoring functions."""

from evaluation import scoring

JD = {"requirements": [
    {"id": "R1", "type": "required", "kind": "skill", "any_of": ["Python", "Java"]},
    {"id": "R2", "type": "preferred", "kind": "skill", "any_of": ["Docker"]},
    {"id": "R3", "type": "required", "kind": "experience"},
    {"id": "R4", "type": "preferred", "kind": "experience", "any_of": ["HIPAA", "healthcare"]},
]}

CONTENT = {
    "education": [], "certifications": [], "achievements": [], "external_profiles": [],
    "skills": [{"id": "s1", "included": True}],
    "experience": [{"id": "e1", "included": True, "bullets": [
        {"id": "b1", "included": True, "original_text": "Built APIs",
         "suggestion": {"text": "Built APIs on Kubernetes", "status": "safe", "reasons": []}},
        {"id": "b2", "included": False, "original_text": "Fixed bugs", "suggestion": None},
        {"id": "b3", "included": True, "original_text": "Helped deploy",
         "suggestion": {"text": "Led deployment", "status": "blocked",
                        "reasons": ["Claims more responsibility than your original (\"led\")"]}},
    ]}],
    "projects": [],
}


def test_reviewed_requirements_include_anything_with_search_words():
    required, preferred, ids = scoring.reviewed_requirements(JD)
    assert (required, preferred) == (["Python or Java"], ["Docker", "HIPAA or healthcare"])
    assert ids == {"Python or Java": "R1", "Docker": "R2", "HIPAA or healthcare": "R4"}


def test_label_agreement_counts_accepted_alternatives():
    task = {"labels": {"R1": {"label": "supported"}, "R2": {"label": "not_found", "accept": ["needs_confirmation"]}}}
    coverage = [{"requirement": "Python or Java", "label": "supported"}, {"requirement": "Docker", "label": "needs_confirmation"}]
    result = scoring.label_agreement(task, coverage, {"Python or Java": "R1", "Docker": "R2"})
    assert (result["checked"], result["agreed"]) == (2, 2)


def test_selection_reports_missing_and_unwanted():
    task = {"must_include": ["P.b1", "P.b2"], "should_omit": ["P.b3"]}
    result = scoring.selection(task, CONTENT, {"P.b1": "b1", "P.b2": "b2", "P.b3": "b3"})
    assert result["missing"] == ["P.b2"] and result["unwanted"] == ["P.b3"]


def test_violation_when_safe_suggestion_adds_forbidden_term():
    violations = scoring.suggestion_violations({"forbidden_claims": ["Kubernetes", "led a team"]}, CONTENT)
    assert [v["terms"] for v in violations] == [["Kubernetes"]]


def test_suggestion_counts_and_reason_kinds():
    counts = scoring.suggestion_counts(CONTENT)
    assert (counts["safe"], counts["blocked"]) == (1, 1)
    assert counts["blocked_reasons"] == {"stronger verb": 1}
    assert scoring.reason_kind("Adds Kafka, which your original does not mention") == "new tool or skill"
    assert scoring.reason_kind("Adds a number that is not in your original: 40%") == "new number"


def test_extraction_recall_accepts_any_alternative():
    result = scoring.extraction_recall(JD, ["Java", "Kubernetes"])
    assert (result["checked"], result["found"], result["missed"]) == (2, 1, ["R2"])
