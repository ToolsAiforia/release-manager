---
name: review
description: Review recent code changes for quality, bugs, and style
argument-hint: "[file_or_path]"
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob
---

# Code Review

Review code for quality, correctness, and style compliance.

## Steps

1. **Gather changes:**
   - If `$ARGUMENTS` is a file path, review that file
   - Otherwise, run `git diff` to find uncommitted changes
   - If no uncommitted changes, review the last commit: `git diff HEAD~1`

2. **Review checklist:**
   - Correctness: logic bugs, edge cases, off-by-one errors
   - Type safety: missing type hints, wrong types
   - Error handling: unhandled exceptions, missing validation
   - Security: injection risks, unescaped user input
   - Style: naming conventions, import order, line length (88 chars)
   - Tests: are changed functions covered by tests?

3. **Report format:**
   - List issues grouped by severity: Critical / Warning / Suggestion
   - For each issue: file:line, description, suggested fix
   - If no issues found, confirm the code looks good

Do NOT make changes — only report findings.
