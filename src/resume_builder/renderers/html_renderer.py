"""HTML renderer — a self-contained, print-ready resume page.

Uses standard Jinja2 delimiters with autoescape ON so any user-supplied text is
HTML-escaped (the inline CSS in the template is literal template text and is not
escaped). The output is a single .html file with embedded styles — open it in a
browser and print to PDF for a polished, text-based resume.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models import Resume
from .base import Renderer


class HtmlRenderer(Renderer):
    extension = "html"

    def __init__(self, templates_dir: Path, template_name: str = "resume.html.j2") -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "j2"), default=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._template_name = template_name

    def render(self, resume: Resume) -> str:
        template = self._env.get_template(self._template_name)
        return template.render(resume=resume)
