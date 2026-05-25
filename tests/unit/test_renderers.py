from __future__ import annotations

import json

from resume_builder.models import (
    ContactInfo,
    Resume,
    ResumeExperience,
    ResumeProject,
    RoleSpec,
)
from resume_builder.renderers import (
    JsonRenderer,
    LatexRenderer,
    MarkdownRenderer,
    get_renderer,
)


def _resume() -> Resume:
    return Resume(
        role=RoleSpec(id="r", label="Cybersecurity Blue Team", keywords=["SIEM"]),
        contact=ContactInfo(name="Drew", email="me@example.com", github="https://github.com/drew"),
        summary="Defensive security engineer.",
        skills=["SIEM", "Splunk", "incident response"],
        experience=[
            ResumeExperience(role="SOC Analyst", company="Acme", bullets=["Tuned 30+ Sigma rules."])
        ],
        projects=[
            ResumeProject(
                name="soc-playbook",
                url="https://github.com/drew/soc-playbook",
                description="Detection playbook.",
                bullets=["Reduced MTTD by 40%."],
                tech=["Python"],
            )
        ],
    )


def test_json_renderer_roundtrip():
    out = JsonRenderer().render(_resume())
    parsed = json.loads(out)
    assert parsed["role"]["label"] == "Cybersecurity Blue Team"
    assert parsed["projects"][0]["name"] == "soc-playbook"


def test_markdown_renderer_contains_sections(templates_dir):
    out = MarkdownRenderer(templates_dir).render(_resume())
    assert "# Drew" in out
    assert "## Projects" in out
    assert "soc-playbook" in out


def test_latex_renderer_escapes_specials(templates_dir):
    resume = _resume()
    resume.summary = "Worked with 100% of clients & saved $1M."
    out = LatexRenderer(templates_dir).render(resume)
    assert r"100\%" in out
    assert r"\&" in out
    assert r"\$1M" in out
    assert r"\documentclass" in out


def test_registry_resolves(templates_dir):
    assert isinstance(get_renderer("json", templates_dir), JsonRenderer)
    assert isinstance(get_renderer("MD", templates_dir), MarkdownRenderer)
    assert isinstance(get_renderer("latex", templates_dir), LatexRenderer)


def test_pdf_renders_single_column_smoke(templates_dir):
    from resume_builder.renderers.pdf_renderer import PdfRenderer
    from resume_builder.models import Resume, RoleSpec, ContactInfo, ResumeProject
    resume = Resume(
        role=RoleSpec(id="r", label="R", keywords=[], must_have_skills=[], nice_to_have=[]),
        contact=ContactInfo(name="Test User"),
        summary="A summary.", skills=["Python", "C++"],
        projects=[ResumeProject(name="Proj", description="d", tech=["Python"])],
        experience=[], education=[],
    )
    pdf = PdfRenderer(templates_dir).render(resume)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 800


def test_latex_is_single_column(templates_dir):
    from resume_builder.renderers.latex_renderer import LatexRenderer
    from resume_builder.models import Resume, RoleSpec, ContactInfo
    resume = Resume(
        role=RoleSpec(id="r", label="R", keywords=[], must_have_skills=[], nice_to_have=[]),
        contact=ContactInfo(name="Test User"), summary="S", skills=["Python"],
        projects=[], experience=[], education=[],
    )
    tex = LatexRenderer(templates_dir).render(resume)
    # Single-column vertical flow; section rule (titlerule) scopes each heading.
    assert "paracol" not in tex
    assert "\\titlerule" in tex
    assert "\\section*{Summary}" in tex


def test_html_is_single_column_with_section_dividers(templates_dir):
    from resume_builder.renderers.html_renderer import HtmlRenderer
    from resume_builder.models import Resume, RoleSpec, ContactInfo
    resume = Resume(
        role=RoleSpec(id="r", label="R", keywords=[], must_have_skills=[], nice_to_have=[]),
        contact=ContactInfo(name="Test User"),
        summary="S", skills=["Python"], projects=[], experience=[], education=[],
    )
    html = HtmlRenderer(templates_dir).render(resume)
    # No two-column grid; sections are scoped by a horizontal divider (border-top).
    assert "grid-template-columns" not in html
    assert 'class="sidebar"' not in html and 'class="main"' not in html
    assert "border-top:1px solid var(--rule)" in html
