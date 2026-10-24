"""Export artifacts: private unique storage, correct formats, and safe templates."""

import pytest

from app.models.resume import ExportArtifact
from app.services import export_service
from app.services.pdf_renderer import render_resume_html
from tests.conftest import export_resume, fill_profile, signup

try:
    from weasyprint import HTML  # noqa: F401
    HAS_WEASYPRINT = True
except OSError:  # system libraries such as pango are missing
    HAS_WEASYPRINT = False


def test_versions_for_the_same_role_get_separate_files(client, db, strong_fit_profile_data, sample_jd_text, tmp_path):
    fill_profile(client, strong_fit_profile_data)
    first, second = export_resume(client, db, sample_jd_text), export_resume(client, db, sample_jd_text)
    assert (first["version"], second["version"]) == (1, 2)

    keys = {a.storage_key for a in db.query(ExportArtifact).all()}
    assert len(keys) == len(first["formats"]) + len(second["formats"])
    assert all((tmp_path / "storage" / k).exists() for k in keys)


def test_two_users_with_the_same_role_do_not_overwrite_each_other(
    make_client, db, strong_fit_profile_data, weak_fit_profile_data, sample_jd_text,
):
    alice, bob = make_client(), make_client()
    signup(alice, "alice@example.com")
    signup(bob, "bob@example.com")
    fill_profile(alice, strong_fit_profile_data)
    fill_profile(bob, weak_fit_profile_data)
    a, b = export_resume(alice, db, sample_jd_text), export_resume(bob, db, sample_jd_text)
    assert a["job_title"] == b["job_title"] and a["version"] == b["version"] == 1

    a_docx = alice.get(f"/api/resumes/{a['id']}/download?format=docx").content
    b_docx = bob.get(f"/api/resumes/{b['id']}/download?format=docx").content
    assert a_docx != b_docx
    assert b"John Doe" in _docx_text(a_docx)
    assert b"Jane Smith" in _docx_text(b_docx)


def _docx_text(data: bytes) -> bytes:
    import io
    import zipfile
    return zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml")


def test_docx_download_has_docx_type_and_content(client, db, strong_fit_profile_data, sample_jd_text):
    fill_profile(client, strong_fit_profile_data)
    result = export_resume(client, db, sample_jd_text)
    resp = client.get(f"/api/resumes/{result['id']}/download?format=docx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert resp.content[:2] == b"PK"
    assert resp.headers["content-disposition"].endswith('_v1.docx"')


@pytest.mark.skipif(not HAS_WEASYPRINT, reason="WeasyPrint system libraries not installed")
def test_pdf_download_is_a_real_pdf(client, db, strong_fit_profile_data, sample_jd_text):
    fill_profile(client, strong_fit_profile_data)
    result = export_resume(client, db, sample_jd_text)
    assert "pdf" in result["formats"]
    resp = client.get(f"/api/resumes/{result['id']}/download?format=pdf")
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_failed_pdf_is_never_served_as_another_format(client, db, monkeypatch, strong_fit_profile_data, sample_jd_text):
    """Regression: a DOCX used to be returned for ?format=pdf when PDF rendering failed."""
    def broken_pdf(_):
        raise OSError("renderer unavailable")

    monkeypatch.setattr(export_service, "render_resume_pdf", broken_pdf)
    fill_profile(client, strong_fit_profile_data)
    result = export_resume(client, db, sample_jd_text)
    assert result["formats"] == ["docx"]
    assert client.get(f"/api/resumes/{result['id']}/download?format=pdf").status_code == 404
    assert client.get(f"/api/resumes/{result['id']}").json()["formats"] == ["docx"]


def test_unknown_format_rejected(client, db, strong_fit_profile_data, sample_jd_text):
    fill_profile(client, strong_fit_profile_data)
    result = export_resume(client, db, sample_jd_text)
    assert client.get(f"/api/resumes/{result['id']}/download?format=exe").status_code == 422


def test_deleting_a_resume_removes_its_files(client, db, strong_fit_profile_data, sample_jd_text, tmp_path):
    fill_profile(client, strong_fit_profile_data)
    result = export_resume(client, db, sample_jd_text)
    keys = [a.storage_key for a in db.query(ExportArtifact).all()]
    assert client.delete(f"/api/resumes/{result['id']}").status_code == 204
    assert not any((tmp_path / "storage" / k).exists() for k in keys)
    assert client.get("/api/resumes").json() == []


def test_version_numbers_are_not_reused_after_deletion(client, db, strong_fit_profile_data, sample_jd_text):
    fill_profile(client, strong_fit_profile_data)
    first, second = export_resume(client, db, sample_jd_text), export_resume(client, db, sample_jd_text)
    client.delete(f"/api/resumes/{first['id']}")
    assert export_resume(client, db, sample_jd_text)["version"] == second["version"] + 1


class TestTemplate:
    def test_user_text_is_escaped(self):
        html = render_resume_html({"personal_info": {"full_name": "<script>alert(1)</script>"}})
        assert "<script>alert(1)" not in html
        assert "&lt;script&gt;" in html

    def test_only_http_links_are_rendered_as_links(self):
        html = render_resume_html({
            "personal_info": {"full_name": "A"},
            "external_profiles": [
                {"platform": "GitHub", "profile_url": "https://github.com/a"},
                {"platform": "Bad", "profile_url": "javascript:alert(1)"},
            ],
        })
        assert 'href="https://github.com/a"' in html
        assert "javascript:" not in html
