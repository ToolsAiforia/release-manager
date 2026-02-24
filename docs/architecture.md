# Release Manager — Architecture

## Purpose

Single-user web tool that automates release notes generation. Scans git repositories in a local directory, collects commits between two tags, extracts Linear issue keys, and produces structured reports for export.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Package manager | uv |
| Web framework | FastAPI |
| Templating | Jinja2 |
| Frontend interactivity | HTMX (vendor file, no build step) |
| Git operations | GitPython |
| Data validation | Pydantic v2 |
| Configuration | pydantic-settings (env vars with `RM_` prefix) |
| Tests | pytest + unittest.mock |

## Project Structure

```
ReleaseManager/
├── pyproject.toml                 # Dependencies, build config, pytest config
├── Makefile                       # setup, run, test, lint
├── .python-version                # 3.12
├── .gitignore
├── .claude/agents/                # Claude Code agent instructions
├── docs/architecture.md           # This file
├── src/release_manager/
│   ├── __init__.py
│   ├── __main__.py                # Entry point: runs uvicorn
│   ├── app.py                     # FastAPI app factory (create_app)
│   ├── settings.py                # Pydantic Settings: host, port, default_root_dir
│   ├── models.py                  # All Pydantic data models
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # All HTTP endpoints (pages, API, HTMX partials)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scanner.py             # Discover git repos in a directory
│   │   ├── git_ops.py             # Tags, fetch/pull, commits between tags
│   │   ├── parser.py              # Extract Linear keys from commit messages
│   │   └── exporter.py            # Export report to CSV, Markdown, JSON
│   ├── templates/
│   │   ├── base.html              # Base layout (head, styles, htmx script)
│   │   ├── index.html             # Main page with 3-step UI + all JS logic
│   │   └── partials/
│   │       ├── repo_list.html     # HTMX fragment: repo table with checkboxes
│   │       └── report_table.html  # HTMX fragment: report (server-rendered)
│   └── static/
│       ├── style.css              # All styles (CSS custom properties, no framework)
│       └── htmx.min.js            # HTMX 2.0.4 vendor file
└── tests/
    ├── __init__.py
    ├── test_parser.py             # Linear key extraction tests
    ├── test_scanner.py            # Repo discovery tests (mocked)
    └── test_git_ops.py            # Git operations tests (mocked)
```

## Data Flow

```
User browser
    │
    ├─ GET /                          → index.html (full page)
    │
    ├─ POST /partials/repo-list       → HTMX fragment with repo table
    │   └─ calls scanner.scan_repos()
    │
    ├─ GET /api/repos/{name}/tags     → JSON list of tags
    │   └─ calls git_ops.get_tags()
    │
    ├─ POST /api/repos/{name}/fetch   → JSON status message
    │   └─ calls git_ops.fetch_and_pull()
    │
    ├─ POST /api/collect              → JSON ReleaseReport
    │   ├─ calls git_ops.get_commits_between_tags() per repo
    │   ├─ calls parser.extract_linear_keys() per commit
    │   └─ stores report in app.state.last_report
    │
    ├─ POST /api/refresh              → JSON ReleaseReport (re-collects from last selections)
    │
    └─ GET /api/export/{format}       → File download (csv|markdown|json)
        └─ reads app.state.last_report
```

## Data Models (models.py)

All models are Pydantic BaseModel subclasses.

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `RepoInfo` | Discovered git repo | name, path, current_branch, has_uncommitted |
| `TagInfo` | Git tag metadata | name, commit_hash, date, is_release |
| `CommitInfo` | Single commit | hash, short_hash, message, author, date, linear_keys |
| `RepoSelection` | User's tag range choice | repo_name, from_tag, to_tag |
| `RepoReport` | Report for one repo | repo_name, from_tag, to_tag, commits, linear_keys |
| `ReleaseReport` | Full aggregated report | generated_at, root_dir, repos[], all_linear_keys[] |

