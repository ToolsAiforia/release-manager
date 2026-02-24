import json
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import git

from release_manager.models import AppConfig, RemoteRepo

CONFIG_FILE = "config.json"


def _resolve_dir(repos_dir: str) -> Path:
    """Resolve ~ and return Path, creating directory if needed."""
    path = Path(repos_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_config(repos_dir: str) -> AppConfig:
    """Load app config from JSON file. Returns defaults if file doesn't exist."""
    config_path = _resolve_dir(repos_dir) / CONFIG_FILE
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return AppConfig(**data)
    return AppConfig()


def save_config(repos_dir: str, config: AppConfig) -> None:
    """Save app config to JSON file."""
    config_path = _resolve_dir(repos_dir) / CONFIG_FILE
    data = config.model_dump(mode="json")
    config_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def repo_name_from_url(url: str) -> str:
    """Extract repo name from a git URL."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    name = path.rsplit("/", 1)[-1]
    return name or "repo"


def _auth_url(url: str, username: str, token: str) -> str:
    """Inject credentials into an HTTPS git URL."""
    if not username or not token:
        return url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return url
    auth_url = f"{parsed.scheme}://{username}:{token}@{parsed.hostname}"
    if parsed.port:
        auth_url += f":{parsed.port}"
    auth_url += parsed.path
    return auth_url


def clone_repo(
    url: str, repos_dir: str, username: str, token: str
) -> str:
    """Clone a remote repo into repos_dir. Returns local path."""
    base = _resolve_dir(repos_dir)
    name = repo_name_from_url(url)
    local_path = base / name

    auth = _auth_url(url, username, token)
    git.Repo.clone_from(auth, str(local_path))
    return str(local_path)


def sync_repo(
    repo_name: str,
    repos_dir: str,
    username: str,
    token: str,
    url: str,
    local_path: str | None = None,
) -> str:
    """Fetch + pull an existing cloned repo. Returns status message."""
    if local_path:
        repo_dir = Path(local_path)
    else:
        base = _resolve_dir(repos_dir)
        repo_dir = base / repo_name

    if not repo_dir.exists():
        if local_path:
            return "Error: local directory missing"
        # Re-clone if directory was deleted
        auth = _auth_url(url, username, token)
        git.Repo.clone_from(auth, str(repo_dir))
        return "Cloned fresh"

    repo = git.Repo(str(repo_dir))

    # Update remote URL with current credentials (skip for local imports)
    if not local_path and url:
        auth = _auth_url(url, username, token)
        if repo.remotes:
            with repo.remotes.origin.config_writer as cw:
                cw.set("url", auth)

    # Fetch all remotes with tags
    messages: list[str] = []
    for remote in repo.remotes:
        try:
            remote.fetch(tags=True)
            messages.append("Fetch OK")
        except git.GitCommandError as e:
            messages.append(f"Fetch error: {e}")

    # Pull if tracking branch exists
    try:
        if not repo.head.is_detached and repo.active_branch.tracking_branch():
            repo.remotes.origin.pull()
            messages.append("Pull OK")
        else:
            messages.append("Pull skipped (no tracking branch)")
    except (git.GitCommandError, TypeError) as e:
        messages.append(f"Pull error: {e}")

    return "; ".join(messages)


def remove_repo(
    repo_name: str, repos_dir: str, is_local_import: bool = False
) -> None:
    """Remove a cloned repo directory. Skips deletion for local imports."""
    if is_local_import:
        return
    base = _resolve_dir(repos_dir)
    local_path = base / repo_name
    if local_path.exists():
        shutil.rmtree(local_path)


def get_repo_path(
    repo_name: str, repos_dir: str, local_path: str | None = None
) -> str:
    """Get the local filesystem path for a remote repo."""
    if local_path:
        return local_path
    base = _resolve_dir(repos_dir)
    return str(base / repo_name)


def get_origin_url(repo_path: str) -> str | None:
    """Extract the origin remote URL from a local git repo."""
    try:
        repo = git.Repo(repo_path)
        if repo.remotes:
            return repo.remotes.origin.url
    except Exception:
        pass
    return None
