# Org Activity Operations Layer — DRAFT (requirements capture)

> ⚠️ **STATUS: WORK IN PROGRESS.** This captures a live requirements dump so nothing is lost.
> The user said *"meron pa"* (more coming) — do NOT build or finalize board items from this yet.
> Pending from user: (1) the rest of the requirements, (2) a **document template**, (3) sign-off
> on the structure below. Once complete, fold into `SPECIFICATION.md` + the board.

This layer extends the PyTorch FIT System from a personal career platform into an **operations
platform for the PyTorch FEU Tech chapter** — running the org's real activities (emails,
documents, posting, officer accountability).

---

## 1. Activity / documentation taxonomy

All documentation is organized by **category × audience scope**:

| Category | Internal | External |
|---|---|---|
| Events | ✓ | ✓ |
| Workshops | ✓ | ✓ |
| Hackathons | ✓ | ✓ |
| Competitive Programming | ✓ | ✓ |

- **Internal** = for officers/members of the chapter.
- **External** = for outside parties (partners, sponsors, other orgs, the public).
- Each document is tagged with `category` + `scope` so pipelines route correctly.

```mermaid
flowchart TD
    Doc[Document] --> Cat{Category}
    Cat --> E[Events]
    Cat --> W[Workshops]
    Cat --> H[Hackathons]
    Cat --> C[Competitive Programming]
    E & W & H & C --> Scope{Scope}
    Scope --> Int[Internal]
    Scope --> Ext[External]
```

---

## 2. Intake → pipeline trigger

**Anyone** can start a pipeline by submitting a link or details about an (e.g. external) event.

```mermaid
flowchart LR
    Anyone[Any member submits link/details] --> Intake[Intake form/endpoint]
    Intake --> Classify[AI: classify category + scope]
    Classify --> Route[Route to the right pipeline]
    Route --> DocPipe[Document pipeline]
    Route --> EmailPipe[Email pipeline]
    Route --> PostPipe[Posting pipeline]
```

Open question: who can submit (any member vs authenticated only), and what's the minimum payload
(just a URL? URL + notes?).

---

## 3. Document injector (scaffold needed)

Generate documents from structured data — **JSON or SQL** (the platform will have a database) —
into a **user-provided template**.

- Input: a record (JSON now; SQL rows once the DB exists) + a template.
- Output: a rendered document (format TBD — DOCX? PDF? Google Doc? — awaiting template).
- This mirrors the legacy `renderers/` pattern (data + template → file), now for org docs.

> **Blocked on:** the template the user will provide. Until then, scaffold only the injector
> shape (input schema + template slot + renderer interface), not the concrete template.

---

## 4. Email pipeline (HITL required)

Pipelined sending of emails tied to activities.

```mermaid
flowchart LR
    Trigger[Activity / intake] --> Draft[AI drafts email]
    Draft --> Recipients[Resolve WHO to email]
    Recipients --> Review[[Human validator confirms]]
    Review -->|approve| Send[Send]
    Review -->|edit| Draft
```

- **AI only drafts/generates** — a human **must confirm before send** (hard gate).
- Needs a way to determine **recipients** ("kung sino-sino ang ee-email") — per category/scope,
  or derived from the intake submission.
- Open: which email surface (Gmail API already connected? org mailing lists?).

---

## 5. Social posting pipeline (Facebook page)

Pipelined posting to the chapter's **Facebook page** — e.g. "happening now" announcements.

```mermaid
flowchart LR
    Event[Activity update] --> Gen[AI drafts post + media]
    Gen --> Approve[[Human validator confirms]]
    Approve -->|ok| Post[Publish to FB page]
```

- Same principle: **AI generates, human validates** before publishing.
- Open: FB Page Graph API access + page token; reuse anything from the legacy scraper? (No —
  posting needs the Pages API, different from scraping.)

---

## 6. Officer scoring / accountability

Score officers on the tasks they complete.

- **Speed**: how fast they respond / close a task.
- **Quality**: **vote-based** (peers/officers vote), not auto-judged by AI.
- Ties into the board: a "Done" task by an officer feeds their score.
- Open: scoring formula, who can vote, anti-gaming, visibility (private vs leaderboard).

---

## 7. Human-in-the-loop principle (reaffirmed)

> The AI **only generates and eases document/communication work**. It never sends an email,
> publishes a post, or finalizes a quality score on its own. A human validator confirms:
> - every **email** before send,
> - every **quality** score (vote-based).

---

## 8. Open questions to resolve before building

1. Document **template(s)** + target output format(s). *(user will provide)*
2. Email surface (Gmail API / org mail) + recipient resolution rules.
3. Facebook **Page** API access + token for posting.
4. Intake: who can submit, minimum payload, auth.
5. Officer scoring formula + voting rules + visibility.
6. "meron pa" — remaining requirements from the user.

---

## 8b. CONFIRMED pipeline design (v1) — reverse-prompted & approved

> Locked with the user. Decisions below drive the eventual build.

**The flow (corrected — RAG = ingest the submitted link, not classify):**

```mermaid
flowchart TD
    A[Member submits a LINK or details<br/>e.g. a competition to join] --> B[Ingest / RAG:<br/>extract + understand the link's context]
    B --> C[Router: configurable rules table<br/>doc type + scope -> required departments]
    C --> D[Per-department brief generator:<br/>compacted context + prompt PER paper<br/>e.g. secretary: to whom + what content]
    D --> E[Each department/officer generates<br/>+ finalizes its paper AI-assisted]
    E --> F[Approval middleman dispatches to<br/>all required departments in PARALLEL]
    F -->|all must approve - unanimous| G[Approved]
    F -->|edit/reject| D
    G --> H[Auto-trigger downstream:<br/>email + FB posting pipelines]
    H --> I[[each still has its own HITL<br/>confirm before send/post]]
```

**Locked decisions:**

1. **Ingestion (RAG):** the AI's RAG step is to **read the submitted link** (e.g. a competition
   page) and extract its context — sometimes this is needed because it must be endorsed/approved
   by school officials. RAG is *content ingestion*, not pipeline classification.
2. **Per-department brief generation:** using that context, the system produces a **compacted
   brief + prompt for each concerned department / each paper** (e.g. the secretary gets: for whom
   the paper is, what its content should be). Officers still generate/finalize the actual papers,
   AI-assisted.
3. **Routing source = configurable rules table** (admin-editable: doc type/scope → required
   approvers). Changeable without a code change.
4. **Approval semantics = parallel, unanimous** — all required departments see it at once and
   ALL must approve before proceeding.
5. **Post-approval = auto-trigger downstream** (email + FB posting), but **each downstream action
   keeps its own HITL** confirm before send/post.

**Code shape (separation of concern):**
- `LinkIngestor` (RAG over the submitted URL/details) → `ActivityContext`
- `DepartmentBriefGenerator` → per-department `{recipient, required_content, draft}`
- `RoutingRules` (config/DB table) → `required_departments`
- `ApprovalMiddleman` + registry of `DepartmentApprover` (secretariat, treasurer, …) — parallel dispatch, collect verdicts
- Downstream `EmailSender` / `Poster` behind interfaces, each HITL-gated

## 9. Folder rename note

User wants the local folder renamed to **`pytorch`**. This can't be done safely from inside the
running session (Windows locks the current working directory). Steps for the user — see the chat
summary; the GitHub repo is already `pytorch-fit-system`.
