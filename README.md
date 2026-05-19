# resume-build-chopper

AI-powered (or fully static) resume builder na nag-mi-mine ng iyong GitHub repos at personal documents (PDF/DOCX) para gumawa ng **role-targeted** resume. Halimbawa: kung gusto mo mag-apply as cybersecurity engineer, only the cybersecurity-relevant projects/skills are surfaced — hindi ang buong portfolio mo.

## Modes

| Mode | Role picker | Source analysis | User docs | Best for |
|---|---|---|---|---|
| **`ai`** | Free-form prompt → LLM produces `RoleSpec` | LLM scans READMEs + metadata for relevance | PDF/DOCX/folder, LLM cross-references | Highest quality, requires API key |
| **`static`** | Pick from `config/roles.json` | Regex + keyword scoring from `config/regex_patterns.json` | LaTeX-formatted resume input | Offline, deterministic, no LLM |

## Quickstart

```bash
# Install
pip install -e ".[dev]"

# Copy env template and fill in API keys (only if using AI mode)
cp .env.example .env

# Make sure gh is installed + authenticated
gh auth status

# CLI — AI mode
resume-build build --mode ai \
    --gh-user yourhandle \
    --role-prompt "cybersecurity blue team / SOC analyst" \
    --docs ./my-resume.pdf \
    --formats latex,pdf,md,json \
    --output ./out/

# CLI — static mode
resume-build build --mode static \
    --gh-user yourhandle \
    --role cybersecurity-blueteam \
    --docs ./my-resume.tex \
    --formats latex,md,json \
    --output ./out/

# Web UI
uvicorn resume_builder.web.app:app --reload
```

## Architecture

See `C:\Users\Drew\.claude\plans\pwede-bang-magkaroon-ka-peppy-trinket.md` for the full plan and design rationale.

Each stage of the pipeline (role picking, source collection, extraction, synthesis, rendering) is an ABC with at least one **static** and one **AI** implementation. LLM access is behind a provider-agnostic interface so you can swap Anthropic ↔ OpenAI without touching pipeline code.

## Extensibility — no code required

- **Add a new role**: edit `config/roles.json`.
- **Add a new regex pattern category**: edit `config/regex_patterns.json`.
- **Add a new resume template**: drop a new `.j2` file into `config/templates/`.

Code-level extension points (subclassing):
- `LLMProvider` — add a new model provider.
- `SourceCollector` — add GitLab, Bitbucket, etc.
- `Renderer` — add a new output format.
