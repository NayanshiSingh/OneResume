"""LaTeX Renderer — renders resume data to PDF via Jinja2 + pdflatex."""

import os
import re
import subprocess
import tempfile
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.config import settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def latex_escape(text: str) -> str:
    """Escape special LaTeX characters in text."""
    if not text:
        return ""
    text = str(text)
    # Order matters — backslash first
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def render_latex(resume_data: dict) -> str:
    """Render resume data into LaTeX source using Jinja2 template."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        block_start_string="{% ",
        block_end_string=" %}",
        variable_start_string="{{",
        variable_end_string="}}",
        comment_start_string="{# ",
        comment_end_string=" #}",
    )
    env.filters["latex_escape"] = latex_escape

    template = env.get_template("resume.tex.j2")
    return template.render(**resume_data)


def compile_pdf(latex_source: str, output_path: str) -> str:
    """Compile LaTeX source to PDF using pdflatex.

    Returns the path to the generated PDF file.
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = os.path.join(tmpdir, "resume.tex")
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_source)

        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_file],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.error("pdflatex stderr: %s", result.stderr)
                logger.error("pdflatex stdout: %s", result.stdout[-2000:])
        except FileNotFoundError:
            logger.error("pdflatex not found. Install texlive: sudo apt-get install texlive-latex-base texlive-latex-extra")
            raise RuntimeError("pdflatex not installed")

        pdf_source = os.path.join(tmpdir, "resume.pdf")
        if not os.path.exists(pdf_source):
            raise RuntimeError(f"PDF compilation failed. Check LaTeX source.")

        # Copy to final destination
        import shutil
        shutil.copy2(pdf_source, output_path)

    return output_path


def render_resume_to_pdf(resume_data: dict, output_path: str) -> str:
    """Full pipeline: resume data → LaTeX → PDF."""
    latex_source = render_latex(resume_data)
    return compile_pdf(latex_source, output_path)
