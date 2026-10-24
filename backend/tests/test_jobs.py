"""Background jobs: idempotency, failure and retry, stale reclaim."""

from datetime import timedelta

from app.models.draft import GenerationJob
from app.services import draft_service, job_service
from app.services.auth_service import utcnow


def _jd(client, text):
    return client.post("/api/jd/analyze", json={"raw_text": text}).json()["id"]


def _request(client, jd_id, key="k1"):
    return client.post("/api/drafts", json={"jd_id": jd_id, "idempotency_key": key})


def test_job_starts_queued_and_worker_completes_it(client, db, sample_jd_text):
    job = _request(client, _jd(client, sample_jd_text)).json()
    assert job["status"] == "queued" and job["result_id"] is None
    assert job_service.process_next(db) is True
    done = client.get(f"/api/jobs/{job['id']}").json()
    assert done["status"] == "succeeded"
    assert client.get(f"/api/drafts/{done['result_id']}").status_code == 200
    assert job_service.process_next(db) is False


def test_same_idempotency_key_returns_the_same_job(client, db, sample_jd_text):
    jd_id = _jd(client, sample_jd_text)
    first, second = _request(client, jd_id).json(), _request(client, jd_id).json()
    assert first["id"] == second["id"]
    assert db.query(GenerationJob).count() == 1
    assert _request(client, jd_id, key="k2").json()["id"] != first["id"]


def test_unknown_job_description_rejected_immediately(client):
    assert _request(client, "does-not-exist").status_code == 404


def test_failed_job_reports_a_safe_message_and_can_retry(client, db, monkeypatch, sample_jd_text):
    real_build = draft_service.build_draft

    def broken(*args):
        raise RuntimeError("database password is hunter2")

    monkeypatch.setattr(draft_service, "build_draft", broken)
    job = _request(client, _jd(client, sample_jd_text)).json()
    job_service.process_next(db)
    failed = client.get(f"/api/jobs/{job['id']}").json()
    assert failed["status"] == "failed"
    assert failed["error"] == job_service.FAILURE_MESSAGE
    assert "hunter2" not in failed["error"]

    monkeypatch.setattr(draft_service, "build_draft", real_build)
    assert client.post(f"/api/jobs/{job['id']}/retry").json()["status"] == "queued"
    job_service.process_next(db)
    assert client.get(f"/api/jobs/{job['id']}").json()["status"] == "succeeded"


def test_only_failed_jobs_can_be_retried(client, sample_jd_text):
    job = _request(client, _jd(client, sample_jd_text)).json()
    assert client.post(f"/api/jobs/{job['id']}/retry").status_code == 422


def test_job_abandoned_by_a_crashed_worker_is_picked_up_again(client, db, sample_jd_text):
    job = _request(client, _jd(client, sample_jd_text)).json()
    record = db.get(GenerationJob, job["id"])
    record.status, record.started_at = "running", utcnow() - job_service.STALE_AFTER - timedelta(seconds=1)
    db.commit()
    assert job_service.process_next(db) is True
    assert client.get(f"/api/jobs/{job['id']}").json()["status"] == "succeeded"


def test_recently_started_job_is_left_alone(client, db, sample_jd_text):
    job = _request(client, _jd(client, sample_jd_text)).json()
    record = db.get(GenerationJob, job["id"])
    record.status, record.started_at = "running", utcnow()
    db.commit()
    assert job_service.process_next(db) is False


def test_jobs_are_private(client, make_client, sample_jd_text):
    from tests.conftest import signup
    job = _request(client, _jd(client, sample_jd_text)).json()
    other = make_client()
    signup(other, "other@example.com")
    assert other.get(f"/api/jobs/{job['id']}").status_code == 404
    assert other.post(f"/api/jobs/{job['id']}/retry").status_code == 404
