#!/usr/bin/env python3
"""Promote EVERY board task to a GitHub issue and sync all Project fields. Idempotent.

Model (the confirmed "full recipe"):
- Every task -> a real GitHub ISSUE (labelled, milestoned), added to the Project, all fields set.
- The matching draft card is deleted so the issue replaces it (dedupe by exact title).
- Assignee is set only where board_tasks.json says so (Done + this session's work).

Fields set per item: Status + Stage (both from `stage`), Role, Group, Department, HITL Gate,
Priority (single-selects); Start, Target, Worst Case (dates); Estimate (number). Milestone and
assignee are set on the issue itself.

Windows-safe: every gh call decodes UTF-8; dates/urls are \\r-stripped.

Usage:
    python scripts/issuesify_board.py                 # process ALL tasks
    python scripts/issuesify_board.py "Title A" ...   # only these titles (staged/test run)
Requires: gh authenticated with the `project` scope; labels, fields, milestones already created.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = "JohnAndrewBalbarosa/pytorch-fit-system"
HERE = Path(__file__).resolve().parent
CONFIG = HERE / "board_tasks.json"

# Project single-select field name -> task json key. Status (built-in, drives the default Board
# view) and Stage (custom) are both set from `stage` so any view groups correctly.
FIELD_KEY = {
    "Status": "stage",
    "Stage": "stage",
    "Role": "role",
    "Group": "group",
    "Department": "department",
    "HITL Gate": "hitl",
    "Priority": "priority",
}
DATE_KEY = {"Start": "start", "Target": "target", "Worst Case": "worst_case"}
NUMBER_KEY = {"Estimate": "estimate"}

DEPT_LABEL = {
    "Legacy Engine": "dept:legacy-engine",
    "Platform Core": "dept:platform-core",
    "Org Operations": "dept:org-operations",
    "Points & Leaderboard": "dept:points",
    "Data & DB": "dept:data-db",
    "AI & ML": "dept:ai-ml",
    "Frontend": "dept:frontend",
    "DevOps": "dept:devops",
    "Docs & Ops": "dept:docs-ops",
}


def gh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def gh_project_json(args: list[str]):
    r = gh([*args, "--format", "json"])
    if r.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed:\n{r.stderr}")
    return json.loads(r.stdout)


def issue_body(task: dict) -> str:
    seed = (
        "Before coding, restate the goal in your own words, list the exact files you'll touch, "
        "and surface any assumption that, if wrong, changes the approach."
    )
    return (
        f"{task.get('body', '').strip()}\n\n"
        "---\n"
        f"**Department:** {task.get('department', '—')} · **HITL Gate:** {task.get('hitl', 'No')} "
        f"· **Priority:** {task.get('priority', '—')} · **Estimate:** {task.get('estimate', '?')}d\n"
        f"**Reverse-prompt seed:** {seed}\n"
        "_Boundary: stay within the files in Scope; if the change spills outside, stop and flag it._"
    )


def labels_for(task: dict) -> list[str]:
    out = ["delegation", DEPT_LABEL.get(task.get("department", ""), "dept:platform-core")]
    if task.get("hitl") == "Yes":
        out.append("hitl")
    if task.get("group") == "Model Training":
        out.append("model-training")
    return out


def set_fields(item_id: str, project_id: str, fmap: dict, opts: dict, task: dict) -> None:
    for fname, key in FIELD_KEY.items():
        value = task.get(key)
        if not value:
            continue
        opt_id = opts[fname].get(value)
        if opt_id is None:
            print(f"  ! unknown {fname} {value!r}")
            continue
        gh(["project", "item-edit", "--id", item_id, "--project-id", project_id,
            "--field-id", fmap[fname]["id"], "--single-select-option-id", opt_id])
    for fname, key in DATE_KEY.items():
        value = (task.get(key) or "").strip()
        if value:
            gh(["project", "item-edit", "--id", item_id, "--project-id", project_id,
                "--field-id", fmap[fname]["id"], "--date", value])
    for fname, key in NUMBER_KEY.items():
        value = task.get(key)
        if value is not None:
            gh(["project", "item-edit", "--id", item_id, "--project-id", project_id,
                "--field-id", fmap[fname]["id"], "--number", str(value)])


def main() -> None:
    only = set(sys.argv[1:])
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    owner, num = cfg["owner"], str(cfg["project_number"])

    project_id = gh_project_json(["project", "view", num, "--owner", owner])["id"]
    fields = gh_project_json(["project", "field-list", num, "--owner", owner])["fields"]
    fmap = {f["name"]: f for f in fields}
    for name in [*FIELD_KEY, *DATE_KEY, *NUMBER_KEY]:
        if name not in fmap:
            sys.exit(f"field {name!r} missing on the project")
    opts = {n: {o["name"]: o["id"] for o in fmap[n].get("options", [])} for n in FIELD_KEY}

    items = gh_project_json(
        ["project", "item-list", num, "--owner", owner, "--limit", "300"]
    )["items"]
    draft_by_title: dict[str, str] = {}
    issue_item_by_title: dict[str, str] = {}
    for it in items:
        c = it.get("content") or {}
        title = c.get("title") or it.get("title")
        if c.get("type") == "DraftIssue":
            draft_by_title.setdefault(title, it["id"])
        else:
            issue_item_by_title.setdefault(title, it["id"])

    r = gh(["issue", "list", "--repo", REPO, "--state", "all", "--limit", "400",
            "--json", "number,title,url"])
    existing = {i["title"]: i for i in json.loads(r.stdout or "[]")}

    created = reused = pruned = 0
    for task in cfg["tasks"]:
        title = task["title"]
        if only and title not in only:
            continue

        issue = existing.get(title)
        if issue is None:
            label_args: list[str] = []
            for lb in labels_for(task):
                label_args += ["--label", lb]
            rc = gh(["issue", "create", "--repo", REPO, "--title", title,
                     "--body", issue_body(task), *label_args])
            url = (rc.stdout or "").strip().splitlines()[-1] if rc.returncode == 0 else ""
            if not url.startswith("http"):
                print(f"  ! issue create failed: {title}: {rc.stderr.strip()[:120]}")
                continue
            number = url.rstrip("/").split("/")[-1]
            created += 1
        else:
            url, number = issue["url"], str(issue["number"])
            reused += 1

        # milestone + assignee live on the issue itself
        edit = ["issue", "edit", number, "--repo", REPO]
        if task.get("milestone"):
            edit += ["--milestone", task["milestone"]]
        if task.get("assignee"):
            edit += ["--add-assignee", task["assignee"]]
        if len(edit) > 4:
            gh(edit)

        item_id = issue_item_by_title.get(title)
        if item_id is None:
            rc = gh(["project", "item-add", num, "--owner", owner, "--url", url, "--format", "json"])
            if rc.returncode != 0:
                print(f"  ! item-add failed: {title}: {rc.stderr.strip()[:100]}")
                continue
            item_id = json.loads(rc.stdout)["id"]
        set_fields(item_id, project_id, fmap, opts, task)

        draft_id = draft_by_title.get(title)
        if draft_id:
            if gh(["project", "item-delete", num, "--owner", owner, "--id", draft_id]).returncode == 0:
                pruned += 1
        print(f"  {'NEW' if issue is None else 'set'}  {title[:58]}")

    print(f"\n{created} issues created, {reused} reused, {pruned} drafts pruned, {len(cfg['tasks'])} total")


if __name__ == "__main__":
    main()
