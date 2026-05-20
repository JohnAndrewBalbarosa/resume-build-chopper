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
from .sources.social.auth import (
    ConsolePrompt,
    Credentials,
    LoginError,
    SessionStore,
    masked_input,
)
from .sources.social.browser_cookies import import_cookies_report

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


def _pick_vendor_interactive() -> str:
    """Show a numbered menu of vendors; accept number or name."""
    agg = build_default_aggregator()
    vendors = agg.available_vendors()
    typer.echo("\nAvailable vendors:")
    for i, v in enumerate(vendors, 1):
        typer.echo(f"  {i}. {v}")
    while True:
        raw = typer.prompt("Pick a vendor (number or name)").strip().lower()
        if raw.isdigit() and 1 <= int(raw) <= len(vendors):
            return vendors[int(raw) - 1]
        if raw in vendors:
            return raw
        typer.secho("Invalid choice. Try again.", fg=typer.colors.YELLOW)


@app.command()
def scrape() -> None:
    """Run a single vendor and dump posts + mentions as JSON. No flags — just answer the prompts."""
    vendor = _pick_vendor_interactive()
    agg = build_default_aggregator()
    handle = typer.prompt(
        "Your handle on that vendor (leave blank to skip own-posts)", default=""
    )
    full_name = typer.prompt(
        "Full name for mention search (leave blank to skip)", default=""
    )
    limit = int(typer.prompt("Max results per call", default="50"))

    factory = agg._registry[vendor]  # noqa: SLF001
    impl = factory()
    posts = impl.fetch_own_posts(handle, limit=limit) if handle else []
    mentions = impl.search_mentions(full_name, limit=limit) if full_name else []
    payload = {
        "vendor": vendor,
        "posts": [p.model_dump(mode="json") for p in posts],
        "mentions": [m.model_dump(mode="json") for m in mentions],
    }
    text = json.dumps(payload, indent=2, default=str)

    if typer.confirm("Save output to a file?", default=False):
        raw = typer.prompt("Output path", default=f"out/{vendor}.json")
        out_path = Path(raw)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        typer.secho(
            f"Wrote {out_path} ({len(posts)} posts, {len(mentions)} mentions)",
            fg=typer.colors.GREEN,
        )
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
def login() -> None:
    """Sign in to a social vendor. No flags — just answer the prompts.

    You'll be asked: which vendor, browser-cookie path or username+password,
    then any 2FA codes if they come up.
    """
    store = SessionStore()
    vendor = _pick_vendor_interactive()

    typer.echo("\nHow do you want to sign in?")
    typer.echo("  1. Use cookies from my browser (recommended — no password needed)")
    typer.echo("  2. Type my username and password here")
    choice = typer.prompt("Pick (1 or 2)", default="1").strip()

    if choice == "1":
        typer.echo("\nWhich browser are you signed in on?")
        typer.echo("  1. Chrome  (needs admin shell on Windows)")
        typer.echo("  2. Edge")
        typer.echo("  3. Firefox")
        typer.echo("  4. Brave")
        typer.echo("  5. Opera")
        typer.echo("  6. Auto (try all, Chrome first)")
        b_raw = typer.prompt("Pick (1-6)", default="6").strip()
        b_map = {"1": "chrome", "2": "edge", "3": "firefox", "4": "brave", "5": "opera", "6": "auto"}
        browser = b_map.get(b_raw, "auto")
        report = import_cookies_report(vendor, browser=browser)
        typer.echo("\nBrowser cookie probe:")
        for name, status in report.attempts:
            typer.echo(f"  {name:<10} {status}")
        if not report.ok:
            typer.secho(
                f"\nNo {vendor} cookies recovered. On Windows, Chrome cookies need "
                "an admin shell to decrypt. Try Edge, or right-click PowerShell -> "
                "'Run as administrator'. Make sure you're signed in on that browser first.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
        store.save(vendor, report.cookies)
        typer.secho(
            f"\nSaved {len(report.cookies)} cookies for {vendor} -> {store.path(vendor)}",
            fg=typer.colors.GREEN,
        )
        return

    # Username/password path
    username = typer.prompt(f"{vendor} username or email")
    password = masked_input(f"{vendor} password (shown as *): ")
    if not password:
        typer.secho("Empty password — aborting.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    creds = Credentials(username=username, password=password)
    login_fn = _resolve_login(vendor)
    try:
        cookies = login_fn(creds, ConsolePrompt())
    except LoginError as exc:
        typer.secho(f"\nLogin failed: {exc}", fg=typer.colors.RED)
        typer.echo("Tip: try the browser-cookie path instead — no password needed.")
        raise typer.Exit(code=1) from exc
    store.save(vendor, cookies)
    typer.secho(
        f"\nSigned in. {len(cookies)} cookies saved to {store.path(vendor)}",
        fg=typer.colors.GREEN,
    )


@app.command()
def logout() -> None:
    """Clear the persisted session for a vendor — no flags, just answer the prompt."""
    vendor = _pick_vendor_interactive()
    SessionStore().clear(vendor)
    typer.secho(f"Cleared session for {vendor}.", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
