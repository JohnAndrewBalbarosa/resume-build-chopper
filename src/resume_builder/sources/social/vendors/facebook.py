"""Facebook handler — mbasic.facebook.com via curl-impersonated GETs.

Requires `FB_COOKIE` env var formatted as `c_user=...; xs=...` (copy from a logged-in
browser DevTools Network tab). Without the cookie, the vendor returns empty results
rather than failing — the rest of the pipeline still produces a valid CV.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Iterable

from ..auth import Credentials, LoginError, LoginPrompt
from ..base import SocialVendor
from ..http import HttpClient
from ..models import SocialMention, SocialPost

log = logging.getLogger(__name__)

_BASE = "https://mbasic.facebook.com"
_POST_LINK_RE = re.compile(r'href="(/story\.php\?story_fbid=\d+[^"]*)"')
_TEXT_BLOCK_RE = re.compile(r"<p>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_AUTHOR_RE = re.compile(r"<strong[^>]*>([^<]+)</strong>")


def _parse_cookie_header(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for chunk in raw.split(";"):
        if "=" in chunk:
            k, v = chunk.strip().split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _strip_html(s: str) -> str:
    return _TAG_STRIP_RE.sub(" ", s).strip()


class FacebookVendor(SocialVendor):
    name = "facebook"

    def __init__(self, cookie_env: str = "FB_COOKIE") -> None:
        cookie_raw = os.environ.get(cookie_env, "")
        if not cookie_raw:
            log.warning("FB_COOKIE not set — Facebook vendor will return empty results.")
        self._client = HttpClient(cookies=_parse_cookie_header(cookie_raw))
        self._authenticated = bool(cookie_raw)

    # ---- public ----

    def fetch_own_posts(self, handle: str, limit: int = 50) -> list[SocialPost]:
        if not self._authenticated:
            return []
        try:
            html = self._get(f"{_BASE}/{handle}")
        except Exception as exc:  # noqa: BLE001
            log.warning("facebook fetch_own_posts failed: %s", exc)
            return []
        return list(self._parse_posts(html, owner=handle))[:limit]

    def search_mentions(self, full_name: str, limit: int = 50) -> list[SocialMention]:
        if not self._authenticated:
            return []
        try:
            html = self._get(f"{_BASE}/search/posts/", params={"q": full_name})
        except Exception as exc:  # noqa: BLE001
            log.warning("facebook search_mentions failed: %s", exc)
            return []
        return list(self._parse_mentions(html))[:limit]

    # ---- internals ----

    def _get(self, url: str, **kwargs: object) -> str:
        resp = self._client.get(url, **kwargs)
        return getattr(resp, "text", "") or ""

    def _parse_posts(self, html: str, owner: str) -> Iterable[SocialPost]:
        seen: set[str] = set()
        for link_match in _POST_LINK_RE.finditer(html):
            link = link_match.group(1)
            if link in seen:
                continue
            seen.add(link)
            window = html[link_match.start() : link_match.start() + 2000]
            text = self._extract_text(window)
            if not text:
                continue
            post_id_match = re.search(r"story_fbid=(\d+)", link)
            post_id = post_id_match.group(1) if post_id_match else link
            yield SocialPost(
                vendor=self.name,
                post_id=post_id,
                url=f"{_BASE}{link}",
                text=text,
            )

    def _parse_mentions(self, html: str) -> Iterable[SocialMention]:
        for block_match in _POST_LINK_RE.finditer(html):
            link = block_match.group(1)
            window = html[max(0, block_match.start() - 400) : block_match.start() + 2000]
            text = self._extract_text(window)
            if not text:
                continue
            author_match = _AUTHOR_RE.search(window)
            author = author_match.group(1) if author_match else ""
            post_id_match = re.search(r"story_fbid=(\d+)", link)
            mention_id = post_id_match.group(1) if post_id_match else link
            yield SocialMention(
                vendor=self.name,
                mention_id=mention_id,
                url=f"{_BASE}{link}",
                text=text,
                author_name=author,
            )

    @staticmethod
    def _extract_text(window: str) -> str:
        for m in _TEXT_BLOCK_RE.finditer(window):
            body = _strip_html(m.group(1))
            if len(body) > 12:
                return body
        return ""


_HIDDEN_RE = re.compile(r'<input[^>]+type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', re.IGNORECASE)
_CHECKPOINT_URL_RE = re.compile(r"https://[^\"' ]*checkpoint[^\"' ]*")


class FacebookLogin:
    """Facebook web login. mbasic.facebook.com is the friendliest surface for non-JS scripts.

    Realistic note: a fresh programmatic login from an unrecognized IP almost
    always lands on a checkpoint page that needs photo/identity verification —
    no console can answer that. Caller should fall back to ``browser_cookies``.
    """

    _LOGIN_PAGE = "https://mbasic.facebook.com/login.php"
    _LOGIN_SUBMIT = "https://mbasic.facebook.com/login/device-based/regular/login/"
    _CHECKPOINT_SUBMIT = "https://mbasic.facebook.com/login/checkpoint/"

    def __init__(self, client: HttpClient | None = None) -> None:
        self._client = client or HttpClient(min_interval_s=2.5)

    def run(self, creds: Credentials, prompt: LoginPrompt) -> dict[str, str]:
        hidden = self._fetch_form()
        hidden.update({"email": creds.username, "pass": creds.password, "login": "Log In"})
        resp = self._client.post(self._LOGIN_SUBMIT, data=hidden, allow_redirects=True)
        body = getattr(resp, "text", "") or ""
        url = getattr(resp, "url", "") or ""
        if "checkpoint" in url.lower() or "checkpoint" in body[:4000].lower():
            self._handle_checkpoint(body, prompt)
        cookies = self._extract_fb_cookies()
        if "c_user" not in cookies or "xs" not in cookies:
            raise LoginError(
                "facebook login: c_user / xs cookies not set — checkpoint likely; "
                "try browser_cookies fallback."
            )
        return cookies

    def _fetch_form(self) -> dict[str, str]:
        resp = self._client.get(self._LOGIN_PAGE)
        html = getattr(resp, "text", "") or ""
        return dict(_HIDDEN_RE.findall(html))

    def _handle_checkpoint(self, html: str, prompt: LoginPrompt) -> None:
        if "approvals_code" not in html and "2fa" not in html.lower():
            raise LoginError("facebook login: checkpoint requires browser (photo / identity check).")
        fields = dict(_HIDDEN_RE.findall(html))
        code = prompt.ask("Facebook: enter the 2FA code (authenticator / SMS)")
        fields["approvals_code"] = code
        fields["submit[Submit Code]"] = "Submit Code"
        self._client.post(self._CHECKPOINT_SUBMIT, data=fields, allow_redirects=True)

    def _extract_fb_cookies(self) -> dict[str, str]:
        jar = getattr(self._client, "cookies", None)
        if jar is None:
            return {}
        out: dict[str, str] = {}
        for c in jar:
            name = getattr(c, "name", None)
            value = getattr(c, "value", None)
            if name in ("c_user", "xs", "fr", "datr") and value:
                out[name] = value
        return out


def login_facebook(creds: Credentials, prompt: LoginPrompt) -> dict[str, str]:
    return FacebookLogin().run(creds, prompt)
