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

        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )

        accent = HexColor("#243b6b")
        rule = HexColor("#c7ccd6")

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceAfter=2, fontSize=17)
        h2 = ParagraphStyle(
            "h2", parent=styles["Heading2"], spaceBefore=0, spaceAfter=3,
            fontSize=11, textColor=accent,
        )
        body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=1)

        story: list = []
        state = {"first": True}

        def section(title: str) -> None:
            # Simple vertical flow: a horizontal rule scopes each section. The first
            # section sits directly under the header rule, so it gets no extra divider.
            if state["first"]:
                state["first"] = False
            else:
                story.append(Spacer(1, 5))
                story.append(HRFlowable(width="100%", thickness=0.6, color=rule, spaceAfter=4))
            story.append(Paragraph(title, h2))

        # --- header ---
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
        if resume.role and resume.role.label:
            story.append(Paragraph(f"<i>{resume.role.label}</i>", body))
        story.append(HRFlowable(width="100%", thickness=1.2, color=accent, spaceBefore=3, spaceAfter=4))

        if resume.summary:
            section("Summary")
            story.append(Paragraph(resume.summary, body))

        if resume.skills:
            section("Skills")
            story.append(Paragraph(" &middot; ".join(resume.skills), body))

        if resume.experience:
            section("Experience")
            for x in resume.experience:
                head = f"<b>{x.role}</b> &mdash; {x.company}"
                if x.start or x.end:
                    head += f" <i>({x.start or ''} – {x.end or 'Present'})</i>"
                story.append(Paragraph(head, body))
                for b in x.bullets:
                    story.append(Paragraph(f"&bull; {b}", body))
                story.append(Spacer(1, 2))

        if resume.projects:
            section("Projects")
            for p in resume.projects:
                head = f"<b>{p.name}</b>"
                if p.url:
                    head += f' <font size=8>&lt;{p.url}&gt;</font>'
                story.append(Paragraph(head, body))
                if p.tech:
                    story.append(Paragraph(f"<i>{' &middot; '.join(p.tech)}</i>", body))
                if p.description:
                    story.append(Paragraph(p.description, body))
                for b in p.bullets:
                    story.append(Paragraph(f"&bull; {b}", body))
                story.append(Spacer(1, 2))

        if resume.achievements:
            section("Achievements")
            for a in resume.achievements:
                line = f"<b>{a.title}</b>"
                if a.date:
                    line += f" ({a.date})"
                story.append(Paragraph(line, body))
                if a.snippet:
                    story.append(Paragraph(a.snippet, body))

        if resume.certifications:
            section("Certifications")
            for c in resume.certifications:
                line = f"<b>{c.name}</b>"
                if c.issuer:
                    line += f" &mdash; {c.issuer}"
                if c.date:
                    line += f" ({c.date})"
                story.append(Paragraph(line, body))

        # Education last — basic supporting info at the bottom of the resume.
        if resume.education:
            section("Education")
            for e in resume.education:
                line = f"<b>{e.school}</b>"
                if e.degree:
                    line += f" &mdash; {e.degree}"
                if e.field:
                    line += f" in {e.field}"
                story.append(Paragraph(line, body))
                for n in e.notes:
                    story.append(Paragraph(f"&bull; {n}", body))

        doc.build(story)
        return buf.getvalue()
