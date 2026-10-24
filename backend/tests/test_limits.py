"""Per-user daily limits and sign-in throttling."""

import io
from datetime import timedelta

import pytest
from docx import Document

from app.clock import utcnow
from app.config import settings
from app.models.usage import AuthAttempt, UsageEvent
from app.services import mailer
from tests.conftest import TEST_PASSWORD, signup

JD = "Backend Engineer. Requirements: Python, PostgreSQL, and Docker experience."


def _docx(text: str) -> bytes:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


RESUME = _docx("Priya Raman\npriya@example.com\nExperience\nIntern | Ledgerly\n• Built REST APIs in Django and Python for the finance team")


class TestDailyLimits:
    def test_jd_analysis_limit(self, client, monkeypatch):
        monkeypatch.setattr(settings, "DAILY_JD_ANALYSES", 2)
        assert [client.post("/api/jd/analyze", json={"raw_text": JD}).status_code for _ in range(2)] == [201, 201]
        resp = client.post("/api/jd/analyze", json={"raw_text": JD})
        assert resp.status_code == 429
        assert "limit of 2 job description analyses" in resp.json()["detail"]
        assert 0 < int(resp.headers["Retry-After"]) <= 24 * 3600

    def test_old_uses_expire_after_a_day(self, client, db, monkeypatch):
        monkeypatch.setattr(settings, "DAILY_JD_ANALYSES", 1)
        client.post("/api/jd/analyze", json={"raw_text": JD})
        db.query(UsageEvent).update({UsageEvent.created_at: utcnow() - timedelta(hours=25)})
        db.commit()
        assert client.post("/api/jd/analyze", json={"raw_text": JD}).status_code == 201

    def test_limits_are_per_user(self, client, make_client, monkeypatch):
        monkeypatch.setattr(settings, "DAILY_JD_ANALYSES", 1)
        client.post("/api/jd/analyze", json={"raw_text": JD})
        other = make_client()
        signup(other, "other@example.com")
        assert other.post("/api/jd/analyze", json={"raw_text": JD}).status_code == 201

    def test_unreadable_upload_does_not_count(self, client, monkeypatch):
        monkeypatch.setattr(settings, "DAILY_RESUME_IMPORTS", 1)
        assert client.post("/api/profile/import", files={"file": ("bad.pdf", b"nope" * 20)}).status_code == 422
        assert client.post("/api/profile/import", files={"file": ("r.docx", RESUME)}).status_code == 200
        assert client.post("/api/profile/import", files={"file": ("r.docx", RESUME)}).status_code == 429

    def test_repeating_a_draft_request_does_not_count(self, client, monkeypatch):
        monkeypatch.setattr(settings, "DAILY_DRAFTS", 1)
        jd_id = client.post("/api/jd/analyze", json={"raw_text": JD}).json()["id"]
        first = client.post("/api/drafts", json={"jd_id": jd_id, "idempotency_key": "a"})
        again = client.post("/api/drafts", json={"jd_id": jd_id, "idempotency_key": "a"})
        assert first.status_code == again.status_code == 202
        assert first.json()["id"] == again.json()["id"]
        assert client.post("/api/drafts", json={"jd_id": jd_id, "idempotency_key": "b"}).status_code == 429


class TestSignInThrottling:
    @pytest.fixture(autouse=True)
    def low_limit(self, monkeypatch):
        monkeypatch.setattr(settings, "LOGIN_FAILURE_LIMIT", 3)

    def _login(self, c, email="owner@example.com", password="wrong-password"):
        return c.post("/api/auth/login", json={"email": email, "password": password})

    def test_too_many_failures_block_even_the_right_password(self, client):
        assert [self._login(client).status_code for _ in range(3)] == [401, 401, 401]
        blocked = self._login(client, password=TEST_PASSWORD)
        assert blocked.status_code == 429
        assert "Too many failed sign-in attempts" in blocked.json()["detail"]

    def test_success_resets_the_count(self, client):
        self._login(client)
        self._login(client)
        assert self._login(client, password=TEST_PASSWORD).status_code == 200
        assert [self._login(client).status_code for _ in range(3)] == [401, 401, 401]

    def test_unknown_emails_are_throttled_the_same_way(self, anon_client):
        codes = [self._login(anon_client, email="nobody@example.com").status_code for _ in range(4)]
        assert codes == [401, 401, 401, 429]

    def test_block_expires(self, client, db):
        for _ in range(3):
            self._login(client)
        db.query(AuthAttempt).update({AuthAttempt.created_at: utcnow() - timedelta(minutes=settings.LOGIN_FAILURE_WINDOW_MINUTES + 1)})
        db.commit()
        assert self._login(client, password=TEST_PASSWORD).status_code == 200


def test_reset_emails_are_capped_per_hour(client, monkeypatch):
    monkeypatch.setattr(settings, "RESET_REQUESTS_PER_HOUR", 2)
    sent = []
    monkeypatch.setattr(mailer, "send_password_reset", lambda to, link: sent.append(link))
    codes = [client.post("/api/auth/password-reset/request", json={"email": "owner@example.com"}).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 202]
    assert len(sent) == 2
