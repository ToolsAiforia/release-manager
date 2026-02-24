---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Python Code Style

## Formatting
- Line length: 88 characters max
- 4-space indentation
- No trailing whitespace
- One blank line between functions within a class, two between top-level definitions

## Naming
- `snake_case` for functions, variables, modules
- `PascalCase` for classes and Pydantic models
- `UPPER_SNAKE_CASE` for module-level constants
- Prefix private helpers with `_` (e.g., `_tag_commit`)

## Imports
- Order: stdlib → third-party → local, each group separated by a blank line
- Use `from` imports for specific items: `from release_manager.models import RepoInfo`
- Never use `import *`

## Type Hints
- All function signatures must have type hints (args + return)
- Python 3.12+ syntax allowed: `str | None` instead of `Optional[str]`
- Use `list[str]` not `List[str]`

## Functions
- Keep functions short and focused (single responsibility)
- Services are stateless pure functions — no classes, no state
- Routes are thin: validate → call service → return response
- No docstrings on test methods or routes — names should be self-documenting
