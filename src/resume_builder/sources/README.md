# `sources/` — Data Collection (Stage 2)

Pulls raw evidence *into* the system and normalizes it into `models.py` shapes. **Department 02.**

> 📖 [Dept 02 — Sources / Data Collection](../../../docs/departments/02-sources/README.md)

## Contract

```python
class SourceCollector(ABC):
    name: str
    def collect(self, **kwargs) -> Any   # concrete return types differ per source
```

| Collector | Input | Output |
|---|---|---|
| `GitHubSource` | github user (via `gh` CLI) | `list[Repo]` |
| `DocumentSource` | file path | `list[RawDocument]` |
| `SocialAggregator` (in [`social/`](social/README.md)) | `ScrapeConfig` | `CollectResult` |

## Process

```mermaid
flowchart TD
    subgraph Sources
      GH[GitHubSource] -->|gh repo list| R[Repo array]
      DOC[DocumentSource] -->|parse PDF/DOCX/TeX/MD| D[RawDocument array]
      SOC[social/ SocialAggregator] -->|parallel scrape + dedupe + cache| C[CollectResult]
    end
    R --> P[[Dept 01: Pipeline]]
    D --> P
    C --> P
```

## Files

| File | Role |
|---|---|
| `base.py` | `SourceCollector` ABC |
| `github.py` | GitHub repos via the `gh` CLI |
| `document.py` | Local resume parsing (PDF/DOCX/TeX/MD) → text |
| [`social/`](social/README.md) | The heavy social-scraping subsystem |

## Golden rule

A source failure must **degrade, never crash** the build. Normalize at the boundary — no raw
HTML/DOM leaks downstream. Sources are mode-agnostic (no `ai`/`static` logic here).
