---
name: test
description: Run tests and report results. Use after code changes.
argument-hint: "[test_name_pattern]"
user-invocable: true
allowed-tools: Bash, Read, Grep
---

# Run Tests

Run the project test suite and report results.

## Without arguments
Run the full suite:
```
make test
```

## With arguments
If `$ARGUMENTS` is provided, run matching tests:
```
uv run pytest tests/ -v -k "$ARGUMENTS"
```

## After running
1. Report pass/fail count
2. If any tests fail, read the failing test file and the source it tests
3. Suggest a fix for the failure
4. Do NOT automatically apply fixes — describe them and wait for confirmation
