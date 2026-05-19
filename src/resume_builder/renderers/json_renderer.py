from __future__ import annotations

from ..models import Resume
from .base import Renderer


class JsonRenderer(Renderer):
    extension = "json"

    def render(self, resume: Resume) -> str:
        return resume.model_dump_json(indent=2)