## Services

### scanner.py
- `scan_repos(root_dir: str) -> list[RepoInfo]`
- Iterates sorted subdirectories of `root_dir`
- Skips hidden dirs (`.name`) and non-git dirs
- Uses `git.Repo()` to detect git repos; catches `InvalidGitRepositoryError`
- Returns branch name and dirty status

### git_ops.py
- `get_tags(repo_path: str) -> list[TagInfo]` — all tags sorted by date descending
- `fetch_and_pull(repo_path: str) -> str` — `git fetch --tags` + `git pull` with error handling
- `get_commits_between_tags(repo_path, from_tag, to_tag) -> list[CommitInfo]` — `git log from_tag..to_tag` (from_tag EXCLUDED)
- `_tag_commit(tag_ref)` — dereferences annotated tags to their commit object

**Release tag patterns:**
- `YYYYMMDD-N` (e.g. `20260206-2`) — regex `^\d{8}-\d+$`
- Semver (e.g. `v1.2.3`) — regex `^v?\d+\.\d+\.\d+`
- Tags matching either pattern have `is_release=True`

### parser.py
- `extract_linear_keys(text: str) -> list[str]`
- Regex: `\b([A-Za-z]+-\d+)\b`
- Normalizes to UPPERCASE
- Deduplicates preserving first-occurrence order

### exporter.py
- `to_csv(report) -> str` — CSV with columns: Repo, From Tag, To Tag, Commit, Author, Date, Message, Linear Keys
- `to_markdown(report) -> str` — Markdown with headers per repo, bullet list of commits
- `to_json(report) -> str` — Full Pydantic model dump as formatted JSON

## State Management

- **No database.** Single-user tool uses `app.state` (in-memory).
- `app.state.templates` — Jinja2Templates instance
- `app.state.last_report` — Last generated `ReleaseReport` (used by export and refresh)

## Frontend Architecture

- **No SPA, no build step.** Server returns full HTML pages and HTMX fragments.
- `index.html` contains all JavaScript inline (no separate JS files).
- **HTMX** handles the scan form → repo list (POST to `/partials/repo-list`, inserts HTML).
- **Vanilla JS** handles tag loading, commit collection, and report rendering (via fetch + DOM manipulation).

### UI Flow
1. User enters directory path, clicks **Scan** → HTMX loads repo table
2. User clicks **Load Tags** per repo (or **Load All Tags**) → JS populates `<select>` dropdowns
3. User optionally clicks **Fetch** per repo → JS calls fetch API
4. User selects from/to tags, checks repos, clicks **Collect Commits** → JS calls collect API, renders report
5. User can **Export** (CSV/MD/JSON) or **Check Changes** (re-collect same selections)

## Configuration

Pydantic Settings with `RM_` env prefix:

| Setting | Env Var | Default |
|---------|---------|---------|
| host | `RM_HOST` | `127.0.0.1` |
| port | `RM_PORT` | `8000` |
| default_root_dir | `RM_DEFAULT_ROOT_DIR` | `/Users/malinovskaia/Work/` |

## Testing Strategy

- **Unit tests only** — no integration/E2E tests.
- Git operations are tested with mocked `git.Repo` (via `unittest.mock.patch`).
- Scanner is tested with `tmp_path` fixture + mocked `Repo`.
- Parser is tested with pure input/output (no mocks needed).
- Run: `make test` or `uv run pytest tests/ -v`

## Safety Constraints

- **No `git commit` or `git push`** — only read operations + `fetch`/`pull`.
- `fetch_and_pull()` is the only write-adjacent operation, triggered explicitly by user.
- Detached HEAD and missing tracking branch are handled gracefully.

## Commands

```bash
make setup    # uv sync --all-extras
make run      # uv run python -m release_manager
make test     # uv run pytest tests/ -v
make lint     # uv run ruff check src/ tests/
```
