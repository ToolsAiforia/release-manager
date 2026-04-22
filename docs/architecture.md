# Release Manager — Architecture

## Purpose

Single-user web tool for building release notes and tracking deployed versions. Clones git repos remotely (via HTTPS + GitHub token), collects commits between tags, extracts Linear issue keys, and produces structured reports. Also snapshots deployed component versions from `platform-deploy` for release tracking.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Package manager | uv |
| Web framework | FastAPI |
| Templating | Jinja2 |
| Frontend interactivity | HTMX (vendor file, no build step) |
| CSS | Tailwind CSS (CDN) |
| Git operations | GitPython |
| GitHub API | urllib (REST API v3) |
| Data validation | Pydantic v2 |
| Configuration | pydantic-settings (env vars with `RM_` prefix) |
| Tests | pytest + unittest.mock |

## Project Structure

```
release-manager/
├── pyproject.toml
├── Makefile                       # setup, run, test, lint
├── docs/architecture.md           # This file
├── src/release_manager/
│   ├── __init__.py
│   ├── __main__.py                # Entry point: runs uvicorn
│   ├── app.py                     # FastAPI app factory (create_app)
│   ├── settings.py                # Pydantic Settings: host, port, repos_dir
│   ├── models.py                  # All Pydantic data models
│   ├── api/
│   │   └── routes.py              # All HTTP endpoints (pages, API, HTMX partials)
│   ├── services/
│   │   ├── scanner.py             # Discover git repos in a directory
│   │   ├── git_ops.py             # Tags, fetch/pull, commits between tags
│   │   ├── parser.py              # Extract Linear keys from commit messages
│   │   ├── exporter.py            # Export report to CSV, Markdown, JSON
│   │   ├── remote.py              # Config/snapshot persistence, clone/sync repos
│   │   ├── deploy.py              # Fetch deployed versions from GitHub API
│   │   └── linear.py              # Linear API integration
│   ├── templates/
│   │   ├── base.html              # Base layout (nav sidebar, head, scripts)
│   │   ├── index.html             # Repositories page
│   │   ├── draft.html             # Draft release page
│   │   ├── deploy.html            # Deploy tracker page
│   │   ├── releases.html          # Saved releases page
│   │   ├── release_detail.html    # Single release detail
│   │   ├── release_diff.html      # Compare two releases
│   │   └── partials/
│   │       ├── repo_list.html         # Local repo table (legacy)
│   │       ├── remote_repo_list.html  # Remote repo table with groups
│   │       └── report_content.html    # Report fragment
│   └── static/
│       ├── style.css
│       └── htmx.min.js           # HTMX 2.0.4 vendor file
└── tests/
    ├── test_parser.py             # Linear key extraction
    ├── test_scanner.py            # Repo discovery (mocked)
    ├── test_git_ops.py            # Git operations (mocked)
    ├── test_deploy.py             # Deploy service (mocked GitHub API)
    ├── test_remote.py             # Config/snapshot persistence
    └── test_sync_check.py         # Smoke test: verify repos cloned + have tags
```

## Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Repositories | Select repos + tag ranges, collect commits |
| `/draft` | Draft | View collected commits, Linear keys |
| `/deploy` | Deploy Tracker | Snapshot deployed versions from platform-deploy |
| `/releases` | Releases | Saved release history |
| `/releases/{id}` | Release Detail | Single release view |
| `/releases/diff` | Release Diff | Compare two releases |

## Data Flow

### Repositories → Draft (release notes)
```
GET /                         → Repositories page
POST /partials/remote-repo-list → Load repo table with tags (HTMX)
POST /partials/remote-sync-all  → Fetch/pull all repos, reload
POST /partials/remote-collect-and-redirect → Collect commits, redirect to /draft
```

### Deploy Tracker
```
GET /deploy                   → Deploy page
GET /api/deploy/versions      → Fetch component versions from platform-deploy (GitHub API)
GET /api/deploy/infra         → Fetch sip-deploy commit + FreeSwitch version
POST /api/deploy/snapshots    → Auto-save snapshot on Load
GET /api/deploy/snapshots     → List saved snapshots
DELETE /api/deploy/snapshots/{id} → Delete snapshot
```

