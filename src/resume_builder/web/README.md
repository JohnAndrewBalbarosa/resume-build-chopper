# `web/` — FastAPI "CareerLens" Prototype

The browser-facing prototype that wraps the CLI pipeline in a UI, with OAuth identity and
assisted social-login. **Department 05.**

> 📖 [Dept 05 — Web / SaaS](../../../docs/departments/05-web-saas/README.md)
> ⚠️ Prototype: **no user DB, no billing, no rate limiting yet.**

## Request flow

```mermaid
flowchart TD
    U[Browser] --> App[FastAPI app.py]
    App -->|GET / /prototype /build-form| Tpl[templates + static]
    App -->|GET /auth/provider/start + callback| Auth[auth.py OAuth<br/>github/google/microsoft]
    App -->|POST /build| Pipe[[Dept 01: Pipeline.run]]
    App -->|POST /api/social-login/vendor| Job[social-login job]
    Job --> SOC[[Dept 02: browser_login]]
    App -->|GET /api/social-login/jobs/id| Job
    App -->|POST /api/cdo/advisor/analyze| Cdo[cdo_advisor.py]
    Pipe --> Out[[Dept 04: renderers]]
```

## Files

| File | Role |
|---|---|
| `app.py` | FastAPI routes (pages, auth, build, social-login, advisor, healthz) |
| `auth.py` | `WebAuthSettings` — GitHub/Google/Microsoft OAuth (`read:user`, `user:email`) |
| `cdo_advisor.py` | Resume injection / compliance analysis |
| `mock_data.py` | Prototype fixtures |
| `dev_server.py` | Local dev server |
| `templates/` | Jinja2 HTML |
| `static/` | CSS / JS |

## Rules

- **Don't fork the engine — call it.** `/build` is a thin adapter to `Pipeline.run()`.
- OAuth is **identity, not authorization-to-act** (don't expand scopes without a product call).
- Secrets via env only (see `docs/web-auth-setup.md`).
- Long/interactive logins run as **jobs** (start → poll), never block a request thread.
- Validate all request bodies; treat advisor input + uploads as untrusted.
