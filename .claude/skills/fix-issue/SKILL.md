---
name: fix-issue
description: Investigate and fix a bug described by the user
argument-hint: "<description of the bug>"
user-invocable: true
disable-model-invocation: true
---

# Fix Issue

Investigate and fix the bug described in: $ARGUMENTS

## Process

1. **Understand** — parse the bug description, identify affected area (backend/frontend/services)
2. **Locate** — find relevant source files using Grep and Glob
3. **Reproduce** — if possible, identify what triggers the bug from the code
4. **Diagnose** — trace the execution path, find the root cause
5. **Fix** — implement the minimal fix that addresses the root cause
6. **Verify** — run `make test` to ensure nothing is broken
7. **Report** — summarize what was wrong and what was changed

## Rules
- Minimal changes only — fix the bug, don't refactor surrounding code
- If the fix touches a service function, check if tests need updating
- If unsure about the right approach, describe options before implementing
