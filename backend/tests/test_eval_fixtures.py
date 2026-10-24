"""Consistency checks for the synthetic evaluation set."""

import pytest

from app.schemas import (
    AchievementCreate, CertificationCreate, EducationCreate, ExperienceCreate,
    ExternalProfileCreate, PersonalInfoCreate, ProjectCreate, SkillCreate,
)
from tests.eval_fixtures import (
    LABELS, evidence_ids, labelled_requirements, load_jds, load_personas,
    load_tasks, profile_api_payload,
)

JDS = load_jds()
PERSONAS = load_personas()
TASKS = load_tasks()

SECTION_SCHEMAS = {
    "education": EducationCreate,
    "skills": SkillCreate,
    "experience": ExperienceCreate,
    "projects": ProjectCreate,
    "certifications": CertificationCreate,
    "achievements": AchievementCreate,
    "external_profiles": ExternalProfileCreate,
}


def test_set_sizes():
    assert len(PERSONAS) == 8
    assert len(JDS) == 20
    assert 30 <= len(TASKS) <= 40


@pytest.mark.parametrize("pid", sorted(PERSONAS))
def test_profile_matches_api_schemas(pid):
    payload = profile_api_payload(PERSONAS[pid])
    PersonalInfoCreate(**payload["personal_info"])
    for section, schema in SECTION_SCHEMAS.items():
        for item in payload[section]:
            schema(**item)


@pytest.mark.parametrize("pid", sorted(PERSONAS))
def test_persona_ids_are_unique_and_prefixed(pid):
    profile = PERSONAS[pid]["profile"]
    ids = [
        i for items in profile.values() if isinstance(items, list)
        for item in items
        for i in [item["id"], *(b["id"] for b in item.get("bullets", []))]
    ]
    assert len(ids) == len(set(ids))
    assert all(i.startswith(f"{pid}.") for i in ids)


@pytest.mark.parametrize("jid", sorted(JDS))
def test_jd_requirements_are_well_formed(jid):
    reqs = JDS[jid]["requirements"]
    ids = [r["id"] for r in reqs]
    assert len(ids) == len(set(ids))
    assert all(i.startswith(f"{jid}.R") for i in ids)
    assert all(r["type"] in {"required", "preferred"} for r in reqs)
    assert all(r["kind"] in {"skill", "experience", "education", "eligibility"} for r in reqs)


def test_task_ids_unique_and_every_persona_and_jd_used():
    assert len({t["id"] for t in TASKS}) == len(TASKS)
    assert {t["persona"] for t in TASKS} == set(PERSONAS)
    assert {t["jd"] for t in TASKS} == set(JDS)


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["id"])
def test_task_labels_cover_every_requirement(task):
    expected = {r["id"] for r in labelled_requirements(JDS[task["jd"]])}
    assert set(task["labels"]) == expected


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["id"])
def test_task_labels_and_evidence_are_valid(task):
    known = evidence_ids(PERSONAS[task["persona"]])
    for rid, entry in task["labels"].items():
        assert entry["label"] in LABELS, rid
        accept = entry.get("accept", [])
        assert set(accept) <= LABELS - {entry["label"]}, rid
        assert all(e in known for e in entry["evidence"]), rid
        if entry["label"] == "supported":
            assert any(known[e] != "skills" for e in entry["evidence"]), (
                f"{rid}: supported needs evidence beyond the skills list"
            )


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["id"])
def test_task_selection_ids_are_valid(task):
    known = evidence_ids(PERSONAS[task["persona"]])
    include, omit = set(task["must_include"]), set(task["should_omit"])
    assert include <= set(known)
    assert omit <= set(known)
    assert not include & omit
    assert task["forbidden_claims"]
