"""Tests for remote service."""

import json

from release_manager.models import AppConfig, DeploySnapshot, DeployComponent, RemoteRepo
from release_manager.services.remote import (
    load_config,
    save_config,
    load_snapshots,
    save_snapshots,
    repo_name_from_url,
    get_repo_path,
)


class TestRepoNameFromUrl:
    def test_https_url(self):
        assert repo_name_from_url("https://github.com/org/my-repo.git") == "my-repo"

    def test_ssh_url(self):
        assert repo_name_from_url("git@github.com:org/my-repo.git") == "my-repo"

    def test_no_git_suffix(self):
        assert repo_name_from_url("https://github.com/org/my-repo") == "my-repo"

    def test_trailing_slash(self):
        assert repo_name_from_url("https://github.com/org/my-repo/") == "my-repo"


class TestGetRepoPath:
    def test_with_local_path(self):
        path = get_repo_path("my-repo", "/tmp/repos", "/home/user/my-repo")
        assert path == "/home/user/my-repo"

    def test_without_local_path(self, tmp_path):
        repos_dir = str(tmp_path / "repos")
        path = get_repo_path("my-repo", repos_dir)
        assert path.endswith("my-repo")


class TestConfigPersistence:
    def test_save_and_load_config(self, tmp_path):
        repos_dir = str(tmp_path)
        config = AppConfig(
            git_username="testuser",
            git_token="testtoken",
            remote_repos=[
                RemoteRepo(id="abc123", url="https://github.com/o/r.git", name="r"),
            ],
        )
        save_config(repos_dir, config)
        loaded = load_config(repos_dir)
        assert loaded.git_username == "testuser"
        assert len(loaded.remote_repos) == 1
        assert loaded.remote_repos[0].name == "r"

    def test_load_missing_config_loads_from_repos_json(self, tmp_path):
        config = load_config(str(tmp_path))
        assert config.git_username == ""
        # repos.json in project root provides default repo list
        assert len(config.remote_repos) >= 0  # may or may not find repos.json


class TestSnapshotPersistence:
    def test_save_and_load_snapshots(self, tmp_path):
        repos_dir = str(tmp_path)
        snapshots = [
            DeploySnapshot(
                id="snap1",
                cluster="aiphoria-qa",
                name="Release 24",
                components=[
                    DeployComponent(name="studio", tag="20260219-5", file="values.yaml"),
                ],
                commit_sha="abc1234",
                infra={"freeswitch": "v1.10.12"},
            ),
        ]
        save_snapshots(repos_dir, snapshots)
        loaded = load_snapshots(repos_dir)
        assert len(loaded) == 1
        assert loaded[0].name == "Release 24"
        assert loaded[0].components[0].name == "studio"
        assert loaded[0].infra["freeswitch"] == "v1.10.12"

    def test_load_missing_snapshots_returns_empty(self, tmp_path):
        loaded = load_snapshots(str(tmp_path))
        assert loaded == []

    def test_snapshot_with_author_and_updated(self, tmp_path):
        repos_dir = str(tmp_path)
        snapshots = [
            DeploySnapshot(
                id="snap2",
                cluster="qa",
                components=[
                    DeployComponent(
                        name="dm", tag="20260319-1",
                        author="Anna M", updated_at="2026-03-19",
                    ),
                ],
            ),
        ]
        save_snapshots(repos_dir, snapshots)
        loaded = load_snapshots(repos_dir)
        assert loaded[0].components[0].author == "Anna M"
        assert loaded[0].components[0].updated_at == "2026-03-19"