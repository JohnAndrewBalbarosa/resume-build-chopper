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
    parse_curl_command,
)
from .sources.social.browser_login import (
    PlaywrightNotInstalled,
    open_login_window,
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

# Per-vendor cookie names users will see in DevTools.
# First entry in each tuple is required; the rest are optional but improve reliability.
_VENDOR_COOKIES: dict[str, tuple[str, ...]] = {
    "facebook": ("c_user", "xs"),
    "linkedin": ("li_at",),
    "instagram": ("sessionid",),
    "twitter": ("auth_token", "ct0"),
}

_DEVTOOLS_HINTS: dict[str, str] = {
    "facebook": "Open facebook.com signed in -> F12 -> Application tab -> Cookies -> https://www.facebook.com",
    "linkedin": "Open linkedin.com signed in -> F12 -> Application tab -> Cookies -> https://www.linkedin.com",
    "instagram": "Open instagram.com signed in -> F12 -> Application tab -> Cookies -> https://www.instagram.com",
    "twitter": "Open x.com signed in -> F12 -> Application tab -> Cookies -> https://x.com",
}


def _collect_manual_cookies(vendor: str) -> dict[str, str]:
    """Walk the user through DevTools cookie-copy. Returns whatever was provided."""
    needed = _VENDOR_COOKIES.get(vendor, ())
    if not needed:
        typer.secho(f"No cookie schema for vendor {vendor}", fg=typer.colors.RED)
        return {}
    typer.echo("")
    typer.secho(
        f"How to grab the cookies for {vendor}:",
        fg=typer.colors.CYAN,
        bold=True,
    )
    typer.echo(f"  {_DEVTOOLS_HINTS.get(vendor, '(see browser DevTools cookie panel)')}")
    typer.echo(f"  You will need: {', '.join(needed)}")
    typer.echo("  Tip: click the cookie row, then double-click the Value cell to select it.\n")

    out: dict[str, str] = {}
    for name in needed:
        value = masked_input(f"Paste value of `{name}`: ")
        value = value.strip().strip('"').strip("'")
        if value:
            out[name] = value
    return out


def _read_curl_paste() -> str:
    """Read a multi-line curl command from stdin. End on an empty line."""
    typer.echo(
        "\nPaste the curl command below. Press Enter on an EMPTY line when done.\n"
        "(In Chrome DevTools: Network tab -> right-click a request -> Copy -> 'Copy as cURL (bash)')\n"
    )
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            if lines:
                break
            continue
        lines.append(line)
    return "\n".join(lines)


def _collect_curl_command(vendor: str) -> dict[str, str]:
    """Parse a pasted curl command and keep only the cookies we expect for this vendor.

    Returns the curl-supplied cookies filtered to the vendor's whitelist + any extras
    that happen to be there (FB needs c_user/xs/fr/datr; we keep all four so future
    code can use them).
    """
    raw = _read_curl_paste()
    if not raw:
        return {}
    try:
        extract = parse_curl_command(raw)
    except LoginError as exc:
        typer.secho(f"Curl parse failed: {exc}", fg=typer.colors.RED)
        return {}

    typer.echo(f"\nParsed {len(extract.cookies)} cookies from the curl command.")
    required = _VENDOR_COOKIES.get(vendor, ())
    missing = [name for name in required if name not in extract.cookies]
    if missing:
        typer.secho(
            f"Warning: missing required cookies for {vendor}: {', '.join(missing)}. "
            "The session may not authenticate properly.",
            fg=typer.colors.YELLOW,
        )
    if extract.url:
        typer.echo(f"  Request URL was: {extract.url}")
    return dict(extract.cookies)


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
    typer.echo("  1. Open a sign-in window — just log in like normal (Recommended)")
    typer.echo("  2. Type my username and password here in the terminal")
    typer.echo("  3. Advanced options")
    choice = typer.prompt("Pick (1, 2, or 3)", default="1").strip()

    if choice == "1":
        ok = _run_playwright_login(vendor, store)
        raise typer.Exit(code=0 if ok else 1)

    if choice == "3":
        _run_advanced_submenu(vendor, store)
        return

    # ---- option 2: type credentials in this terminal ----
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
        typer.echo("Tip: try option 1 (sign-in window) — handles 2FA, CAPTCHA, anything.")
        raise typer.Exit(code=1) from exc
    store.save(vendor, cookies)
    typer.secho(
        f"\nSigned in. {len(cookies)} cookies saved to {store.path(vendor)}",
        fg=typer.colors.GREEN,
    )


def _run_playwright_login(vendor: str, store: SessionStore) -> bool:
    typer.echo(
        "\nA browser window will open. Sign in like you normally would — "
        "username, password, and any 2FA codes. When you reach your home page, "
        "the window will close automatically and your session is saved."
    )
    try:
        result = open_login_window(vendor)
    except PlaywrightNotInstalled as exc:
        typer.secho(f"\n{exc}", fg=typer.colors.RED)
        return False
    except TimeoutError as exc:
        typer.secho(f"\n{exc}", fg=typer.colors.RED)
        return False
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"\nBrowser login failed: {exc}", fg=typer.colors.RED)
        return False
    store.save(vendor, result.cookies)
    if result.storage_state is not None:
        store.save_storage_state(vendor, result.storage_state)
    typer.secho(
        f"\nSigned in. {len(result.cookies)} cookies saved to {store.path(vendor)}",
        fg=typer.colors.GREEN,
    )
    return True


