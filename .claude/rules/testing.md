---
paths:
  - "tests/**/*.py"
---

# Testing Rules

## Framework
- pytest with pytest-asyncio
- Config in `pyproject.toml` → `[tool.pytest.ini_options]`
- Run: `make test` or `uv run pytest tests/ -v`

## File & Class Naming
- One test file per source module: `tests/test_{module}.py`
- Class name: `Test{FunctionNameInCamelCase}`
- Method name: `test_{behavior_being_tested}`
- No docstrings — test name should be self-documenting

## Mocking Strategy
- **parser.py** — no mocks, pure functions
- **scanner.py** — mock `git.Repo`, use `tmp_path` for directory structures
- **git_ops.py** — mock `git.Repo` with `MagicMock`
- Always patch at the import location: `@patch("release_manager.services.scanner.Repo")`
- Always set `tag.tag = None` for lightweight tag mocks (avoids infinite MagicMock loops)

## Constraints
- No real git repos or network access
- No filesystem writes outside `tmp_path`
- No `sleep`/`wait`/`polling`
- No `pytest.mark.skip` without documented reason
- All tests must pass in under 5 seconds
- Tests must be independent — no shared mutable state
