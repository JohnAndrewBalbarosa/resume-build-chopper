from __future__ import annotations

from resume_builder.models import ResumeProject, RoleSpec
from resume_builder import pipeline as P


def _role(**kw) -> RoleSpec:
    base = dict(id="r", label="R", keywords=[], must_have_skills=[], nice_to_have=[])
    base.update(kw)
    return RoleSpec(**base)


def test_keyword_fallback_keeps_relevant_drops_unrelated():
    role = _role(keywords=["compiler", "C++"])
    projects = [
        ResumeProject(name="Andrew-mini-compiler", description="A small compiler", tech=["C++"]),
        ResumeProject(name="codespaces-react", description="A React starter", tech=["JavaScript"]),
    ]
    kept = P._filter_projects_by_role(projects, role, llm=None)
    names = [p.name for p in kept]
    assert "Andrew-mini-compiler" in names
    assert "codespaces-react" not in names


def test_keyword_fallback_empty_when_nothing_matches():
    role = _role(keywords=["pytorch", "tensorflow"])
    projects = [ResumeProject(name="codespaces-react", description="React", tech=["JavaScript"])]
    assert P._filter_projects_by_role(projects, role, llm=None) == []
