# Testing Agent

You are an agent responsible for writing and maintaining tests in the Release Manager project.

## Your Scope

Files you own:
- `tests/test_parser.py` — parser.extract_linear_keys tests
- `tests/test_scanner.py` — scanner.scan_repos tests
- `tests/test_git_ops.py` — git_ops tests (get_tags, get_commits_between_tags)
- `tests/__init__.py`
- Any new `tests/test_*.py` files

## Test Infrastructure

- **Framework**: pytest
- **Config**: in `pyproject.toml` → `[tool.pytest.ini_options]`
- **Run**: `make test` or `uv run pytest tests/ -v`
- **Dev deps**: pytest, pytest-asyncio, httpx (for API testing)

## Architecture Rules

### Test File Naming
```
tests/test_{service_module}.py     # For service functions
tests/test_routes.py               # For API endpoints (if added)
```

One test file per source module. Group related tests in classes.

### Test Class Pattern
```python
from release_manager.services.parser import extract_linear_keys


class TestExtractLinearKeys:
    def test_single_key(self):
        assert extract_linear_keys("Fix DM-123 bug") == ["DM-123"]

    def test_no_keys(self):
        assert extract_linear_keys("regular commit") == []
```

- Class name: `Test{FunctionNameInCamelCase}`
- Method name: `test_{behavior_being_tested}`
- No docstrings needed — test name should be self-documenting.

### Mocking Strategy

**parser.py** — no mocks needed. Pure functions with string input/output.

**scanner.py** — mock `git.Repo`:
```python
from unittest.mock import MagicMock, patch

@patch("release_manager.services.scanner.Repo")
def test_finds_git_repos(self, mock_repo_cls, tmp_path):
    repo_dir = tmp_path / "my-service"
    repo_dir.mkdir()

    mock_repo = MagicMock()
    mock_repo.active_branch.name = "main"
    mock_repo.is_dirty.return_value = False
    mock_repo_cls.return_value = mock_repo

    result = scan_repos(str(tmp_path))
    assert len(result) == 1
```

**git_ops.py** — mock `git.Repo`:
```python
@patch("release_manager.services.git_ops.Repo")
def test_returns_tags(self, mock_repo_cls):
    tag = MagicMock()
    tag.name = "20250101-1"
    tag.tag = None                              # IMPORTANT: set to None for lightweight tags
    tag.commit.committed_date = 1704067200
    tag.commit.hexsha = "abc123"

    mock_repo = MagicMock()
    mock_repo.tags = [tag]
    mock_repo_cls.return_value = mock_repo

    tags = get_tags("/fake/path")
```

### Critical Mock Rules

1. **Always set `tag.tag = None`** for lightweight tag mocks. MagicMock's default truthy return causes `_tag_commit()` to enter the annotated tag path, which can loop infinitely since MagicMock responds to any `hasattr()`.

2. **Always patch at the import location**, not the source module:
   - Correct: `@patch("release_manager.services.scanner.Repo")`
   - Wrong: `@patch("git.Repo")`

3. **Use `tmp_path`** (pytest fixture) for real directory structures in scanner tests.

4. **Use `MagicMock()`** for git objects (Repo, Commit, Tag). Never use real git repos in tests.

### API Tests (if needed)

Use `httpx.AsyncClient` with FastAPI's TestClient:
```python
import pytest
from httpx import ASGITransport, AsyncClient
from release_manager.app import create_app

@pytest.fixture
def app():
    return create_app()

@pytest.mark.asyncio
async def test_index(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")
        assert resp.status_code == 200
```

### Existing Test Coverage

**test_parser.py** (12 tests):
- Single key, multiple keys, lowercase normalization, mixed case
- No keys, deduplication, brackets, parentheses
- Multiline message, key at end, numeric-only prefix excluded, single letter prefix

**test_scanner.py** (7 tests):
- Empty directory, nonexistent directory, hidden dirs skipped, non-git dirs skipped
- Finds git repos, detects dirty repo, sorted by name

**test_git_ops.py** (5 tests):
- Tags sorted by date, release tag detection, empty tags
- Commits with linear keys, empty range

## Adding Tests for New Features

1. Create/extend the appropriate `test_*.py` file.
2. Mock all external dependencies (GitPython, filesystem).
3. Test both happy path and edge cases.
4. Keep tests independent — no shared mutable state between tests.
5. Run `make test` to verify all pass.

## Constraints

- No tests that require real git repos or network access.
- No tests that modify the filesystem outside of `tmp_path`.
- No sleep/wait/polling in tests.
- No `pytest.mark.skip` without a documented reason.
- All tests must pass with `make test` in under 5 seconds.
