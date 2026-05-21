"""Playwright login flow tested with a fully mocked playwright module."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from resume_builder.sources.social.browser_login import (
    PlaywrightNotInstalled,
    open_login_window,
)


def _make_playwright(cookie_jar_sequence: list[list[dict]], storage_state: dict | None = None):
    """Build a fake sync_playwright that returns the supplied cookie jars in order.

    Each call to ``context.cookies()`` pops the next jar. When the jar contains the
    success cookie, the flow exits and returns.
    """
    context = MagicMock()
    storage = storage_state if storage_state is not None else {"cookies": [], "origins": []}
    context.cookies.side_effect = list(cookie_jar_sequence)
    context.storage_state.return_value = storage
    browser = MagicMock()
    browser.new_context.return_value = context
    page = MagicMock()
    context.new_page.return_value = page
    chromium = MagicMock()
    chromium.launch.return_value = browser
    pw = MagicMock()
    pw.chromium = chromium

    @contextmanager
    def fake_sync_playwright():
        yield pw

    return fake_sync_playwright, browser, page, context


def test_returns_cookies_when_success_cookie_appears():
    jars = [
        [],  # first poll — not signed in yet
        [{"name": "c_user", "value": "100012345"}, {"name": "xs", "value": "abc"}],
        # settle-window poll — same state
        [{"name": "c_user", "value": "100012345"}, {"name": "xs", "value": "abc"}],
    ]
    fake_pw, browser, page, _ = _make_playwright(jars, storage_state={"cookies": [{"name": "c_user"}]})
    result = open_login_window(
        "facebook",
        poll_seconds=0.0,
        timeout_seconds=5.0,
        settle_seconds=0.0,
        playwright_module=fake_pw,
    )
    assert result.cookies["c_user"] == "100012345"
    assert result.cookies["xs"] == "abc"
    assert result.storage_state == {"cookies": [{"name": "c_user"}]}
    page.goto.assert_called_once_with("https://www.facebook.com/")
    browser.close.assert_called_once()


def test_times_out_when_success_cookie_never_arrives():
    # `cookies()` keeps returning an empty jar forever.
    context = MagicMock()
    context.cookies.return_value = []
    context.storage_state.return_value = {"cookies": [], "origins": []}
    browser = MagicMock()
    browser.new_context.return_value = context
    context.new_page.return_value = MagicMock()
    chromium = MagicMock(); chromium.launch.return_value = browser
    pw = MagicMock(); pw.chromium = chromium

    @contextmanager
    def fake_sync_playwright():
        yield pw

    with pytest.raises(TimeoutError, match="c_user"):
        open_login_window(
            "facebook",
            poll_seconds=0.0,
            timeout_seconds=0.05,
            settle_seconds=0.0,
            playwright_module=fake_sync_playwright,
        )


def test_missing_playwright_raises_clear_install_message(monkeypatch):
    """When playwright isn't installed, surface a PlaywrightNotInstalled with install hint."""
    # Block the import so the lazy path falls through to the ImportError branch.
    import sys

    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    with pytest.raises(PlaywrightNotInstalled, match="pip install playwright"):
        open_login_window("facebook")


def test_different_vendor_uses_right_success_cookie():
    jars = [[{"name": "li_at", "value": "AbCdEf"}], [{"name": "li_at", "value": "AbCdEf"}]]
    fake_pw, _, page, _ = _make_playwright(jars)
    result = open_login_window(
        "linkedin",
        poll_seconds=0.0,
        timeout_seconds=5.0,
        settle_seconds=0.0,
        playwright_module=fake_pw,
    )
    assert result.cookies == {"li_at": "AbCdEf"}
    page.goto.assert_called_once_with("https://www.linkedin.com/login")