## Data Models (models.py)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `RepoInfo` | Discovered git repo | name, path, current_branch, has_uncommitted |
| `TagInfo` | Git tag metadata | name, commit_hash, date, is_release |
| `CommitInfo` | Single commit | hash, short_hash, message, author, date, linear_keys |
| `RepoSelection` | User's tag range choice | repo_name, from_tag, to_tag |
| `RepoReport` | Report for one repo | repo_name, from_tag, to_tag, commits, linear_keys |
| `ReleaseReport` | Full aggregated report | generated_at, root_dir, repos[], all_linear_keys[] |
| `Release` | Saved release | id, name, created_at, report |
| `RemoteRepo` | Remote git repo config | id, url, name, source_repo, group, note |
| `DeployComponent` | Single deployed component | name, tag, file, author, updated_at |
| `DeploySnapshot` | Saved deploy state | id, cluster, name, components[], infra, commit_* |
| `AppConfig` | Application settings | git_username, git_token, linear_api_key, remote_repos[] |

## Services

### remote.py
- `load_config() / save_config()` — JSON config persistence (`~/.release-manager/repos/config.json`)
- `load_snapshots() / save_snapshots()` — Deploy snapshots persistence (`snapshots.json`)
- `clone_repo() / sync_repo()` — Clone or fetch+pull remote repos (HTTPS + token auth)
- `get_repo_path()` — Resolve filesystem path for a repo

### deploy.py
- `fetch_deployed_versions()` — GitHub API: list cluster dirs, extract image.tag from YAML files
- `fetch_infra_info()` — GitHub API: latest sip-deploy commit + FreeSwitch version
- `_get_last_commit_info()` — Per-component: who last modified + when
- `_scan_extra_components()` — Extract versions from specific files (e.g. rasa-oss from rasa_server_values.yaml)

### git_ops.py
- `get_tags()` — All tags sorted by date + build number descending
- `fetch_and_pull()` — `git fetch --tags` + `git pull`
- `get_commits_between_tags()` — Commits in range (from_tag, to_tag]
- `check_for_newer_tags()` — Find newer release tags after a given tag

### parser.py
- `extract_linear_keys()` — Regex extraction, uppercase normalization, deduplication

### exporter.py
- `to_csv() / to_markdown() / to_json()` — Export ReleaseReport in various formats

## Component Groups

Repos can have a `group` field (e.g. `"RASA"`) for visual separation in tables. Repos with `source_repo` set are aliases — they use another repo's clone for tags/commits (e.g. `action-server` and `rasa-oss` both point to `rasa`).

Source-only repos (referenced by `source_repo` but not directly displayed) are hidden from the Repositories table.

## State Management

- **No database.** Single-user tool uses `app.state` (in-memory) + JSON files on disk.
- `app.state.templates` — Jinja2Templates instance
- `app.state.last_report` — Last generated ReleaseReport
- `app.state.releases` — Saved releases (in-memory)
- `app.state.deploy_snapshots` — Deploy snapshots (persisted to `snapshots.json`)
- `app.state.app_config` — AppConfig (persisted to `config.json`)

## Configuration

Pydantic Settings with `RM_` env prefix:

| Setting | Env Var | Default |
|---------|---------|---------|
| host | `RM_HOST` | `127.0.0.1` |
| port | `RM_PORT` | `8000` |
| default_root_dir | `RM_DEFAULT_ROOT_DIR` | `~/Work` |
| repos_dir | `RM_REPOS_DIR` | `~/.release-manager/repos` |
| git_username | `RM_GIT_USERNAME` | (empty) |
| git_token | `RM_GIT_TOKEN` | (empty) |

Credentials are also stored in `config.json` and can be set via the Repositories page UI.

## Persistence

| Data | File | Location |
|------|------|----------|
| Repo list, credentials | `config.json` | `~/.release-manager/repos/` |
| Deploy snapshots | `snapshots.json` | `~/.release-manager/repos/` |
| Cloned repos | `{repo-name}/` dirs | `~/.release-manager/repos/` |

## Testing Strategy

- **52 unit tests** across 5 test files
- Git operations: mocked `git.Repo` (via `unittest.mock.patch`)
- Deploy service: mocked GitHub API (`_github_get`)
- Remote service: `tmp_path` fixture for file I/O
- Parser: pure input/output (no mocks)
- Smoke test (`test_sync_check.py`): verifies all repos cloned + have tags (run manually after Sync All)
- Run: `make test` or `uv run pytest tests/ -v`

## Safety Constraints

- **No `git commit` or `git push`** — only read operations + `fetch`/`pull`
- `fetch_and_pull()` and `sync_repo()` are the only write-adjacent operations
- All repo URLs use HTTPS with token auth (no SSH)
- Detached HEAD and missing tracking branch are handled gracefully

## Commands

```bash
make setup    # uv sync --all-extras
make run      # uv run python -m release_manager (localhost:8000)
make test     # uv run pytest tests/ -v
make lint     # uv run ruff check src/ tests/
```