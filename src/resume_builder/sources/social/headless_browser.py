"""Playwright scrape session — visible Chromium by default, with scroll-to-load.

Despite the file name (kept for import-path stability), the default ``headless``
value is ``False``: the user sees the same Chromium that signed them in, navigating
their feed and pulling posts. Visible mode also reduces bot-detection noise that
fully-headless Chromium triggers on Facebook and LinkedIn.

A scroll helper drives infinite-scroll feeds so the scraper captures every post,
not just the first viewport.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from .auth import SessionStore
from .browser_login import PlaywrightNotInstalled, _resolve_playwright
from .playwright_debug import (
    highlight_selector,
    launch_options,
    pause,
    visual_debug_from_env,
)

log = logging.getLogger(__name__)


class NoStoredSessionError(RuntimeError):
    """Raised when ``storage_state.json`` for the requested vendor is missing.

    Callers can catch this and fall back to a curl-only path.
    """


@contextmanager
def PlaywrightSession(  # noqa: N802 - context-manager helper
    vendor: str,
    *,
    headless: bool = False,
    playwright_module=None,
    store: SessionStore | None = None,
    timeout_ms: int = 30_000,
) -> Iterator[object]:
    """Yield a Playwright ``page`` bound to the vendor's stored authenticated context."""
    store = store or SessionStore()
    state = store.load_storage_state(vendor)
    if state is None:
        raise NoStoredSessionError(
            f"No stored sign-in for {vendor}. Run `resume-build login` first."
        )
    sync_playwright = _resolve_playwright(playwright_module)
    visual_debug = visual_debug_from_env()

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_options(headless, visual_debug))
        try:
            context = browser.new_context(storage_state=state)
            context.set_default_timeout(timeout_ms)
            page = context.new_page()
            highlight_selector(page, "body", label=f"{vendor} session ready", debug=visual_debug)
            yield page
        finally:
            browser.close()


# Backwards-compatible alias for older imports.
HeadlessBrowser = PlaywrightSession


def scroll_collect(
    page,
    item_selector: str,
    *,
    max_scrolls: int = 60,
    settle_ms: int = 1500,
    no_growth_passes: int = 3,
) -> list:
    """Scroll the page until ``item_selector`` stops growing, then return all matches.

    ``max_scrolls`` is the hard cap on scroll cycles; ``no_growth_passes`` is how
    many consecutive scrolls with the same item count we tolerate before declaring
    the feed exhausted (Facebook sometimes lazy-loads with a small delay).
    """
    visual_debug = visual_debug_from_env()
    seen = 0
    flat = 0
    for _ in range(max_scrolls):
        highlight_selector(
            page,
            item_selector,
            label="items collected before scroll",
            debug=visual_debug,
        )
        items = page.query_selector_all(item_selector) or []
        if len(items) > seen:
            seen = len(items)
            flat = 0
        else:
            flat += 1
            if flat >= no_growth_passes:
                break
        try:
            page.evaluate("window.scrollBy(0, window.innerHeight * 0.9)")
            pause(page, debug=visual_debug)
        except Exception as exc:  # noqa: BLE001
            log.debug("scroll failed: %s", exc)
            break
        page.wait_for_timeout(settle_ms)
    highlight_selector(page, item_selector, label="final collected items", debug=visual_debug)
    return page.query_selector_all(item_selector) or []


def fetch_rendered_html(
    vendor: str,
    url: str,
    *,
    wait_for_selector: str | None = None,
    timeout_ms: int = 30_000,
    headless: bool = False,
    playwright_module=None,
    store: SessionStore | None = None,
) -> str:
    """Open ``url`` with the vendor's authenticated context, return the page HTML.

    Returns ``""`` on any internal failure so callers can check truthiness.
    """
    visual_debug = visual_debug_from_env()
    try:
        with PlaywrightSession(
            vendor,
            headless=headless,
            playwright_module=playwright_module,
            store=store,
            timeout_ms=timeout_ms,
        ) as page:
            page.goto(url, wait_until="domcontentloaded")
            highlight_selector(page, "body", label="loaded page", debug=visual_debug)
            if wait_for_selector:
                try:
                    highlight_selector(
                        page,
                        wait_for_selector,
                        label="wait target",
                        debug=visual_debug,
                    )
                    page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
                    highlight_selector(
                        page,
                        wait_for_selector,
                        label="wait target ready",
                        debug=visual_debug,
                    )
                except Exception as exc:  # noqa: BLE001
                    log.debug("wait_for_selector %s missed: %s", wait_for_selector, exc)
            return page.content() or ""
    except (NoStoredSessionError, PlaywrightNotInstalled):
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("Playwright fetch %s failed: %s", url, exc)
        return ""
