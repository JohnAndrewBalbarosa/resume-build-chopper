# `resume_builder` — package overview

The whole application lives here. It's a **5-stage pipeline** where every stage has two
interchangeable implementations (`static` = offline/regex, `ai` = LLM-driven) behind one
interface. The orchestrator (`pipeline.py`) is the only code that knows which mode is running.

> 📖 Architecture & team ownership: [`docs/departments/`](../../docs/departments/README.md)

## Core principle

> **One person, many roles — one truth, many resumes.** Collect everything true about a
> candidate, then *chop* it down to a single target role so only relevant evidence survives.

## The pipeline

```mermaid
flowchart LR
    A[role/<br/>RolePicker] --> B[sources/<br/>collect raw evidence]
    B --> C[extractors/<br/>score by role]
    C --> D[synthesizers/<br/>assemble Resume]
    D --> E[renderers/<br/>write files]
    M[models.py<br/>shared contracts] -.-> A
    M -.-> B
    M -.-> C
    M -.-> D
    M -.-> E
    P[pipeline.py<br/>orchestrator] ==> A
    P ==> B
    P ==> C
    P ==> D
    P ==> E
```

## Folder map

| Folder / file | Responsibility | Department |
|---|---|---|
| `models.py` | Canonical pydantic contracts shared by all stages (the constitution) | 01 |
| `pipeline.py` | Orchestrator; the only mode-aware code | 01 |
| `config.py` / `principles.py` | Settings, paths, Harvard resume principles | 01 |
| `cli.py` | `resume-build` Typer entrypoint | 01 |
| [`role/`](role/README.md) | Pick a `RoleSpec` from an id or a prompt | 01 |
| [`sources/`](sources/README.md) | Pull raw evidence (GitHub, docs, social) | 02 |
| [`extractors/`](extractors/README.md) | Score/filter repos by role → `Evidence` | 03 |
| [`synthesizers/`](synthesizers/README.md) | Assemble inputs → `Resume` | 03 |
| [`llm/`](llm/README.md) | Provider-agnostic LLM interface | 03 |
| [`renderers/`](renderers/README.md) | `Resume` → files (LaTeX/PDF/HTML/MD/JSON) | 04 |
| [`web/`](web/README.md) | FastAPI "CareerLens" prototype | 05 |
| [`commands/`](commands/README.md) | CLI subcommands (auth, scrape) | 01 |
| `review_orchestrator.py` | LLM audit/review of a resume | 03 |

## Two modes

```mermaid
flowchart TD
    Mode{Mode?}
    Mode -->|static| S[StaticRolePicker / StaticExtractor /<br/>StaticSynthesizer / NullProvider]
    Mode -->|ai| AI[AIRolePicker / AIExtractor /<br/>AISynthesizer / real LLMProvider]
    S --> R[same Resume shape]
    AI --> R
    R --> Out[renderers never know which mode ran]
```

## Full architecture — all packages

```mermaid
flowchart TD
    subgraph P1["P1 — Collection (sources/)"]
        GH[GitHub API] --> SC[sources/]
        SM[Social / docs] --> SC
    end

    subgraph P2["P2 — Extraction (extraction/)"]
        SC --> EX[extraction/<br/>SourceFetcher · ExtractionRuleEngine<br/>gather_repo_sources · extract_website]
        EX --> CS[CleanedSource list]
    end

    subgraph P3["P3 — Interpretation (interpretation/)"]
        CS --> IN[interpretation/<br/>RetrievalMiddleman → ParallelTagRunner<br/>→ compile_tags → GlobalNormalizer]
        IN --> IC[IndustryClassification]
        IN --> UP[UserProfile]
    end

    subgraph P4["P4 — Assembly (industry.py + synthesizers/)"]
        IC --> AS[synthesizers/<br/>AISynthesizer / StaticSynthesizer]
        ME[metrics/<br/>ProjectMetric CSV] --> AS
        AS --> RES[Resume]
    end

    subgraph P5["P5 — Render (renderers/ + layout/)"]
        RES --> RN[renderers/<br/>LaTeX · HTML · PDF · MD · JSON]
        RN --> LY[layout/<br/>analyze_html_bounds<br/>BoundsReport]
    end

    LLM[llm/<br/>LLMProvider ABC<br/>Anthropic · OpenAI · ClaudeSession · Null] -.->|structured calls| EX
    LLM -.->|structured calls| IN
    LLM -.->|structured calls| AS

    JA[job_application/<br/>ApplicationPlan · WorkflowStateMachine<br/>field_taxonomy · field_mapping] -.->|sibling concern| RES

    P1 --> P2 --> P3 --> P4 --> P5
```

## Extended folder map

| Folder / file | Stage | Responsibility | Department |
|---|---|---|---|
| `models.py` | cross-cut | Canonical pydantic contracts (the constitution) | 01 |
| `pipeline.py` | cross-cut | Orchestrator; the only mode-aware code | 01 |
| `config.py` / `principles.py` | cross-cut | Settings, paths, Harvard resume principles | 01 |
| `cli.py` | cross-cut | `resume-build` Typer entrypoint | 01 |
| [`role/`](role/README.md) | pre-P1 | Pick a `RoleSpec` from an id or a prompt | 01 |
| [`sources/`](sources/README.md) | P1 | Pull raw evidence (GitHub, docs, social) | 02 |
| [`extraction/`](extraction/README.md) | P2 | Website-agnostic extraction → `CleanedSource` | 03 |
| [`interpretation/`](interpretation/README.md) | P3 | Tag + normalize → `IndustryClassification` + `UserProfile` | 03 |
| [`extractors/`](extractors/README.md) | P3-legacy | Score/filter repos by role → `Evidence` | 03 |
| [`synthesizers/`](synthesizers/README.md) | P4 | Assemble inputs → `Resume` | 03 |
| `industry.py` | P4 | Industry plan + classification models | 03 |
| [`metrics/`](metrics/README.md) | P4 support | Candidate-confirmed impact numbers → grounds bullets | 03 |
| [`llm/`](llm/README.md) | cross-cut | Provider-agnostic LLM interface | 03 |
| [`renderers/`](renderers/README.md) | P5 | `Resume` → files (LaTeX/PDF/HTML/MD/JSON) | 04 |
| [`layout/`](layout/README.md) | P5 support | HTML → `BoundsReport` (page-bleed analysis) | 04 |
| [`job_application/`](job_application/README.md) | sibling | `ApplicationPlan` schema + workflow state machine | 05 |
| [`web/`](web/README.md) | sibling | FastAPI "CareerLens" prototype | 05 |
| [`commands/`](commands/README.md) | cross-cut | CLI subcommands (auth, scrape) | 01 |
| `review_orchestrator.py` | cross-cut | LLM audit/review of a resume | 03 |
