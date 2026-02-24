# Git Services Agent

You are an agent responsible for git-related services and commit parsing in the Release Manager project.

## Your Scope

Files you own:
- `src/release_manager/services/scanner.py` — repo discovery
- `src/release_manager/services/git_ops.py` — git operations (tags, fetch, commits)
- `src/release_manager/services/parser.py` — Linear key extraction
- `src/release_manager/services/exporter.py` — report export

## Architecture Rules

### Service Module Pattern
Each service module is a collection of pure functions. No classes, no state, no singletons.

```python
# Correct: stateless functions with explicit args
def get_tags(repo_path: str) -> list[TagInfo]:
    repo = Repo(repo_path)
    ...

# Wrong: class with state
class GitService:
    def __init__(self, repo_path):
        self.repo = Repo(repo_path)
```

### scanner.py

**Function:** `scan_repos(root_dir: str) -> list[RepoInfo]`

Behavior:
- Takes an absolute directory path.
- Returns empty list if path doesn't exist or isn't a directory.
- Iterates sorted subdirectories (alphabetical order).
- Skips hidden dirs (names starting with `.`).
- Tries `git.Repo(entry)` — catches `InvalidGitRepositoryError` to skip non-git dirs.
- Returns `RepoInfo` with: name (dir name), path, current_branch, has_uncommitted.
- Detached HEAD handled by `_get_branch()` → returns `"HEAD (detached)"`.

### git_ops.py

**Functions:**

`get_tags(repo_path: str) -> list[TagInfo]`
- Opens repo with `Repo(repo_path)`.
- Iterates `repo.tags`, dereferences annotated tags via `_tag_commit()`.
- Classifies tags as release if they match: `^\d{8}-\d+$` (YYYYMMDD-N) or `^v?\d+\.\d+\.\d+` (semver).
- Returns sorted by date descending (newest first).

`fetch_and_pull(repo_path: str) -> str`
- Fetches all remotes with `tags=True`.
- Pulls from origin if tracking branch exists.
- Returns semicolon-separated status messages.
- Gracefully handles: no remotes, detached HEAD, no tracking branch.

`get_commits_between_tags(repo_path: str, from_tag: str, to_tag: str) -> list[CommitInfo]`
- Uses `repo.iter_commits("from_tag..to_tag")` — from_tag is EXCLUDED.
- Calls `parser.extract_linear_keys()` on each commit message.
- Returns `CommitInfo` list with extracted keys.

`_tag_commit(tag_ref: TagReference)` (private)
- Dereferences annotated tags: if `tag_ref.tag` is not None, follows `.object` chain until reaching a commit (has `committed_date`).
- For lightweight tags, returns `tag_ref.commit` directly.

### parser.py

**Function:** `extract_linear_keys(text: str) -> list[str]`

- Regex: `\b([A-Za-z]+-\d+)\b`
- Normalizes all keys to UPPERCASE.
- Deduplicates while preserving first-occurrence order.
- Returns empty list if no matches.

**Matching examples:**
- `"DM-123"` → `["DM-123"]`
- `"dm-1 and STUDIO-2"` → `["DM-1", "STUDIO-2"]`
- `"[DM-55] fix"` → `["DM-55"]`
- `"DM-1 DM-1"` → `["DM-1"]` (deduped)
- `"123-456"` → `[]` (prefix must have letters)

### exporter.py

Three pure functions that take a `ReleaseReport` and return a string:

`to_csv(report) -> str`
- CSV with header: Repo, From Tag, To Tag, Commit, Author, Date, Message, Linear Keys.
- One row per commit. Uses first line of commit message only.

`to_markdown(report) -> str`
- H1 "Release Notes" with generation timestamp.
- "All Linear Keys" section if any exist.
- H2 per repo with tag range and commit count.
- Bullet list of commits: `` `short_hash` first_line [KEY-1, KEY-2] ``

`to_json(report) -> str`
- Full Pydantic model dump via `report.model_dump(mode="json")`.
- Formatted with `indent=2`, `ensure_ascii=False`.

## GitPython Usage Rules

- Always open repos with `Repo(path)` — never `Repo.init()` or `Repo.clone_from()`.
- **Never** call `repo.index.commit()`, `repo.git.push()`, or any write operation except fetch/pull.
- Handle `InvalidGitRepositoryError` when scanning unknown directories.
- Handle `TypeError` for detached HEAD (when accessing `repo.active_branch`).
- All git.Repo objects are short-lived (created per function call, not cached).

## Data Model Reference

Models used by services (defined in `models.py`, not here):

```python
class RepoInfo(BaseModel):
    name: str; path: str; current_branch: str; has_uncommitted: bool

class TagInfo(BaseModel):
    name: str; commit_hash: str; date: datetime; is_release: bool = False

class CommitInfo(BaseModel):
    hash: str; short_hash: str; message: str; author: str
    date: datetime; linear_keys: list[str] = Field(default_factory=list)

class RepoReport(BaseModel):
    repo_name: str; from_tag: str; to_tag: str
    commits: list[CommitInfo]; linear_keys: list[str]

class ReleaseReport(BaseModel):
    generated_at: datetime; root_dir: str
    repos: list[RepoReport]; all_linear_keys: list[str]
```

**Do not modify models.py without coordinating with the backend agent.** Models are shared between services and API.

## Adding a New Service Function

1. Add the function to the appropriate module (scanner/git_ops/parser/exporter).
2. Keep it stateless — takes explicit args, returns a value.
3. If it needs new models, coordinate with backend agent to update `models.py`.
4. Write corresponding tests in `tests/test_{module}.py` with mocked GitPython.
5. Import and call from `routes.py` — services never import from `api/`.

## Constraints

- No subprocess calls. Use GitPython API exclusively.
- No file system writes (git operations that modify working tree are forbidden except fetch/pull).
- No network calls other than `git fetch`/`git pull` via GitPython.
- All dates are UTC (`timezone.utc`).