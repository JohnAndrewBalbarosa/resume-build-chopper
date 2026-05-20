"""Shared auth primitives for social vendors that support real sign-in flows.

Three concerns live here, kept tiny on purpose:

1. ``LoginPrompt`` — abstract surface for asking the user a question. Console impl
   uses ``input()`` / ``getpass()``; tests can swap in a scripted prompt.

2. ``LoginChallenge`` — discriminated enum returned by a vendor mid-login when the
   server demands extra proof (TOTP / SMS / email / CAPTCHA). The orchestrator
   reads ``challenge.kind`` and ``challenge.question`` and routes to the prompt.

3. ``SessionStore`` — JSON-on-disk persistence for vendor cookies so a successful
   login carries across CLI invocations. Files are written 0600.

Vendors are NOT required to implement login. The ``LoginCapable`` mixin is opt-in.
"""

from __future__ import annotations

import getpass
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable

log = logging.getLogger(__name__)


# ---- prompts ----


@runtime_checkable
class LoginPrompt(Protocol):
    def ask(self, question: str, *, secret: bool = False) -> str:
        ...


class ConsolePrompt:
    """Default: read from stdin. Hides input for ``secret=True`` via getpass."""

    def ask(self, question: str, *, secret: bool = False) -> str:
        if secret:
            return getpass.getpass(f"{question}: ")
        return input(f"{question}: ").strip()


@dataclass
class ScriptedPrompt:
    """Test double — pops answers in order. Raises if asked beyond the script."""

    answers: list[str]

    def ask(self, question: str, *, secret: bool = False) -> str:
        if not self.answers:
            raise AssertionError(f"ScriptedPrompt exhausted on: {question!r}")
        return self.answers.pop(0)


# ---- challenges ----


class ChallengeKind(str, Enum):
    TOTP = "totp"           # 6-digit code from authenticator app
    SMS = "sms"             # code sent to phone
    EMAIL = "email"         # code sent to email
    PUSH_APPROVAL = "push"  # tap on phone app — poll-based, no input
    CAPTCHA = "captcha"     # visual — unsupported on console
    UNKNOWN = "unknown"


@dataclass
class LoginChallenge:
    kind: ChallengeKind
    question: str
    state: dict = field(default_factory=dict)


@dataclass
class Credentials:
    username: str
    password: str


class LoginError(RuntimeError):
    """Login failed and cannot recover via console (e.g. CAPTCHA)."""


# ---- session store ----


def _default_session_dir() -> Path:
    base = os.environ.get("RESUME_BUILDER_CACHE") or (Path.home() / ".cache" / "resume-builder" / "social")
    path = Path(base) / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


class SessionStore:
    """Per-vendor cookie persistence."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _default_session_dir()
        self._dir.mkdir(parents=True, exist_ok=True)

    def path(self, vendor: str) -> Path:
        return self._dir / f"{vendor}.json"

    def load(self, vendor: str) -> dict[str, str]:
        p = self.path(vendor)
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("session load failed for %s: %s", vendor, exc)
            return {}

    def save(self, vendor: str, cookies: dict[str, str]) -> None:
        p = self.path(vendor)
        try:
            p.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
            try:
                os.chmod(p, 0o600)
            except OSError:
                pass
        except OSError as exc:
            log.warning("session save failed for %s: %s", vendor, exc)

    def clear(self, vendor: str) -> None:
        p = self.path(vendor)
        if p.exists():
            try:
                p.unlink()
            except OSError as exc:
                log.warning("session clear failed for %s: %s", vendor, exc)


# ---- mixin / capability marker ----


@runtime_checkable
class LoginCapable(Protocol):
    """Vendors implementing programmatic login satisfy this protocol."""

    name: str

    def login(self, creds: Credentials, prompt: LoginPrompt) -> dict[str, str]:
        """Return cookie dict on success. Raise ``LoginError`` on unrecoverable failure."""


# ---- layered cookie resolution ----


def _parse_cookie_string(raw: str) -> dict[str, str]:
    """Parse a `k1=v1; k2=v2` cookie header into a dict."""
    out: dict[str, str] = {}
    for chunk in (raw or "").split(";"):
        if "=" in chunk:
            k, v = chunk.strip().split("=", 1)
            if k.strip():
                out[k.strip()] = v.strip()
    return out


# Env-var contract per vendor. Some carry the full cookie header (FB),
# others carry just the session token (LI/IG); both styles work because we
# pass the resulting dict through to requests.cookies.set.
_ENV_VAR: dict[str, str] = {
    "facebook": "FB_COOKIE",
    "linkedin": "LI_COOKIE",
    "instagram": "IG_COOKIE",
    "twitter": "TW_COOKIE",
}

# Single-key env vars: if value has no '=', treat as the named cookie's value.
_ENV_SINGLE_KEY: dict[str, str] = {
    "linkedin": "li_at",
    "instagram": "sessionid",
    "twitter": "auth_token",
}


def resolve_session_cookies(
    vendor: str, *, prefer_browser: str = "auto"
) -> dict[str, str]:
    """Return the best available cookie set for ``vendor`` without prompting.

    Resolution order:
      1. Explicit env var (``FB_COOKIE`` / ``LI_COOKIE`` / ``IG_COOKIE`` / ``TW_COOKIE``).
      2. Persistent session store (cookies from a prior ``resume-build login`` run).
      3. Local browser cookie jar via ``browser_cookie3`` (Chrome first, then auto).

    The browser path's success is cached into the session store so subsequent runs
    are fast and don't repeatedly hit DPAPI / keychain prompts.
    """

    env_name = _ENV_VAR.get(vendor)
    if env_name:
        raw = os.environ.get(env_name, "").strip()
        if raw:
            if "=" in raw:
                return _parse_cookie_string(raw)
            single = _ENV_SINGLE_KEY.get(vendor)
            if single:
                return {single: raw}

    store = SessionStore()
    saved = store.load(vendor)
    if saved:
        return saved

    # Last resort: import live from local browser. Lazy import keeps the optional
    # dep truly optional. Tests / CI can set RESUME_BUILDER_NO_BROWSER_COOKIES=1
    # to suppress the live scan.
    if os.environ.get("RESUME_BUILDER_NO_BROWSER_COOKIES"):
        return {}
    try:
        from .browser_cookies import import_cookies_report
    except Exception:  # noqa: BLE001
        return {}
    report = import_cookies_report(vendor, browser=prefer_browser)
    if report.ok:
        try:
            store.save(vendor, report.cookies)
        except Exception:  # noqa: BLE001 - cache write is best-effort
            pass
        log.info(
            "resolved %s cookies from local browser (%d entries)",
            vendor,
            len(report.cookies),
        )
        return report.cookies
    return {}
