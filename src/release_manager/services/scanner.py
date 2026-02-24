from pathlib import Path

from git import InvalidGitRepositoryError, Repo

from release_manager.models import RepoInfo


def scan_repos(root_dir: str) -> list[RepoInfo]:
    """Scan subdirectories of root_dir for git repositories."""
    root = Path(root_dir)
    if not root.is_dir():
        return []

    repos: list[RepoInfo] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        try:
            repo = Repo(entry)
        except InvalidGitRepositoryError:
            continue

        repos.append(
            RepoInfo(
                name=entry.name,
                path=str(entry),
                current_branch=_get_branch(repo),
                has_uncommitted=repo.is_dirty(),
            )
        )
    return repos


def _get_branch(repo: Repo) -> str:
    try:
        return repo.active_branch.name
    except TypeError:
        return "HEAD (detached)"
