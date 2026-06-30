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
            Table,
            TableStyle,
        )

        from .brand_icons import drawing as bi_drawing, declutter as bi_declutter

        accent = HexColor("#243b6b")
        rule = HexColor("#c7ccd6")
        muted = HexColor("#5b6270")

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

        # Role label is the dominant H1; name is secondary info in the header.
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceAfter=2, fontSize=17)
        h2 = ParagraphStyle(
            "h2",
            parent=styles["Heading2"],
            spaceBefore=0,
            spaceAfter=3,
            fontSize=11,
            textColor=accent,
        )
        body = ParagraphStyle(
            "body", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=1
        )
        name_style = ParagraphStyle(
            "name_style",
            parent=styles["BodyText"],
            fontSize=11,
            leading=13,
            spaceAfter=1,
            textColor=muted,
        )
        contact_style = ParagraphStyle(
            "contact_style",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            spaceAfter=0,
            textColor=muted,
        )

        story: list = []
        state = {"first": True}

        def section(title: str) -> None:
            if state["first"]:
                state["first"] = False
            else:
                story.append(Spacer(1, 5))
                story.append(
                    HRFlowable(width="100%", thickness=0.6, color=rule, spaceAfter=4)
                )
            story.append(Paragraph(title, h2))

        # ------------------------------------------------------------------ header
        # Role label → H1 (dominant heading)
        role_label = (
            (resume.role.label if resume.role and resume.role.label else "") or "Resume"
        )
        story.append(Paragraph(role_label, h1))

        # Single contact line: name (bold) · email · phone · github · linkedin · facebook
        # Location/address is intentionally omitted from the header.
        _icon_w = 10    # points — icon cell width
        _text_w = 72    # points — handle text cell width
        _sep_w = 6      # points — separator cell width

        contact_cells: list = []
        contact_col_widths: list[float] = []

        def _add_plain(text: str, width: float) -> None:
            contact_cells.append(Paragraph(text, contact_style))
            contact_col_widths.append(width)

        def _add_sep() -> None:
            contact_cells.append(Paragraph("&middot;", contact_style))
            contact_col_widths.append(_sep_w)

        def _add_link(provider: str, raw_val: str, default_base: str) -> None:
            d = bi_drawing(provider, size=9)
            _, handle = bi_declutter(raw_val, provider)
            if not handle:
                return
            href = (
                raw_val
                if raw_val.startswith("http")
                else default_base + handle
            )
            link_p = Paragraph(
                f'<link href="{href}">{handle}</link>', contact_style
            )
            if contact_cells:
                _add_sep()
            if d is not None:
                contact_cells.append(d)
                contact_col_widths.append(_icon_w)
            contact_cells.append(link_p)
            contact_col_widths.append(_text_w)

        def _add_nolink(provider: str, username: str) -> None:
            """Add a branded icon + plain text (no hyperlink). Used for Facebook."""
            if not username:
                return
            d = bi_drawing(provider, size=9)
            plain_p = Paragraph(username, contact_style)
            if contact_cells:
                _add_sep()
            if d is not None:
                contact_cells.append(d)
                contact_col_widths.append(_icon_w)
            contact_cells.append(plain_p)
            contact_col_widths.append(_text_w)

        # Name is always the first item on the contact line (bold).
        if resume.contact.name:
            contact_cells.append(Paragraph(f"<b>{resume.contact.name}</b>", contact_style))
            contact_col_widths.append(100)

        if resume.contact.email:
            if contact_cells:
                _add_sep()
            _add_plain(resume.contact.email, width=110)
        if resume.contact.phone:
            if contact_cells:
                _add_sep()
            _add_plain(resume.contact.phone, width=78)
        if resume.contact.github:
            _add_link("github", resume.contact.github, "https://github.com/")
        if resume.contact.linkedin:
            _add_link("linkedin", resume.contact.linkedin, "https://www.linkedin.com/in/")
        if resume.contact.facebook:
            _add_nolink("facebook", resume.contact.facebook)
        if resume.contact.website:
            _add_link("website", resume.contact.website, "https://")

        if contact_cells:
            tbl = Table(
                [contact_cells],
                colWidths=contact_col_widths,
                hAlign="LEFT",
            )
            tbl.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            story.append(tbl)

        story.append(
            HRFlowable(
                width="100%", thickness=1.2, color=accent, spaceBefore=3, spaceAfter=4
            )
        )

        # ------------------------------------------------------------------ sections

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
                story.append(Paragraph(f"<b>{p.name}</b>", body))
                if p.url:
                    if p.display_url:
                        provider = p.source_icon or "website"
                        path = (
                            p.display_url.replace("github/", "")
                            if provider == "github"
                            else p.display_url
                        )
                    else:
                        provider, path = bi_declutter(p.url)
                        provider = provider or "website"
                    if path:
                        d = bi_drawing(provider, size=8)
                        link_p = Paragraph(
                            f'<link href="{p.url}">{path}</link>',
                            contact_style,
                        )
                        _cells: list = []
                        _widths: list[float] = []
                        if d is not None:
                            _cells.append(d)
                            _widths.append(10)
                        _cells.append(link_p)
                        _widths.append(120)
                        proj_tbl = Table(
                            [_cells],
                            colWidths=_widths,
                            hAlign="LEFT",
                        )
                        proj_tbl.setStyle(
                            TableStyle(
                                [
                                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                                ]
                            )
                        )
                        story.append(proj_tbl)
                if p.tech:
                    story.append(
                        Paragraph(f"<i>{' &middot; '.join(p.tech)}</i>", body)
                    )
                # Bullet order: quantitative_impact first, then description,
                # then qualitative_impact, then component bullets.
                for q in p.quantitative_impact:
                    story.append(Paragraph(q, body))
                if p.description:
                    story.append(Paragraph(p.description, body))
                for ql in p.qualitative_impact:
                    story.append(Paragraph(ql, body))
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
                for note in e.notes:
                    story.append(Paragraph(f"&bull; {note}", body))

        doc.build(story)
        return buf.getvalue()
