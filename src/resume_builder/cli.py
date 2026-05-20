"""Typer CLI entrypoint.

Examples:
    resume-build list-roles
    resume-build build --mode static --gh-user JohnDoe --role cybersecurity-blueteam \
        --docs ./my-resume.tex --output ./out --formats latex,md,json
    resume-build build --mode ai --gh-user JohnDoe --role-prompt "blue team SOC analyst" \
        --docs ./my-resume.pdf --output ./out
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

import json

from .config import get_settings
from .llm import get_provider
from .models import Mode
from .pipeline import BuildInputs, Pipeline
from .role import StaticRolePicker
from .sources.social import build_default_aggregator, load_scrape_config
from .sources.social.auth import ConsolePrompt, Credentials, LoginError, SessionStore
from .sources.social.browser_cookies import import_cookies as import_browser_cookies

app = typer.Typer(help="GitHub-aware role-targeted resume builder.", no_args_is_help=True)


def _parse_formats(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@app.command()
def list_roles() -> None:
    """List role ids available in config/roles.json."""
    settings = get_settings()
    picker = StaticRolePicker(settings.roles_path)
    for role in picker.list_available():
        typer.echo(f"  {role.id:30}  {role.label}")


@app.command()
def build(
    mode: Mode = typer.Option(Mode.STATIC, "--mode", help="ai | static"),
    gh_user: str = typer.Option(..., "--gh-user", help="GitHub username/org to scan."),
    role: str | None = typer.Option(None, "--role", help="Role id (static mode)."),
    role_prompt: str | None = typer.Option(
        None, "--role-prompt", help="Free-form role description (AI mode)."
    ),
    docs: Path | None = typer.Option(
        None, "--docs", help="Path to a resume file (PDF/DOCX/TEX) or a folder."
    ),
    formats: str = typer.Option(
        "latex,md,json,pdf",
        "--formats",
        help="Comma-separated output formats: latex, md, json, pdf.",
    ),
    output: Path = typer.Option(Path("./out"), "--output", help="Output directory."),
    social: Path | None = typer.Option(
        None,
        "--social",
        help="Path to a social.yaml describing handles + enabled vendors for the "
        "scraping middleman. Optional — pipeline runs fine without it.",
    ),
    llm_provider: str | None = typer.Option(
        None,
        "--llm-provider",
        help="Override LLM provider (anthropic | openai | claude-session | null). "
        "Use `claude-session` to drive AI mode interactively via stdin/stdout — "
        "no API key required.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Build a role-targeted resume."""
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    selection = role_prompt if mode == Mode.AI else role
    if not selection:
        flag = "--role-prompt" if mode == Mode.AI else "--role"
        raise typer.BadParameter(f"{flag} is required in {mode.value} mode.")

    llm = get_provider(llm_provider) if (llm_provider and mode == Mode.AI) else None
    pipeline = Pipeline(mode=mode, llm=llm)
    inputs = BuildInputs(
        gh_user=gh_user,
        role_selection=selection,
        docs_path=docs,
        formats=_parse_formats(formats),
        output_dir=output,
        social_config_path=social,
    )
    result = pipeline.run(inputs)
    typer.echo(f"\nGenerated for role: {result.resume.role.label}")
    typer.echo(f"Projects included: {len(result.resume.projects)}")
    for path in result.output_paths:
        typer.echo(f"  -> {path}")


@app.command("list-vendors")
def list_vendors() -> None:
    """List registered social-media vendor handlers."""
    agg = build_default_aggregator()
    for name in agg.available_vendors():
        typer.echo(f"  {name}")


@app.command()
def scrape(
    vendor: str = typer.Option(..., "--vendor", help="Vendor name (e.g. twitter)."),
    handle: str = typer.Option("", "--handle", help="User handle on that vendor."),
    full_name: str = typer.Option(
        "", "--full-name", help="Full name for mention search."
    ),
    limit: int = typer.Option(50, "--limit"),
    output: Path | None = typer.Option(None, "--output", help="Write JSON here."),
) -> None:
    """Run a single vendor and dump posts + mentions as JSON for debugging."""
    agg = build_default_aggregator()
    if vendor not in agg.available_vendors():
        raise typer.BadParameter(f"Unknown vendor: {vendor}")
    factory = agg._registry[vendor]  # intentional: debug-only path  # noqa: SLF001
    impl = factory()
    posts = impl.fetch_own_posts(handle, limit=limit) if handle else []
    mentions = impl.search_mentions(full_name, limit=limit) if full_name else []
    payload = {
        "vendor": vendor,
        "posts": [p.model_dump(mode="json") for p in posts],
        "mentions": [m.model_dump(mode="json") for m in mentions],
    }
    text = json.dumps(payload, indent=2, default=str)
    if output:
        output.write_text(text, encoding="utf-8")
        typer.echo(f"Wrote {output}")
    else:
        typer.echo(text)


