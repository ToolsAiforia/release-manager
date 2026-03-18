import re
from datetime import datetime, timezone
from pathlib import Path

from git import Repo, TagReference

from release_manager.models import CommitInfo, TagInfo
from release_manager.services.parser import extract_linear_keys

RELEASE_TAG_RE = re.compile(r"^\d{8}-\d+$")
SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+")


def get_tags(repo_path: str) -> list[TagInfo]:
    """Return tags sorted by date descending (newest first)."""
    repo = Repo(repo_path)
    tags: list[TagInfo] = []

    for tag_ref in repo.tags:
        commit = _tag_commit(tag_ref)
        tag_date = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
        name = tag_ref.name
        is_release = bool(RELEASE_TAG_RE.match(name) or SEMVER_RE.match(name))
        tags.append(
            TagInfo(
                name=name,
                commit_hash=commit.hexsha,
                date=tag_date,
                is_release=is_release,
            )
        )

    tags.sort(key=lambda t: t.date, reverse=True)
    return tags


def fetch_and_pull(repo_path: str) -> str:
    """Run git fetch --tags and git pull. Return status message."""
    repo = Repo(repo_path)
    messages: list[str] = []

    try:
        for remote in repo.remotes:
            remote.fetch(tags=True)
        messages.append("Fetch OK")
    except Exception as exc:
        messages.append(f"Fetch error: {exc}")

    try:
        if repo.active_branch.tracking_branch():
            repo.remotes.origin.pull()
            messages.append("Pull OK")
        else:
            messages.append("No tracking branch, pull skipped")
    except TypeError:
        messages.append("Detached HEAD, pull skipped")
    except Exception as exc:
        messages.append(f"Pull error: {exc}")

    return "; ".join(messages)


def get_commits_between_tags(
    repo_path: str, from_tag: str, to_tag: str
) -> list[CommitInfo]:
    """Return commits in range (from_tag, to_tag] — from_tag excluded."""
    repo = Repo(repo_path)
    rev_range = f"{from_tag}..{to_tag}"
    commits: list[CommitInfo] = []

    for commit in repo.iter_commits(rev_range):
        msg = commit.message.strip()
        keys = extract_linear_keys(msg)
        commits.append(
            CommitInfo(
                hash=commit.hexsha,
                short_hash=commit.hexsha[:7],
                message=msg,
                author=str(commit.author),
                date=datetime.fromtimestamp(
                    commit.committed_date, tz=timezone.utc
                ),
                linear_keys=keys,
            )
        )

    return commits


def check_for_newer_tags(
    repo_path: str, current_to_tag: str
) -> TagInfo | None:
    """Return the newest release tag after current_to_tag, or None."""
    tags = get_tags(repo_path)
    current_idx: int | None = None
    for i, t in enumerate(tags):
        if t.name == current_to_tag:
            current_idx = i
            break
    if current_idx is None:
        return None
    # Tags before current_idx are newer (list sorted newest-first).
    # Return first release tag found.
    for t in tags[:current_idx]:
        if t.is_release:
            return t
    return None


def _tag_commit(tag_ref: TagReference):
    """Dereference annotated tags to their commit."""
    obj = tag_ref.tag
    if obj is not None:
        # Annotated tag — dereference to commit
        while hasattr(obj, "object") and not hasattr(obj, "committed_date"):
            obj = obj.object
        return obj
    return tag_ref.commit
