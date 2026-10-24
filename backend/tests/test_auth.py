"""Accounts: registration, sessions, password reset, CSRF origin check, deletion."""

from datetime import timedelta

from app.models.user import PasswordResetToken, User, UserSession
from app.clock import utcnow
from app.services import auth_service, mailer
from tests.conftest import TEST_PASSWORD, signup


def _capture_reset_links(monkeypatch) -> list[str]:
    links = []
    monkeypatch.setattr(mailer, "send_password_reset", lambda to, link: links.append(link))
    return links


def _token_from(link: str) -> str:
    return link.split("token=", 1)[1]


class TestRegistration:
    def test_register_signs_in_and_creates_profile(self, anon_client):
        user = signup(anon_client, "New@Example.com")
        assert user["email"] == "new@example.com"
        assert anon_client.get("/api/auth/me").json()["id"] == user["id"]
        assert anon_client.get("/api/profile").status_code == 200

    def test_password_is_stored_hashed(self, anon_client, db):
        signup(anon_client, "hash@example.com")
        stored = db.query(User).filter_by(email="hash@example.com").one().password_hash
        assert TEST_PASSWORD not in stored
        assert stored.startswith("$argon2")

    def test_duplicate_email_rejected(self, anon_client):
        signup(anon_client, "dup@example.com")
        resp = anon_client.post("/api/auth/register", json={"email": "DUP@example.com", "password": TEST_PASSWORD})
        assert resp.status_code == 409

    def test_short_password_rejected(self, anon_client):
        resp = anon_client.post("/api/auth/register", json={"email": "a@example.com", "password": "short"})
        assert resp.status_code == 422

    def test_session_cookie_is_http_only(self, anon_client):
        resp = anon_client.post("/api/auth/register", json={"email": "c@example.com", "password": TEST_PASSWORD})
        cookie = resp.headers["set-cookie"].lower()
        assert "httponly" in cookie
        assert "samesite=lax" in cookie


class TestLogin:
    def test_login_and_logout(self, make_client):
        signup(make_client(), "login@example.com")
        c = make_client()
        assert c.get("/api/auth/me").status_code == 401
        assert c.post("/api/auth/login", json={"email": "login@example.com", "password": TEST_PASSWORD}).status_code == 200
        assert c.get("/api/auth/me").status_code == 200
        assert c.post("/api/auth/logout").status_code == 204
        assert c.get("/api/auth/me").status_code == 401

    def test_wrong_password_and_unknown_email_look_the_same(self, anon_client):
        signup(anon_client, "known@example.com")
        wrong = anon_client.post("/api/auth/login", json={"email": "known@example.com", "password": "not-the-password"})
        unknown = anon_client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "not-the-password"})
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json()

    def test_expired_session_is_rejected(self, client, db):
        session = db.query(UserSession).one()
        session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        assert client.get("/api/auth/me").status_code == 401
        assert db.query(UserSession).count() == 0

    def test_protected_routes_require_sign_in(self, anon_client):
        for path in ["/api/profile", "/api/resumes", "/api/jd", "/api/drafts", "/api/jobs/x"]:
            assert anon_client.get(path).status_code == 401
        assert anon_client.post("/api/drafts", json={"jd_id": "x", "idempotency_key": "k"}).status_code == 401


class TestPasswordReset:
    def test_reset_changes_password_and_signs_out_everywhere(self, client, make_client, monkeypatch):
        links = _capture_reset_links(monkeypatch)
        other = make_client()
        assert other.post("/api/auth/password-reset/request", json={"email": "owner@example.com"}).status_code == 202
        token = _token_from(links[0])

        resp = other.post("/api/auth/password-reset/confirm", json={"token": token, "new_password": "brand-new-password"})
        assert resp.status_code == 204
        assert client.get("/api/auth/me").status_code == 401
        assert other.post("/api/auth/login", json={"email": "owner@example.com", "password": TEST_PASSWORD}).status_code == 401
        assert other.post("/api/auth/login", json={"email": "owner@example.com", "password": "brand-new-password"}).status_code == 200

    def test_reset_token_works_once(self, client, monkeypatch):
        links = _capture_reset_links(monkeypatch)
        client.post("/api/auth/password-reset/request", json={"email": "owner@example.com"})
        token = _token_from(links[0])
        body = {"token": token, "new_password": "brand-new-password"}
        assert client.post("/api/auth/password-reset/confirm", json=body).status_code == 204
        assert client.post("/api/auth/password-reset/confirm", json=body).status_code == 400

    def test_expired_reset_token_rejected(self, client, db, monkeypatch):
        links = _capture_reset_links(monkeypatch)
        client.post("/api/auth/password-reset/request", json={"email": "owner@example.com"})
        db.query(PasswordResetToken).one().expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        body = {"token": _token_from(links[0]), "new_password": "brand-new-password"}
        assert client.post("/api/auth/password-reset/confirm", json=body).status_code == 400

    def test_unknown_email_gets_same_response_and_no_email(self, anon_client, monkeypatch):
        links = _capture_reset_links(monkeypatch)
        resp = anon_client.post("/api/auth/password-reset/request", json={"email": "ghost@example.com"})
        assert resp.status_code == 202
        assert links == []


class TestOriginCheck:
    def test_write_from_foreign_origin_rejected(self, client):
        resp = client.post("/api/profile/skills", json={"skill_name": "Python"}, headers={"Origin": "https://evil.example"})
        assert resp.status_code == 403

    def test_write_from_allowed_origin_accepted(self, client):
        resp = client.post("/api/profile/skills", json={"skill_name": "Python"}, headers={"Origin": "http://localhost:3000"})
        assert resp.status_code == 201


class TestAccountDeletion:
    def test_delete_account_removes_data_and_files(self, client, db, strong_fit_profile_data, sample_jd_text, tmp_path):
        from tests.conftest import export_resume, fill_profile
        fill_profile(client, strong_fit_profile_data)
        export_resume(client, db, sample_jd_text)
        user_id = client.get("/api/auth/me").json()["id"]
        user_dir = tmp_path / "storage" / "users" / user_id
        assert user_dir.exists()

        assert client.delete("/api/auth/account").status_code == 204
        assert client.get("/api/auth/me").status_code == 401
        assert db.query(User).count() == 0
        assert not user_dir.exists()
