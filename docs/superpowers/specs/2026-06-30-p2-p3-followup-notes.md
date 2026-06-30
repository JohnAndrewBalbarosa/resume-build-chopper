# P2 / P3 follow-up notes (user feedback, 2026-06-30)

Captured mid-build so they are not lost. These refine the already-merged P2 and shape the
not-yet-built P3 (Interpretation & Tagging). Not implemented yet — inputs for the next plan.

## 1. Scan depth becomes a USER-FACING 3-way option

The earlier P2 decision (README-only default + optional deep code) is refined into an explicit
**user-selectable** choice, picked according to the capability of the model the user supplies:

| Option | What gets fed to the model | For |
|---|---|---|
| `readme` (default, lightest) | the main/root README only | weak or no AI / smallest token budget |
| `markdown` | all markdown docs in the repo (README.* + docs/*.md) | mid capability |
| `code` | all relevant code too (broad source sweep) | strong models / richest context |

- **Why:** give importance to people who don't have much AI capability — the lightest option keeps
  token cost low and still works on small/free models. The heavier options are opt-in for stronger
  models.
- `collect_repo_markdown` already implements the `markdown` tier; `readme`-only is a trivial subset;
  the `code` tier is the deferred broad-source-sweep (`collect_repo_code`).
- Surface: a CLI flag / API param now (developer option); a real product UI toggle later.

## 2. P3 architecture — parallel per-project tagging agents

In the actual interpretation pipeline, do NOT send all projects to one big call. Instead:

- **One agent per project** — each agent summarizes its single project and emits that project's
  JSON (industries, skill_subtags, quantitative/qualitative impact, component-level bullets).
- **Run them in parallel** (fan-out) — independent, so wall-clock = slowest single project.
- **Compile, do NOT aggregate** — once all per-project JSONs return, simply concatenate/combine
  them into one structure the system can parse. No cross-project merging or summarization at this
  step; keep each project's result intact for easy downstream parsing.
- Benefit: scales to many repos, isolates context per project (cheaper/cleaner prompts), and avoids
  one giant prompt. Fits the per-source `CleanedSource` output of P2 one-to-one.
- **Request/response reconciliation checker.** Track how many per-project requests were **sent** vs how
  many **came back** (a dispatched-vs-returned counter). Two uses:
  - **Developer KPI reporting** — surface `sent / returned / failed`, success rate, and timing so devs
    can see throughput and reliability of the parallel fan-out.
  - **Retry detection** — the gap (sent minus returned) names exactly which projects did not respond
    (timeout / error / dropped); re-request only those, with a bounded retry count, then report any
    that still fail. Never silently drop a project — an unreturned request is a tracked miss, not a
    success.

## 3. Refactor + folder-structure segregation by functionality

- Refactor refactorable code into **functionally-segregated folders** — one folder per concept/theory.
- Model the segregation on the existing **botting folder** pattern: the whole idea/concept lives in a
  single self-contained folder. One-folder-per-concept is the target; a single cohesive folder is fine.
- Apply when touching code that has grown tangled; keep each concept's code together.

## 4. Compile pipeline = the retrieval MIDDLEMAN for ALL sources (+ PDF upload, no OCR)

Reframe the P3 "compile" step from "concatenate the per-project tagging JSONs" into the **single
middleman that gathers every retrieved input** and routes it. All retrieval flows through it.

- **Sources it gathers** (one typed envelope each):
  - `project` — GitHub repos via P2 `gather_repo_sources` (depth `readme`/`markdown`/`code`).
  - `post` — social posts (Profile Scraper Agent) and arbitrary websites (P2 skeleton pass).
  - `document` — **user-uploaded PDF/DOCX/TXT** from the UI. **Text-based → NO OCR**; extract text
    directly via the existing `DocumentSource` (pypdf / python-docx). A "PDF upload / scanner"
    control on the UI side feeds these in.
- **Routing after compile:**
  - `project` + `post` → the parallel per-project / per-post **tagging** agents (industries + skills).
  - `document` → candidate context (contact / experience / education / skills) consumed by P4 synth;
    may also surface taggable achievements.
- **Why middleman:** one place owns retrieval + normalization into a common shape, so tagging and
  assembly depend on the envelope, not on each source's quirks. Uploaded docs become a first-class
  source alongside GitHub and social — no special-casing downstream.

> Status: notes only. Fold #1 into a P2 follow-up task (scan-depth option + `collect_repo_code`,
> partly shipped 2026-06-30), and #2/#3/#4 into the P3 (Interpretation & Tagging) spec.
