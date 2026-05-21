"""Playwright-driven sign-in: the only login UX an end user should see.

Tool opens a real Chromium window pointed at the vendor's login URL. The user does
exactly what they would do anywhere else — type credentials, complete 2FA, solve any
CAPTCHA. While that happens we poll the browser context's cookie jar; when the
vendor's session-defining cookie appears we wait a short settle window, grab every
cookie, and close the browser.

No DevTools, no curl, no library decryption — the same TLS session the user
authenticated through is the one whose cookies we keep.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)


_LOGIN_URLS: dict[str, str] = {
    "facebook": "https://www.facebook.com/",
    "twitter": "https://x.com/i/flow/login",
    "linkedin": "https://www.linkedin.com/login",
    "instagram": "https://www.instagram.com/accounts/login/",
}

# Cookie whose presence means the vendor has authenticated the session.
_SUCCESS_COOKIE: dict[str, str] = {
    "facebook": "c_user",
    "twitter": "auth_token",
    "linkedin": "li_at",
    "instagram": "sessionid",
}


class PlaywrightNotInstalled(RuntimeError):
    """Raised when ``playwright`` isn't importable so the CLI can print install hints."""


@dataclass(frozen=True)
class BrowserLoginResult:
    cookies: dict[str, str]
    storage_state: dict | None


def open_login_window(
    vendor: str,
    *,
    poll_seconds: float = 1.5,
    timeout_seconds: float = 600.0,
    settle_seconds: float = 2.0,
    playwright_module=None,
) -> BrowserLoginResult:
    """Open a real Chromium window for the vendor; return cookies after sign-in.

    ``playwright_module`` is for tests — production callers leave it None and the
    real ``playwright.sync_api`` is imported lazily.
    """
    sync_playwright = _resolve_playwright(playwright_module)

    url = _LOGIN_URLS.get(vendor)
    if not url:
        raise RuntimeError(f"No login URL configured for vendor: {vendor}")
    success_cookie = _SUCCESS_COOKIE[vendor]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            cookies = _jar_to_dict(context.cookies())
            if success_cookie in cookies:
                time.sleep(settle_seconds)
                cookies = _jar_to_dict(context.cookies())
                state = context.storage_state()
                browser.close()
                return BrowserLoginResult(cookies=cookies, storage_state=state)
            time.sleep(poll_seconds)

        browser.close()
        raise TimeoutError(
            f"login window timed out for {vendor} — no `{success_cookie}` cookie set."
        )


def _resolve_playwright(injected):
    if injected is not None:
        return injected
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PlaywrightNotInstalled(
            "playwright is not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        ) from exc
    return sync_playwright


def _jar_to_dict(jar) -> dict[str, str]:
    return {c["name"]: c["value"] for c in jar or [] if c.get("value")}
