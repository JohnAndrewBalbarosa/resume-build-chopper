"""Facebook handler.

Two scrape paths, picked at runtime:

1. **Headless Playwright** using the ``storage_state.json`` written during sign-in.
   Hits real ``www.facebook.com`` URLs as the authenticated user — full React feed,
   not the mobile-basic fallback. This is the path the user explicitly chose when
   they ran ``resume-build login``.

2. **mbasic.facebook.com via curl** with cookies — kept as a fallback for users who
   only have cookies (env var / DevTools paste) and never ran the Playwright sign-in.

Vendors return ``[]`` cleanly when neither path is usable.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Iterable

from ..auth import Credentials, LoginError, LoginPrompt, SessionStore, resolve_session_cookies
from ..base import SocialVendor
from ..headless_browser import (
    NoStoredSessionError,
    PlaywrightSession,
    fetch_rendered_html,
    scroll_collect,
)
from ..http import HttpClient
from ..models import SocialMention, SocialPost

log = logging.getLogger(__name__)

_BASE = "https://mbasic.facebook.com"
_POST_LINK_RE = re.compile(r'href="(/story\.php\?story_fbid=\d+[^"]*)"')
_TEXT_BLOCK_RE = re.compile(r"<p>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_AUTHOR_RE = re.compile(r"<strong[^>]*>([^<]+)</strong>")


def _snapshot_article(element) -> dict:
    """Extract a stable plain-dict snapshot of a single FB article element.

    The snapshot keeps everything we need (text, url, author, post_id) so the
    Playwright page can close before parsing — avoiding stale-handle errors.
    """
    text = (element.inner_text() or "").strip()
    href = ""
    author = ""
    try:
        # FB renders post permalinks as anchors carrying /posts/ or /permalink/ paths.
        anchor = element.query_selector('a[href*="/posts/"], a[href*="/permalink/"]')
        if anchor:
            href = anchor.get_attribute("href") or ""
    except Exception:  # noqa: BLE001
        pass
    try:
        # Author name lives in the post header strong/h-style element.
        author_el = element.query_selector("strong, h2, h3")
        if author_el:
            author = (author_el.inner_text() or "").strip().splitlines()[0]
    except Exception:  # noqa: BLE001
        pass

    if href.startswith("/"):
        href = f"https://www.facebook.com{href}"
    post_id = ""
    if href:
        post_id = href.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
    if not post_id:
        post_id = f"render-{hash(text) & 0xFFFFFF}"

    return {"post_id": post_id, "url": href, "author": author, "text": text[:1000]}


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

    def __init__(
        self,
        cookies: dict[str, str] | None = None,
        *,
        prefer_headless: bool = True,
        session_store: SessionStore | None = None,
    ) -> None:
        resolved = cookies if cookies is not None else resolve_session_cookies("facebook")
        if not resolved:
            log.warning(
                "Facebook vendor has no cookies (env FB_COOKIE / session store / "
                "browser jar all empty) — curl fallback will return []."
            )
        self._client = HttpClient(cookies=resolved)
        self._authenticated = bool(resolved)
        self._prefer_headless = prefer_headless
        self._store = session_store or SessionStore()
        # Cache the storage_state presence so we don't hit disk on every call.
        self._has_storage_state = self._store.load_storage_state("facebook") is not None

    # ---- public ----

    def fetch_own_posts(self, handle: str, limit: int = 50) -> list[SocialPost]:
        if self._prefer_headless and self._has_storage_state:
            posts = self._headless_own_posts(handle, limit)
            if posts:
                return posts
            log.info("headless FB own-posts returned empty; falling back to mbasic curl.")
        if not self._authenticated:
            return []
        try:
            html = self._get(f"{_BASE}/{handle}")
        except Exception as exc:  # noqa: BLE001
            log.warning("facebook mbasic fetch_own_posts failed: %s", exc)
            return []
        return list(self._parse_posts(html, owner=handle))[:limit]

    def search_mentions(self, full_name: str, limit: int = 50) -> list[SocialMention]:
        if self._prefer_headless and self._has_storage_state:
            mentions = self._headless_search_mentions(full_name, limit)
            if mentions:
                return mentions
            log.info("headless FB mentions returned empty; falling back to mbasic curl.")
        if not self._authenticated:
            return []
        try:
            html = self._get(f"{_BASE}/search/posts/", params={"q": full_name})
        except Exception as exc:  # noqa: BLE001
            log.warning("facebook mbasic search_mentions failed: %s", exc)
            return []
        return list(self._parse_mentions(html))[:limit]

    # ---- playwright scrape path (visible Chromium + scroll-to-load) ----

    def _headless_own_posts(self, handle: str, limit: int) -> list[SocialPost]:
        url = f"https://www.facebook.com/{handle}"
        try:
            articles = self._scrape_articles(url, max_scrolls=60)
        except NoStoredSessionError:
            return []
        posts = list(self._articles_to_posts(articles, profile_url=url))
        return posts[:limit] if limit else posts

    def _headless_search_mentions(
        self, full_name: str, limit: int
    ) -> list[SocialMention]:
        from urllib.parse import quote_plus

        url = f"https://www.facebook.com/search/posts/?q={quote_plus(full_name)}"
        try:
            articles = self._scrape_articles(url, max_scrolls=30)
        except NoStoredSessionError:
            return []
        mentions = list(self._articles_to_mentions(articles, query_url=url, full_name=full_name))
        return mentions[:limit] if limit else mentions

    def _scrape_articles(self, url: str, *, max_scrolls: int) -> list[dict]:
        """Drive a visible Chromium to ``url``, scroll until the feed stops growing,
        and snapshot each article into a plain dict so the page can close before parsing.
        """
        records: list[dict] = []
        with PlaywrightSession(
            "facebook", headless=False, store=self._store
        ) as page:
            page.goto(url, wait_until="domcontentloaded")
            try:
                page.wait_for_selector("div[role='main']", timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                log.warning("FB main feed never rendered at %s: %s", url, exc)
                return []
            articles = scroll_collect(
                page,
                "div[role='article']",
                max_scrolls=max_scrolls,
            )
            log.info("FB scrape captured %d articles at %s", len(articles), url)
            for art in articles:
                try:
                    records.append(_snapshot_article(art))
                except Exception as exc:  # noqa: BLE001
                    log.debug("article snapshot failed: %s", exc)
        return records

    @staticmethod
    def _articles_to_posts(
        records: list[dict], profile_url: str
    ) -> Iterable[SocialPost]:
        seen_ids: set[str] = set()
        for rec in records:
            post_id = rec["post_id"]
            if post_id in seen_ids:
                continue
            if not rec["text"]:
                continue
            seen_ids.add(post_id)
            yield SocialPost(
                vendor="facebook",
                post_id=post_id,
                url=rec["url"] or profile_url,
                text=rec["text"],
            )

    @staticmethod
    def _articles_to_mentions(
        records: list[dict], query_url: str, full_name: str
    ) -> Iterable[SocialMention]:
        name_lower = full_name.lower()
        seen_ids: set[str] = set()
        for rec in records:
            mention_id = rec["post_id"]
            text = rec["text"]
            if not text or mention_id in seen_ids:
                continue
            # Only treat as a mention if the searched name actually appears in
            # the post body — FB's search returns ambient noise too.
            if name_lower not in text.lower():
                continue
            seen_ids.add(mention_id)
            yield SocialMention(
                vendor="facebook",
                mention_id=mention_id,
                url=rec["url"] or query_url,
                text=text,
                author_name=rec["author"],
            )

    @staticmethod
    def _parse_rendered_posts(html: str, profile_url: str) -> Iterable[SocialPost]:
        """Pull post text out of the rendered React feed.

        FB posts on the modern site live inside ``<div role="article">`` blocks; we
        snapshot the inner text and use the article anchor's ``href`` as the post id.
        """
        if not html:
            return
        article_re = re.compile(
            r'role="article"[^>]*>(.*?)(?=role="article"|</body>)',
            re.IGNORECASE | re.DOTALL,
        )
        href_re = re.compile(r'href="(/[^"]*?/posts/[^"]+|/permalink/\d+[^"]*)"')
        for match in article_re.finditer(html):
            block = match.group(1)
            href_m = href_re.search(block)
            text = _strip_html(block)[:600]
            if not text:
                continue
            link = href_m.group(1) if href_m else ""
            post_id = link.rsplit("/", 1)[-1].split("?")[0] if link else f"render-{hash(text) & 0xFFFFFF}"
            yield SocialPost(
                vendor="facebook",
                post_id=post_id,
                url=f"https://www.facebook.com{link}" if link else profile_url,
                text=text,
            )

    @staticmethod
    def _parse_rendered_mentions(html: str, query_url: str) -> Iterable[SocialMention]:
        if not html:
            return
        article_re = re.compile(
            r'role="article"[^>]*>(.*?)(?=role="article"|</body>)',
            re.IGNORECASE | re.DOTALL,
        )
        href_re = re.compile(r'href="(/[^"]*?/posts/[^"]+|/permalink/\d+[^"]*)"')
        author_re = re.compile(r'<strong[^>]*>([^<]{1,80})</strong>')
        for match in article_re.finditer(html):
            block = match.group(1)
            href_m = href_re.search(block)
            author_m = author_re.search(block)
            text = _strip_html(block)[:600]
            if not text:
                continue
            link = href_m.group(1) if href_m else ""
            mention_id = (
                link.rsplit("/", 1)[-1].split("?")[0]
                if link
                else f"render-{hash(text) & 0xFFFFFF}"
            )
            yield SocialMention(
                vendor="facebook",
                mention_id=mention_id,
                url=f"https://www.facebook.com{link}" if link else query_url,
                text=text,
                author_name=(author_m.group(1).strip() if author_m else ""),
            )

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