@app.command("scrape-all")
def scrape_all(
    config: Path = typer.Option(..., "--config", help="Path to social.yaml."),
    output: Path | None = typer.Option(None, "--output", help="Write merged JSON."),
) -> None:
    """Run every enabled vendor through the aggregator and dump merged JSON."""
    scrape_config = load_scrape_config(str(config))
    agg = build_default_aggregator()
    result = agg.collect(scrape_config)
    payload = {
        "posts": [p.model_dump(mode="json") for p in result.posts],
        "mentions": [m.model_dump(mode="json") for m in result.mentions],
        "failures": result.failures,
    }
    text = json.dumps(payload, indent=2, default=str)
    if output:
        output.write_text(text, encoding="utf-8")
        typer.echo(f"Wrote {output} ({len(result.posts)} posts, {len(result.mentions)} mentions)")
    else:
        typer.echo(text)


_LOGIN_REGISTRY = {
    "twitter": "resume_builder.sources.social.vendors.twitter:login_twitter",
    "linkedin": "resume_builder.sources.social.vendors.linkedin:login_linkedin",
    "facebook": "resume_builder.sources.social.vendors.facebook:login_facebook",
    "instagram": "resume_builder.sources.social.vendors.instagram:login_instagram",
}


def _resolve_login(vendor: str):
    target = _LOGIN_REGISTRY.get(vendor)
    if not target:
        raise typer.BadParameter(f"No login flow registered for vendor: {vendor}")
    module_path, attr = target.split(":")
    import importlib

    mod = importlib.import_module(module_path)
    return getattr(mod, attr)


@app.command()
def login(
    vendor: str = typer.Option(..., "--vendor", help="twitter | linkedin | facebook | instagram"),
    username: str = typer.Option(..., "--username", "-u"),
    use_browser_cookies: bool = typer.Option(
        False,
        "--from-browser",
        help="Skip programmatic login; pull cookies from local browser instead.",
    ),
    browser: str = typer.Option("auto", "--browser", help="chrome|edge|firefox|brave|opera|auto"),
) -> None:
    """Sign in to a social vendor. Prompts the password (hidden) and any 2FA challenges.

    On programmatic-login failure (checkpoint, CAPTCHA, etc.), pass --from-browser
    to read cookies from your already-signed-in browser session — no password needed.
    """
    store = SessionStore()
    prompt = ConsolePrompt()

    if use_browser_cookies:
        cookies = import_browser_cookies(vendor, browser=browser)
        if not cookies:
            typer.secho(
                f"Could not load {vendor} cookies from browser. Install browser_cookie3 "
                "and make sure you are signed in.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
        store.save(vendor, cookies)
        typer.secho(
            f"Saved {len(cookies)} cookies for {vendor} from browser to {store.path(vendor)}",
            fg=typer.colors.GREEN,
        )
        return

    password = prompt.ask(f"{vendor} password", secret=True)
    creds = Credentials(username=username, password=password)
    login_fn = _resolve_login(vendor)
    try:
        cookies = login_fn(creds, prompt)
    except LoginError as exc:
        typer.secho(f"Login failed: {exc}", fg=typer.colors.RED)
        typer.echo("Tip: retry with --from-browser if you can sign in via your browser.")
        raise typer.Exit(code=1) from exc

    store.save(vendor, cookies)
    typer.secho(
        f"Signed in. {len(cookies)} cookies saved to {store.path(vendor)}",
        fg=typer.colors.GREEN,
    )


@app.command()
def logout(vendor: str = typer.Option(..., "--vendor")) -> None:
    """Clear the persisted session for a vendor."""
    SessionStore().clear(vendor)
    typer.echo(f"Cleared session for {vendor}.")


if __name__ == "__main__":
    app()
