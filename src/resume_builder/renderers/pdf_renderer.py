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
            BaseDocTemplate,
            Frame,
            FrameBreak,
            PageTemplate,
            Paragraph,
            Spacer,
        )

        buf = BytesIO()
        pw, ph = letter
        lm = rm = 0.55 * inch
        tm = bm = 0.45 * inch
        header_h = 0.9 * inch
        gutter = 0.2 * inch
        usable_w = pw - lm - rm
        side_w = usable_w * 0.34
        main_w = usable_w - side_w - gutter
        body_top = ph - tm - header_h
        body_h = body_top - bm

        header_frame = Frame(
            lm, ph - tm - header_h, usable_w, header_h, id="header",
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        side_frame = Frame(
            lm, bm, side_w, body_h, id="side",
            leftPadding=0, rightPadding=8, topPadding=0, bottomPadding=0,
        )
        main_frame = Frame(
            lm + side_w + gutter, bm, main_w, body_h, id="main",
            leftPadding=8, rightPadding=0, topPadding=0, bottomPadding=0,
        )

        doc = BaseDocTemplate(buf, pagesize=letter)
        doc.addPageTemplates([
            PageTemplate(id="two-col", frames=[header_frame, side_frame, main_frame]),
        ])

        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceAfter=2, fontSize=16)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=6, spaceAfter=2, fontSize=12)
        body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=11, spaceAfter=1)

        story = []

        # --- HEADER frame ---
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

        story.append(FrameBreak())

        # --- SIDEBAR frame: Skills, Certifications, Education (Education last) ---
        if resume.skills:
            story.append(Paragraph("Skills", h2))
            story.append(Paragraph(" &middot; ".join(resume.skills), body))

        if resume.certifications:
            story.append(Paragraph("Certifications", h2))
            for c in resume.certifications:
                line = f"<b>{c.name}</b>"
                if c.issuer:
                    line += f" &mdash; {c.issuer}"
                if c.date:
                    line += f" ({c.date})"
                story.append(Paragraph(line, body))

        # Education last in sidebar — basic supporting info.
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

        story.append(FrameBreak())

        # --- MAIN frame: Summary, Experience, Projects, Achievements ---
        story.append(Paragraph("Summary", h2))
        story.append(Paragraph(resume.summary or "", body))

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

        if resume.achievements:
            story.append(Paragraph("Achievements", h2))
            for a in resume.achievements:
                line = f"<b>{a.title}</b>"
                if a.date:
                    line += f" ({a.date})"
                story.append(Paragraph(line, body))
                if a.snippet:
                    story.append(Paragraph(a.snippet, body))

        doc.build(story)
        return buf.getvalue()
