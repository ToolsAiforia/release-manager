# Security & Safety Rules

## Git Operations
- **No git commit, push, or rebase** — only read operations + fetch/pull
- `fetch_and_pull()` is the only write-adjacent operation, triggered explicitly by user
- No `subprocess` calls — use GitPython API exclusively

## File System
- No filesystem writes beyond what FastAPI/uvicorn needs
- Never open repos with `Repo.init()` or `Repo.clone_from()`
- All `git.Repo` objects are short-lived (per function call, never cached)

## Dependencies
- No new dependencies without explicit user approval
- Current deps: fastapi, uvicorn, jinja2, pydantic, pydantic-settings, gitpython, python-multipart
- Dev deps: pytest, pytest-asyncio, httpx

## Web Security
- Escape user-provided text before DOM insertion (`escapeHtml()`)
- No raw user input in server-rendered HTML (Jinja2 auto-escapes)
- No secret files committed (`.env`, credentials)
