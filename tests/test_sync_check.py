"""Smoke test: verify all configured repos can load tags after sync.

Run manually after Sync All: pytest tests/test_sync_check.py -v
Skipped in CI (requires cloned repos).
"""

import json
import os
from pathlib import Path

import pytest

from release_manager.services import git_ops, remote
from release_manager.settings import settings


REPOS_DIR = os.path.expanduser("~/.release-manager/repos")
CONFIG_PATH = Path(REPOS_DIR) / "config.json"


def _load_repos():
    if not CONFIG_PATH.exists():
        return []
    data = json.loads(CONFIG_PATH.read_text())
    return data.get("remote_repos", [])


def _repo_ids():
    repos = _load_repos()
    return [
        pytest.param(r["name"], id=r["name"])
        for r in repos
        if not r.get("source_repo")  # skip aliases like action-server, rasa-oss
    ]


@pytest.mark.skipif(
    not CONFIG_PATH.exists(),
    reason="No config.json — run in dev environment only",
)
class TestRepoTagsAfterSync:
    @pytest.mark.parametrize("repo_name", _repo_ids())
    def test_repo_has_been_cloned(self, repo_name):
        repos = _load_repos()
        entry = next(r for r in repos if r["name"] == repo_name)
        repo_path = remote.get_repo_path(
            repo_name, settings.repos_dir, entry.get("local_path")
        )
        assert Path(repo_path).exists(), (
            f"{repo_name} not cloned at {repo_path} — run Sync All first"
        )

    @pytest.mark.parametrize("repo_name", _repo_ids())
    def test_repo_has_tags(self, repo_name):
        repos = _load_repos()
        entry = next(r for r in repos if r["name"] == repo_name)
        repo_path = remote.get_repo_path(
            repo_name, settings.repos_dir, entry.get("local_path")
        )
        if not Path(repo_path).exists():
            pytest.skip(f"{repo_name} not cloned yet")
        tags = git_ops.get_tags(repo_path)
        assert len(tags) > 0, f"{repo_name} has no tags"

    @pytest.mark.parametrize("repo_name", _repo_ids())
    def test_tags_sorted_newest_first(self, repo_name):
        repos = _load_repos()
        entry = next(r for r in repos if r["name"] == repo_name)
        repo_path = remote.get_repo_path(
            repo_name, settings.repos_dir, entry.get("local_path")
        )
        if not Path(repo_path).exists():
            pytest.skip(f"{repo_name} not cloned yet")
        tags = git_ops.get_tags(repo_path)
        if len(tags) < 2:
            pytest.skip(f"{repo_name} has fewer than 2 tags")
        # First tag should be newest
        assert tags[0].date >= tags[1].date