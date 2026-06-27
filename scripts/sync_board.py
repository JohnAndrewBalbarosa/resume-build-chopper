#!/usr/bin/env python3
"""Idempotent sync of the GitHub Project board from scripts/board_tasks.json.

Why: GitHub does NOT let you create a Project *view* (the Board/kanban layout) via API
— that's a one-time UI click. Everything else (items, Stage, Role, Group, bodies) is fully
scriptable. This script is the lazy path: edit board_tasks.json, run this, the board matches.

Idempotent + authoritative:
- items matched by title (no duplicates ever).
- missing items created; every run re-sets the configured single-select fields.
- with --prune, board items whose title is NOT in the JSON are deleted, so the JSON is the
  single source of truth.

Single-select field + option IDs are discovered by NAME at runtime, so this keeps working
even if the project / fields are recreated.

Usage:
    python scripts/sync_board.py            # create + update
    python scripts/sync_board.py --prune    # also delete board items not in the JSON
Requires: gh CLI authenticated with the `project` scope.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "board_tasks.json"


def gh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def gh_json(args: list[str]):
    r = gh([*args, "--format", "json"])
    if r.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed:\n{r.stderr}")
    return json.loads(r.stdout)


def main() -> None:
    prune = "--prune" in sys.argv[1:]
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    owner = cfg["owner"]
    num = str(cfg["project_number"])
    # Names of the single-select fields to set on each item, e.g. ["Stage","Role","Group"].
    select_fields: list[str] = cfg.get("select_fields", ["Stage", "Role"])
    # Names of DATE fields to set, e.g. ["Start","Target"]. Task keys are the lowercased name.
    date_fields: list[str] = cfg.get("date_fields", [])

    project_id = gh_json(["project", "view", num, "--owner", owner])["id"]

    fields = gh_json(["project", "field-list", num, "--owner", owner])["fields"]
    fmap = {f["name"]: f for f in fields}
    for name in [*select_fields, *date_fields]:
        if name not in fmap:
            sys.exit(f"field {name!r} not found on the project (create it first)")

    def options(field_name: str) -> dict[str, str]:
        return {o["name"]: o["id"] for o in fmap[field_name].get("options", [])}

    field_ids = {name: fmap[name]["id"] for name in select_fields}
    field_opts = {name: options(name) for name in select_fields}

    existing = gh_json(["project", "item-list", num, "--owner", owner, "--limit", "300"])["items"]
    by_title: dict[str, str] = {}
    for it in existing:
        title = (it.get("content") or {}).get("title") or it.get("title")
        by_title.setdefault(title, it["id"])

    desired_titles = {t["title"] for t in cfg["tasks"]}
    created = updated = 0

    for task in cfg["tasks"]:
        title = task["title"]
        item_id = by_title.get(title)
        if item_id is None:
            r = gh(["project", "item-create", num, "--owner", owner, "--title", title,
                    "--body", task.get("body", ""), "--format", "json"])
            if r.returncode != 0:
                print(f"  ! create failed: {title}: {r.stderr.strip()[:120]}"); continue
            item_id = json.loads(r.stdout)["id"]
            created += 1; tag = "NEW"
        else:
            updated += 1; tag = "set"

        labels = []
        for fname in select_fields:
            value = task.get(fname.lower())
            if value is None:
                continue
            opt_id = field_opts[fname].get(value)
            if opt_id is None:
                print(f"  ! unknown {fname} {value!r} for {title!r}"); continue
            gh(["project", "item-edit", "--id", item_id, "--project-id", project_id,
                "--field-id", field_ids[fname], "--single-select-option-id", opt_id])
            labels.append(value)

        for fname in date_fields:
            value = task.get(fname.lower())
            if not value:
                continue
            gh(["project", "item-edit", "--id", item_id, "--project-id", project_id,
                "--field-id", fmap[fname]["id"], "--date", value])
        dates = " ".join(task.get(f.lower(), "") for f in date_fields).strip()
        print(f"  {tag:3} {' / '.join(labels):42} {dates:23} {title[:46]}")

    pruned = 0
    if prune:
        for title, item_id in by_title.items():
            if title not in desired_titles:
                r = gh(["project", "item-delete", num, "--owner", owner, "--id", item_id])
                if r.returncode == 0:
                    pruned += 1; print(f"  del {title[:60]}")

    print(f"\nsynced: {created} created, {updated} updated, {pruned} pruned, {len(cfg['tasks'])} total")


if __name__ == "__main__":
    main()
