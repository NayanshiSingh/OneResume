"""PDF Renderer — renders resume data to HTML with Jinja2, then to PDF with WeasyPrint."""

from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _is_safe_url(value) -> bool:
    """Only http(s) links are rendered as links; anything else is shown as text."""
    return isinstance(value, str) and urlparse(value).scheme in {"http", "https"}


_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html", "j2"]))
_env.tests["safe_url"] = _is_safe_url


def render_resume_html(resume_data: dict) -> str:
    return _env.get_template("resume.html.j2").render(**resume_data)


def render_resume_pdf(resume_data: dict) -> bytes:
    # Imported here because WeasyPrint needs system libraries (pango); the rest
    # of the app must still start without them.
    from weasyprint import HTML

    return HTML(string=render_resume_html(resume_data)).write_pdf()