def _run_advanced_submenu(vendor: str, store: SessionStore) -> None:
    typer.echo("\nAdvanced options:")
    typer.echo("  a. Read cookies from my installed browser jar (Chrome v127+ usually fails)")
    typer.echo("  b. Paste cookie values individually")
    typer.echo("  c. Paste a `curl` command from DevTools")
    adv = typer.prompt("Pick (a, b, or c)", default="c").strip().lower()

    if adv == "a":
        _legacy_browser_jar_login(vendor, store)
        return
    if adv == "b":
        cookies = _collect_manual_cookies(vendor)
        if not cookies:
            typer.secho("No cookies entered.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        store.save(vendor, cookies)
        typer.secho(f"\nSaved {len(cookies)} cookies -> {store.path(vendor)}", fg=typer.colors.GREEN)
        return
    if adv == "c":
        cookies = _collect_curl_command(vendor)
        if not cookies:
            typer.secho("No cookies in curl.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        store.save(vendor, cookies)
        typer.secho(f"\nSaved {len(cookies)} cookies -> {store.path(vendor)}", fg=typer.colors.GREEN)
        return
    typer.secho(f"Unknown option: {adv}", fg=typer.colors.RED)
    raise typer.Exit(code=1)


def _legacy_browser_jar_login(vendor: str, store: SessionStore) -> None:
    typer.echo("\nWhich browser?  1.Chrome  2.Edge  3.Firefox  4.Brave  5.Opera  6.Auto")
    b_raw = typer.prompt("Pick (1-6)", default="6").strip()
    b_map = {"1": "chrome", "2": "edge", "3": "firefox", "4": "brave", "5": "opera", "6": "auto"}
    browser = b_map.get(b_raw, "auto")
    report = import_cookies_report(vendor, browser=browser)
    typer.echo("\nBrowser cookie probe:")
    for name, status in report.attempts:
        typer.echo(f"  {name:<10} {status}")
    if not report.ok:
        app_bound = any(
            "unable to get key" in status.lower() or "app-bound" in status.lower()
            for _, status in report.attempts
        )
        requires_admin = any(
            "requiresadmin" in status.lower() for _, status in report.attempts
        )
        typer.echo("")
        if app_bound:
            typer.secho(
                "Chrome v127+ uses app-bound encryption that browser_cookie3 cannot "
                "read. Try option 1 (sign-in window) instead — it always works.",
                fg=typer.colors.RED,
            )
        elif requires_admin:
            typer.secho(
                "Chrome cookies are DPAPI-encrypted at user scope. Run PowerShell as "
                "administrator, or use option 1 (sign-in window) — no admin needed.",
                fg=typer.colors.RED,
            )
        else:
            typer.secho(
                f"No {vendor} cookies recovered. Sign in on that browser first, "
                "or use option 1 (sign-in window).",
                fg=typer.colors.RED,
            )
        raise typer.Exit(code=1)
    store.save(vendor, report.cookies)
    typer.secho(
        f"\nSaved {len(report.cookies)} cookies -> {store.path(vendor)}",
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
