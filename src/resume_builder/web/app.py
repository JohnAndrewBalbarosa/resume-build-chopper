"""Minimal FastAPI UI on top of the Pipeline.

Routes:
    GET  /           — form (mode, gh user, role, docs upload)
    POST /build      — runs the pipeline, returns links to generated files
    GET  /files/...  — serves the generated files
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
import threading
import traceback
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..core.config import get_settings
from ..llm import LLMUnavailableError, get_provider
from ..core.models import Mode
from ..orchestration.pipeline import BuildInputs, Pipeline
from ..role import StaticRolePicker
from ..sources.social.auth import SessionStore
from ..sources.social.browser_login import PlaywrightNotInstalled, open_login_window
from .auth import (
    IDENTITY_PROVIDERS,
    SOCIAL_VENDORS,
    IdentityStore,
    OAuthExchangeError,
    OAuthSetupError,
    OAuthStateError,
    auth_status,
    build_authorize_url,
    clear_social_session,
    complete_oauth_callback,
    preferred_identity_email,
    provider_configuration_status,
)
from .cdo_advisor import AdvisorAnalyzeRequest, analyze_for_injection
from .mock_data import PROTOTYPE_DATA

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(title="resume-build-chopper")

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARTIFACT_ROOT = _REPO_ROOT / "out"
_OUTPUT_ROOT = Path(tempfile.gettempdir()) / "resume-build-chopper-out"
_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
app.mount("/files", StaticFiles(directory=str(_OUTPUT_ROOT)), name="files")
app.mount("/artifacts", StaticFiles(directory=str(_ARTIFACT_ROOT)), name="artifacts")

_LOGIN_JOBS: dict[str, dict[str, str]] = {}
_LOGIN_JOBS_LOCK = threading.Lock()


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


@app.get("/developer/scraping", response_class=HTMLResponse)
def developer_scraping(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "developer_scraping.html", {})


@app.get("/api/auth/status")
def api_auth_status() -> dict:
    status = auth_status()
    status["oauth_setup"] = provider_configuration_status()
    with _LOGIN_JOBS_LOCK:
        status["jobs"] = dict(_LOGIN_JOBS)
    return status


@app.get("/auth/{provider}/start")
def auth_start(provider: str):
    if provider not in IDENTITY_PROVIDERS:
        return JSONResponse({"error": f"Unknown provider: {provider}"}, status_code=404)
    try:
        return RedirectResponse(build_authorize_url(provider), status_code=302)
    except OAuthSetupError as exc:
        return JSONResponse(
            {
                "error": str(exc),
                "provider": provider,
                "setup_required": True,
            },
            status_code=400,
        )


@app.get("/auth/{provider}/callback")
def auth_callback(provider: str, code: str = "", state: str = ""):
    if provider not in IDENTITY_PROVIDERS:
        return JSONResponse({"error": f"Unknown provider: {provider}"}, status_code=404)
    if not code or not state:
        return JSONResponse({"error": "Missing OAuth code or state."}, status_code=400)
    try:
        complete_oauth_callback(provider, code, state)
    except OAuthSetupError as exc:
        return JSONResponse({"error": str(exc), "setup_required": True}, status_code=400)
    except OAuthStateError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except OAuthExchangeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    except Exception as exc:  # noqa: BLE001 - OAuth providers can fail in many ways
        return JSONResponse({"error": f"OAuth callback failed: {exc}"}, status_code=502)
    return RedirectResponse("/#dashboard", status_code=302)


@app.get("/api/resumes")
def api_resumes() -> dict[str, list[dict[str, object]]]:
    return {"items": _list_generated_resumes()}


@app.post("/api/cdo/advisor/analyze")
def api_cdo_advisor_analyze(payload: AdvisorAnalyzeRequest):
    try:
        result = analyze_for_injection(payload, get_provider())
    except LLMUnavailableError as exc:
        return JSONResponse(
            {
                "error": str(exc),
                "setup_required": True,
                "hint": "Set LLM_PROVIDER plus the provider API key before running AI tagging.",
            },
            status_code=503,
        )
    except Exception as exc:  # noqa: BLE001 - API should surface provider/schema failures
        return JSONResponse({"error": f"CDO advisor analysis failed: {exc}"}, status_code=502)
    return result.model_dump(mode="json")


@app.post("/api/auth/disconnect/{provider}")
def disconnect_identity(provider: str) -> dict[str, object]:
    if provider not in IDENTITY_PROVIDERS:
        return JSONResponse({"error": f"Unknown provider: {provider}"}, status_code=404)
    cleared = IdentityStore().clear_profile(provider)
    return {"provider": provider, "cleared": cleared}


@app.post("/api/social-login/{vendor}")
def start_social_login(vendor: str) -> dict[str, str]:
    if vendor not in SOCIAL_VENDORS:
        return JSONResponse({"error": f"Unknown vendor: {vendor}"}, status_code=404)
    job_id = uuid.uuid4().hex
    _set_job(
        job_id,
        {
            "id": job_id,
            "vendor": vendor,
            "status": "queued",
            "message": "Waiting to open visible browser login.",
        },
    )
    thread = threading.Thread(
        target=_run_social_login_job,
        args=(job_id, vendor),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/social-login/jobs/{job_id}")
def social_login_job(job_id: str):
    with _LOGIN_JOBS_LOCK:
        job = _LOGIN_JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "Unknown job."}, status_code=404)
    return job


@app.post("/api/social-login/{vendor}/disconnect")
def disconnect_social(vendor: str) -> dict[str, object]:
    if vendor not in SOCIAL_VENDORS:
        return JSONResponse({"error": f"Unknown vendor: {vendor}"}, status_code=404)
    cleared = clear_social_session(vendor)
    return {"vendor": vendor, "cleared": cleared}


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


def _list_generated_resumes() -> list[dict[str, object]]:
    resumes_root = _ARTIFACT_ROOT / "resumes"
    if not resumes_root.exists():
        return []
    items: list[dict[str, object]] = []
    for role_dir in sorted(path for path in resumes_root.iterdir() if path.is_dir()):
        formats: dict[str, str] = {}
        newest = 0.0
        for ext in ("html", "json", "md", "pdf", "tex"):
            file_path = role_dir / f"resume.{ext}"
            if not file_path.exists():
                continue
            formats[ext] = f"/artifacts/resumes/{role_dir.name}/resume.{ext}"
            newest = max(newest, file_path.stat().st_mtime)
        if formats:
            items.append(
                {
                    "role_id": role_dir.name,
                    "formats": formats,
                    "updated_at": newest,
                }
            )
    return sorted(items, key=lambda item: float(item["updated_at"]), reverse=True)


def _set_job(job_id: str, payload: dict[str, str]) -> None:
    with _LOGIN_JOBS_LOCK:
        _LOGIN_JOBS[job_id] = payload


def _run_social_login_job(job_id: str, vendor: str) -> None:
    _set_job(
        job_id,
        {
            "id": job_id,
            "vendor": vendor,
            "status": "running",
            "message": "Visible browser login is open. Complete sign-in in Chrome.",
        },
    )
    os.environ.setdefault("RESUME_BUILD_PLAYWRIGHT_VISUAL", "1")
    os.environ.setdefault("RESUME_BUILD_PLAYWRIGHT_DELAY_MS", "700")
    os.environ.setdefault("RESUME_BUILD_PLAYWRIGHT_CDP_URL", "http://127.0.0.1:9222")
    os.environ.setdefault("RESUME_BUILD_LINKEDIN_GOOGLE_LOGIN", "1")
    store = SessionStore()
    try:
        result = open_login_window(
            vendor,
            prefill_username=preferred_identity_email(),
            on_twofa_detected=lambda v: _set_job(
                job_id,
                {
                    "id": job_id,
                    "vendor": v,
                    "status": "running",
                    "message": "Two-factor prompt detected. Enter the code in the open browser.",
                },
            ),
        )
        store.save(vendor, result.cookies)
        if result.storage_state is not None:
            store.save_storage_state(vendor, result.storage_state)
    except PlaywrightNotInstalled as exc:
        _set_job(
            job_id,
            {"id": job_id, "vendor": vendor, "status": "failed", "message": str(exc)},
        )
        return
    except Exception as exc:  # noqa: BLE001 - surfaced as job state to the UI
        message = str(exc).strip() or repr(exc)
        _set_job(
            job_id,
            {
                "id": job_id,
                "vendor": vendor,
                "status": "failed",
                "message": f"{vendor} login failed ({type(exc).__name__}): {message}",
                "traceback": traceback.format_exc(limit=6),
            },
        )
        return
    _set_job(
        job_id,
        {
            "id": job_id,
            "vendor": vendor,
            "status": "success",
            "message": f"{vendor} session saved for future scraping.",
        },
    )
