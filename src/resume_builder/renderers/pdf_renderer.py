"""PDF renderer.

Strategy:
1. If `pdflatex` is on PATH, render via the LaTeX template and compile.
2. Else, fall back to a direct reportlab layout from the Resume model.

This keeps the dependency surface optional — no LaTeX install required.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ..models import Resume
from .base import Renderer
from .latex_renderer import LatexRenderer


class PdfRenderer(Renderer):
    extension = "pdf"

    def __init__(self, templates_dir: Path) -> None:
        self._latex = LatexRenderer(templates_dir)

    def render(self, resume: Resume) -> bytes:
        if shutil.which("pdflatex"):
            tex_source = self._latex.render(resume)
            pdf_bytes = self._compile_latex(tex_source)
            if pdf_bytes:
                return pdf_bytes
        return self._render_reportlab(resume)

    @staticmethod
    def _compile_latex(tex_source: str) -> bytes | None:
        with tempfile.TemporaryDirectory() as td:
            tex_path = Path(td) / "resume.tex"
            tex_path.write_text(tex_source, encoding="utf-8")
            try:
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"],
                    cwd=td,
                    capture_output=True,
                    check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                return None
            pdf_path = Path(td) / "resume.pdf"
            return pdf_path.read_bytes() if pdf_path.exists() else None

    @staticmethod
    def _render_reportlab(resume: Resume) -> bytes:
        from io import BytesIO

        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=0.55 * inch,
            rightMargin=0.55 * inch,
            topMargin=0.45 * inch,
            bottomMargin=0.45 * inch,
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceAfter=2, fontSize=16)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=6, spaceAfter=2, fontSize=12)
        body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=11, spaceAfter=1)
        story = []

        story.append(Paragraph(resume.contact.name or "Resume", h1))
        contact_bits = [
            resume.contact.email,
            resume.contact.phone,
            resume.contact.location,
            resume.contact.github,
            resume.contact.linkedin,
            resume.contact.website,
        ]
        contact_line = " &middot; ".join(b for b in contact_bits if b)
        if contact_line:
            story.append(Paragraph(contact_line, body))
        story.append(Paragraph(f"<i>Target role:</i> <b>{resume.role.label}</b>", body))

        story.append(Paragraph("Summary", h2))
        story.append(Paragraph(resume.summary or "", body))

        if resume.skills:
            story.append(Paragraph("Skills", h2))
            story.append(Paragraph(" &middot; ".join(resume.skills), body))

        if resume.experience:
            story.append(Paragraph("Experience", h2))
            for x in resume.experience:
                head = f"<b>{x.role}</b> &mdash; {x.company}"
                if x.start or x.end:
                    head += f" <i>({x.start or ''} – {x.end or 'Present'})</i>"
                story.append(Paragraph(head, body))
                for b in x.bullets:
                    story.append(Paragraph(f"&bull; {b}", body))
                story.append(Spacer(1, 2))

        if resume.projects:
            story.append(Paragraph("Projects", h2))
            for p in resume.projects:
                head = f"<b>{p.name}</b>"
                if p.url:
                    head += f' <font size=8>&lt;{p.url}&gt;</font>'
                story.append(Paragraph(head, body))
                if p.description:
                    story.append(Paragraph(p.description, body))
                for b in p.bullets:
                    story.append(Paragraph(f"&bull; {b}", body))
                if p.tech:
                    story.append(Paragraph(f"<i>Tech: {', '.join(p.tech)}</i>", body))
                story.append(Spacer(1, 2))

        if resume.education:
            story.append(Paragraph("Education", h2))
            for e in resume.education:
                line = f"<b>{e.school}</b>"
                if e.degree:
                    line += f" &mdash; {e.degree}"
                if e.field:
                    line += f" in {e.field}"
                story.append(Paragraph(line, body))
                for n in e.notes:
                    story.append(Paragraph(f"&bull; {n}", body))

        if resume.certifications:
            story.append(Paragraph("Certifications", h2))
            for c in resume.certifications:
                line = f"<b>{c.name}</b>"
                if c.issuer:
                    line += f" &mdash; {c.issuer}"
                if c.date:
                    line += f" ({c.date})"
                story.append(Paragraph(line, body))

        doc.build(story)
        return buf.getvalue()
