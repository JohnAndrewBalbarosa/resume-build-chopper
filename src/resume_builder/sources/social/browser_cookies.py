"""Local-browser cookie import — the friction-free fallback when programmatic login fails.

Uses ``browser_cookie3`` if installed. The user signs in normally on their machine
(2FA, biometric, password manager all work) and we read the cookie jar that was
written by their browser. No password ever passes through this code.

If ``browser_cookie3`` is not installed, ``import_cookies`` returns ``None`` so callers
can degrade to an error message.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Map vendor -> browser cookie domain we need to extract from.
_DOMAINS: dict[str, str] = {
    "facebook": ".facebook.com",
    "linkedin": ".linkedin.com",
    "twitter": ".twitter.com",  # x.com cookies typically also live under .twitter.com
    "instagram": ".instagram.com",
}


def import_cookies(vendor: str, browser: str = "auto") -> dict[str, str] | None:
    """Pull cookies for ``vendor`` from the local browser store.

    ``browser`` is one of: auto, chrome, edge, firefox, brave, opera. ``auto`` tries
    each in turn and returns the first non-empty result.
    """
    try:
        import browser_cookie3 as bc  # type: ignore[import-not-found]
    except ImportError:
        log.info("browser_cookie3 not installed — cannot import browser cookies.")
        return None

    domain = _DOMAINS.get(vendor)
    if domain is None:
        log.warning("no browser-cookie domain mapping for vendor %s", vendor)
        return None

    loaders: list[tuple[str, callable]] = [
        ("chrome", bc.chrome),
        ("edge", bc.edge),
        ("firefox", bc.firefox),
        ("brave", bc.brave),
        ("opera", bc.opera),
    ]
    if browser != "auto":
        loaders = [(n, fn) for n, fn in loaders if n == browser]

    for name, fn in loaders:
        try:
            jar = fn(domain_name=domain.lstrip("."))
            out = {c.name: c.value for c in jar if c.value}
            if out:
                log.info("loaded %d cookies for %s from %s", len(out), vendor, name)
                return out
        except Exception as exc:  # noqa: BLE001 - any per-browser failure is fine
            log.debug("browser %s lookup failed for %s: %s", name, vendor, exc)
    return None
