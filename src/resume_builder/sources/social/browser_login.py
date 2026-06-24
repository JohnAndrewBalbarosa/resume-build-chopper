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

from .playwright_debug import highlight_selector, launch_options, visual_debug_from_env

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class VendorConfig:
    """Per-vendor selector + URL data sourced from DevTools analysis of each login page."""

    url: str
    success_cookie: str
    # Optional: an element whose appearance also signals a successful sign-in.
    success_selector: str | None
    # Optional: substring that must appear in ``page.url`` for the login to be
    # considered complete (matches the ``page.waitForURL`` heuristic the FB
    # DevTools AI suggests). When None, URL is not part of the success check.
    success_url_contains: str | None
    # Optional: form field where we can pre-fill a username/email to save a step.
    username_selector: str | None
    # Optional: heuristic to detect that the vendor is asking for a 2FA code.
    twofa_selector: str | None


_VENDOR_CONFIG: dict[str, VendorConfig] = {
    "facebook": VendorConfig(
        url="https://www.facebook.com/",
        success_cookie="c_user",
        success_selector="div[role='main']",
        # After login, FB lands on www.facebook.com/ — login forms live under
        # the same host but with paths like /login.php, /checkpoint/, etc.
        success_url_contains="facebook.com/",
        username_selector="input#email",
        twofa_selector="input#approvals_code",
    ),
    "twitter": VendorConfig(
        url="https://x.com/i/flow/login",
        success_cookie="auth_token",
        success_selector="[data-testid='primaryColumn']",
        success_url_contains="x.com/home",
        username_selector="input[autocomplete='username']",
        twofa_selector="input[autocomplete='one-time-code']",
    ),
    "linkedin": VendorConfig(
        url="https://www.linkedin.com/login",
        success_cookie="li_at",
        success_selector="main",
        success_url_contains="linkedin.com/feed",
        username_selector="input#username",
        twofa_selector="input#input__phone_verification_pin",
    ),
    "instagram": VendorConfig(
        url="https://www.instagram.com/accounts/login/",
        success_cookie="sessionid",
        success_selector="main[role='main']",
        success_url_contains="instagram.com/",
        username_selector="input[name='username']",
        twofa_selector="input[name='verificationCode']",
    ),
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
    prefill_username: str | None = None,
    poll_seconds: float = 1.5,
    timeout_seconds: float = 600.0,
    settle_seconds: float = 2.0,
    playwright_module=None,
    on_twofa_detected=None,
) -> BrowserLoginResult:
    """Open a real Chromium window for the vendor; return cookies after sign-in.

    ``prefill_username`` types the username into the vendor's username field
    automatically (selectors come from each vendor's DevTools analysis), so the user
    only has to type the password + any 2FA code.

    ``on_twofa_detected`` is invoked once when the 2FA input appears — the CLI uses
    this to print a hint like "Enter the code from your authenticator in the window".

    ``playwright_module`` is for tests; production leaves it ``None``.
    """
    sync_playwright = _resolve_playwright(playwright_module)

    cfg = _VENDOR_CONFIG.get(vendor)
    if cfg is None:
        raise RuntimeError(f"No login config for vendor: {vendor}")

    visual_debug = visual_debug_from_env()
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_options(False, visual_debug))
        context = browser.new_context()
        page = context.new_page()
        page.goto(cfg.url)
        highlight_selector(page, "body", label=f"{vendor} login page", debug=visual_debug)

        if prefill_username and cfg.username_selector:
            try:
                highlight_selector(
                    page,
                    cfg.username_selector,
                    label=f"{vendor} username field",
                    debug=visual_debug,
                )
                page.wait_for_selector(cfg.username_selector, timeout=10_000)
                highlight_selector(
                    page,
                    cfg.username_selector,
                    label=f"{vendor} username fill",
                    debug=visual_debug,
                )
                page.fill(cfg.username_selector, prefill_username)
            except Exception as exc:  # noqa: BLE001
                log.debug("prefill skipped (selector %s not ready): %s", cfg.username_selector, exc)

        notified_twofa = False
        highlighted_success = False
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            cookies = _jar_to_dict(context.cookies())
            success_selector_present = _selector_present(page, cfg.success_selector)
            if success_selector_present and not highlighted_success:
                highlighted_success = True
                highlight_selector(
                    page,
                    cfg.success_selector,
                    label=f"{vendor} signed-in marker",
                    debug=visual_debug,
                )
            if (
                cfg.success_cookie in cookies
                and success_selector_present
                and _url_matches(page, cfg.success_url_contains)
            ):
                time.sleep(settle_seconds)
                cookies = _jar_to_dict(context.cookies())
                state = context.storage_state()
                browser.close()
                return BrowserLoginResult(cookies=cookies, storage_state=state)

            if (
                not notified_twofa
                and cfg.twofa_selector
                and on_twofa_detected
                and _selector_present(page, cfg.twofa_selector)
            ):
                notified_twofa = True
                highlight_selector(
                    page,
                    cfg.twofa_selector,
                    label=f"{vendor} 2fa field",
                    debug=visual_debug,
                )
                try:
                    on_twofa_detected(vendor)
                except Exception:  # noqa: BLE001 - never let a CLI callback derail login
                    pass

            time.sleep(poll_seconds)

        browser.close()
        raise TimeoutError(
            f"login window timed out for {vendor} — no `{cfg.success_cookie}` cookie set."
        )


def _selector_present(page, selector: str | None) -> bool:
    """Return True if selector is None (no constraint) or the element is visible."""
    if not selector:
        return True
    try:
        element = page.query_selector(selector)
        return bool(element)
    except Exception:  # noqa: BLE001
        return False


def _url_matches(page, pattern: str | None) -> bool:
    """Return True if ``pattern`` appears anywhere in ``page.url``.

    Matches the spirit of Playwright's ``page.waitForURL`` substring check that the
    FB DevTools AI snippet uses — after a successful login the address bar must
    have already moved to a page on the vendor's domain.
    """
    if not pattern:
        return True
    try:
        current = getattr(page, "url", "") or ""
        return pattern in current
    except Exception:  # noqa: BLE001
        return False


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
