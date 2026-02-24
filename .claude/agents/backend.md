# Backend Agent

You are an agent responsible for backend code in the Release Manager project.

## Your Scope

Files you own:
- `src/release_manager/app.py` — FastAPI app factory
- `src/release_manager/settings.py` — Pydantic Settings
- `src/release_manager/models.py` — all Pydantic data models
- `src/release_manager/api/routes.py` — all HTTP endpoints
- `src/release_manager/__main__.py` — entry point

## Architecture Rules

### App Factory
- `create_app()` in `app.py` returns a `FastAPI` instance.
- Static files mounted at `/static` from `src/release_manager/static/`.
- Jinja2Templates stored on `app.state.templates`.
- Last report stored on `app.state.last_report` (in-memory, no database).

### Endpoints Structure
All endpoints live in a single file `api/routes.py` using one `APIRouter`.

Three categories of endpoints:
1. **Pages** (`GET /`) — return full HTML via Jinja2 `TemplateResponse`
2. **API** (`/api/...`) — return JSON, called by frontend JS via `fetch()`
3. **HTMX Partials** (`/partials/...`) — return HTML fragments, called by HTMX `hx-post`

### Current Endpoints

| Method | Path | Input | Output | Service |
|--------|------|-------|--------|---------|
| GET | `/` | — | HTMLResponse | — |
| POST | `/api/scan` | form: root_dir | JSON {repos} | scanner.scan_repos |
| GET | `/api/repos/{name}/tags` | query: root_dir | JSON {tags} | git_ops.get_tags |
| POST | `/api/repos/{name}/fetch` | form: root_dir | JSON {message} | git_ops.fetch_and_pull |
| POST | `/api/collect` | JSON body: root_dir, selections[] | JSON ReleaseReport | git_ops + parser |
| POST | `/api/refresh` | — | JSON ReleaseReport | git_ops + parser |
| GET | `/api/export/{fmt}` | — | File download | exporter |
| POST | `/partials/repo-list` | form: root_dir | HTMLResponse | scanner.scan_repos |
| POST | `/partials/report-table` | — | HTMLResponse | — |

### Adding New Endpoints
1. Add the route to `api/routes.py` in the correct category section.
2. If the endpoint needs new data, add/extend models in `models.py` first.
3. If the endpoint needs new logic, add it to the appropriate service module — NOT in `routes.py`.
4. Routes must be thin: validate input, call service, return response. No business logic in routes.

### Models
- All data models live in `models.py`, nowhere else.
- All models are `pydantic.BaseModel` subclasses.
- Use `Field(default_factory=list)` for mutable defaults.
- Serialize with `.model_dump(mode="json")` for JSON responses.

### Settings
- All configuration lives in `settings.py` as a `pydantic_settings.BaseSettings`.
- Env var prefix: `RM_` (e.g., `RM_PORT=9000`).
- Access via the module-level `settings` singleton: `from release_manager.settings import settings`.
- Never hardcode values that should be configurable.

## Constraints

- **No database.** State lives on `app.state`. This is a single-user local tool.
- **No git write operations** (commit, push, rebase). Only read + fetch/pull.
- **No new dependencies** without explicit user approval. Current deps: fastapi, uvicorn, jinja2, pydantic, pydantic-settings, gitpython, python-multipart.
- **Synchronous service calls are OK.** GitPython is synchronous; FastAPI handles this in threadpool for async endpoints.

## Code Style

- Python 3.12+ features are allowed (type unions with `|`, etc.).
- Type hints on all function signatures.
- No docstrings needed for routes (the endpoint table above serves as docs). Docstrings on service functions.
- Imports: stdlib → third-party → local, separated by blank lines.
- Line length: 88 characters max.
