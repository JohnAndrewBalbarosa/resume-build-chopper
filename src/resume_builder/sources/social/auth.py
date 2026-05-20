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
