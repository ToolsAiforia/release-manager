# Release Manager

Single-user web tool for building release notes from local git repositories. Scans repos, collects commits between tags, extracts Linear issue keys, produces structured reports.

## Quick Reference

```bash
make setup    # uv sync --all-extras
make run      # uv run python -m release_manager (localhost:8000)
make test     # uv run pytest tests/ -v
make lint     # uv run ruff check src/ tests/
```

## Tech Stack

Python 3.12 · FastAPI · Jinja2 · HTMX 2.0.4 (vendor, no build step) · Tailwind CSS (CDN) · GitPython · Pydantic v2 · pydantic-settings · uv

## Project Structure

```
src/release_manager/
├── app.py              # FastAPI app factory (create_app)
├── settings.py         # Pydantic Settings (RM_ env prefix)
├── models.py           # All Pydantic data models
├── api/routes.py       # All endpoints (pages, API, HTMX partials)
├── services/
│   ├── scanner.py      # Discover git repos
│   ├── git_ops.py      # Tags, fetch/pull, commits
│   ├── parser.py       # Extract Linear keys
│   └── exporter.py     # Export CSV/MD/JSON
├── templates/           # Jinja2 (base.html, index.html, partials/)
└── static/              # style.css, htmx.min.js
```

Tests: `tests/test_parser.py`, `tests/test_scanner.py`, `tests/test_git_ops.py`

## Architecture

- @docs/architecture.md — full architecture reference
- **No database** — state lives in `app.state` (in-memory)
- **No git writes** — only read + fetch/pull
- **No build step** — pure HTML + Tailwind CDN + inline JS + HTMX vendor file
- **Services are stateless functions** — no classes, no singletons
- **Routes are thin** — validate input → call service → return response
- **Multi-page** — vertical icon nav sidebar (w-16) + pages: Repos `/`, Draft `/draft`, Releases `/releases`

## Coding Conventions

- Python 3.12+ features OK (type unions with `|`, etc.)
- Type hints on all function signatures
- Line length: 88 chars max
- Imports: stdlib → third-party → local, separated by blank lines
- HTML: 4-space indentation
- CSS: Tailwind utility classes, custom styles in `style.css` only
- JS: inline in `index.html`, `const`/`let` only, `async/await` for fetch

## Key Rules

- Always run `make test` after backend changes
- Never modify `static/htmx.min.js` (vendor file)
- No new dependencies without explicit user approval
- Escape user text before DOM insertion
- All git.Repo objects are short-lived (created per call, never cached)
