"""GitHub source via the `gh` CLI (assumed installed + authenticated).

Subprocess access is encapsulated behind `_gh_json` so tests can mock a single seam.
"""

from __future__ import annotations

import base64
import json
import logging
import shutil
import subprocess
from typing import Any

from ..models import Repo
from .base import SourceCollector

log = logging.getLogger(__name__)

_REPO_FIELDS = "name,nameWithOwner,url,description,primaryLanguage,languages,repositoryTopics,stargazerCount,isArchived"


class GitHubCliNotFoundError(RuntimeError):
    pass


class GitHubSource(SourceCollector):
    name = "github"

    def __init__(self, gh_binary: str = "gh") -> None:
        if shutil.which(gh_binary) is None:
            raise GitHubCliNotFoundError(
                f"`{gh_binary}` CLI not found on PATH. Install it from https://cli.github.com/"
            )
        self._gh = gh_binary

    # ------- public API -------

    def collect(self, user: str, limit: int = 100, include_readme: bool = True) -> list[Repo]:
        """Fetch all repos for `user`, optionally hydrating README content."""
        raw = self._list_repos(user, limit=limit)
        repos = [self._normalize_repo(r) for r in raw]
        if include_readme:
            for repo in repos:
                repo.readme = self._fetch_readme(repo.full_name)
        return repos

    # ------- internals (single subprocess seam) -------

    def _gh_json(self, args: list[str]) -> Any:
        try:
            result = subprocess.run(
                [self._gh, *args],
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
            )
        except subprocess.CalledProcessError as exc:
            log.warning("gh command failed: %s | stderr=%s", args, exc.stderr.strip())
            raise
        return json.loads(result.stdout) if result.stdout.strip() else None

    def _list_repos(self, user: str, limit: int) -> list[dict]:
        return self._gh_json(
            ["repo", "list", user, "--limit", str(limit), "--json", _REPO_FIELDS]
        ) or []

    def _fetch_readme(self, full_name: str) -> str | None:
        try:
            data = self._gh_json(["api", f"repos/{full_name}/readme"])
        except subprocess.CalledProcessError:
            return None
        if not data or "content" not in data:
            return None
        try:
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalize_repo(raw: dict) -> Repo:
        languages = raw.get("languages") or []
        if languages and isinstance(languages[0], dict):
            languages = [lang.get("node", {}).get("name") or lang.get("name") for lang in languages]
        languages = [l for l in languages if l]
        primary = raw.get("primaryLanguage")
        if primary and isinstance(primary, dict):
            primary_name = primary.get("name")
            if primary_name and primary_name not in languages:
                languages.insert(0, primary_name)
        topics_raw = raw.get("repositoryTopics") or []
        topics = [t.get("name") if isinstance(t, dict) else t for t in topics_raw]
        topics = [t for t in topics if t]
        return Repo(
            name=raw.get("name", ""),
            full_name=raw.get("nameWithOwner") or raw.get("name", ""),
            url=raw.get("url", ""),
            description=raw.get("description"),
            languages=languages,
            topics=topics,
            stars=raw.get("stargazerCount") or 0,
            archived=bool(raw.get("isArchived")),
        )
