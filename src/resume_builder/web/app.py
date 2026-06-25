"""Minimal FastAPI UI on top of the Pipeline.

Routes:
    GET  /           — form (mode, gh user, role, docs upload)
    POST /build      — runs the pipeline, returns links to generated files
    GET  /files/...  — serves the generated files
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import get_settings
from ..models import Mode
from ..pipeline import BuildInputs, Pipeline
from ..role import StaticRolePicker
from .mock_data import PROTOTYPE_DATA

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(title="resume-build-chopper")

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_OUTPUT_ROOT = Path(tempfile.gettempdir()) / "resume-build-chopper-out"
_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
app.mount("/files", StaticFiles(directory=str(_OUTPUT_ROOT)), name="files")


@app.get("/", response_class=HTMLResponse)
def prototype(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "prototype.html",
        {"data": PROTOTYPE_DATA},
    )


@app.get("/prototype", response_class=HTMLResponse)
def prototype_alias(request: Request) -> HTMLResponse:
    return prototype(request)


@app.get("/build-form", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    settings = get_settings()
    roles = StaticRolePicker(settings.roles_path).list_available()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"roles": roles},
    )


@app.post("/build", response_class=HTMLResponse)
async def build_view(
    request: Request,
    mode: Annotated[str, Form()],
    gh_user: Annotated[str, Form()],
    role: Annotated[str, Form()] = "",
    role_prompt: Annotated[str, Form()] = "",
    formats: Annotated[str, Form()] = "latex,md,json,pdf",
    docs: Annotated[UploadFile | None, File()] = None,
) -> HTMLResponse:
    mode_enum = Mode(mode)
    selection = role_prompt if mode_enum == Mode.AI else role
    if not selection:
        return templates.TemplateResponse(
            request,
            "result.html",
            {"error": "Role selection is required.", "files": []},
            status_code=400,
        )

    job_dir = _OUTPUT_ROOT / f"job-{abs(hash((gh_user, selection, formats)))}"
    if job_dir.exists():
        shutil.rmtree(job_dir)
    job_dir.mkdir(parents=True)

    docs_path: Path | None = None
    if docs and docs.filename:
        docs_path = job_dir / docs.filename
        with open(docs_path, "wb") as fp:
            fp.write(await docs.read())

    try:
        pipeline = Pipeline(mode=mode_enum)
        result = pipeline.run(
            BuildInputs(
                gh_user=gh_user,
                role_selection=selection,
                docs_path=docs_path,
                formats=[f.strip() for f in formats.split(",") if f.strip()],
                output_dir=job_dir,
            )
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "result.html",
            {"error": str(exc), "files": []},
            status_code=500,
        )

    files = [
        {"name": p.name, "url": f"/files/{job_dir.name}/{p.name}"}
        for p in result.output_paths
    ]
    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "files": files,
            "resume": result.resume,
            "error": None,
        },
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
