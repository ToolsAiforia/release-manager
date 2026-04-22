"""Tests for GitHub PR key enrichment."""

from unittest.mock import patch

from release_manager.services.github_pr import (
    enrich_commits_with_pr_keys,
    get_merged_pr_keys,
    get_repo_owner_name,
)


class TestGetRepoOwnerName:
    def test_https_url(self):
        result = get_repo_owner_name("https://github.com/acclaim-ai/studio.git")
        assert result == ("acclaim-ai", "studio")

    def test_without_git_suffix(self):
        result = get_repo_owner_name("https://github.com/acclaim-ai/studio")
        assert result == ("acclaim-ai", "studio")

    def test_trailing_slash(self):
        result = get_repo_owner_name("https://github.com/org/repo/")
        assert result == ("org", "repo")


class TestGetMergedPrKeys:
    @patch("release_manager.services.github_pr._github_get")
    def test_extracts_keys_from_merged_prs(self, mock_get):
        mock_get.return_value = [
            {
                "title": "ATEAM-620: add visual indicator",
                "body": "Also fixes DDEV-333",
                "merged_at": "2026-03-15T10:00:00Z",
                "merge_commit_sha": "abc123",
            },
            {
                "title": "chore: update deps",
                "body": None,
                "merged_at": "2026-03-14T10:00:00Z",
                "merge_commit_sha": "def456",
            },
        ]
        result = get_merged_pr_keys(
            "org", "repo", "2026-03-01", "2026-03-31", "token"
        )
        assert "abc123" in result
        assert "ATEAM-620" in result["abc123"]
        # DDEV-333 is in body only, not title — should NOT be included
        assert "DDEV-333" not in result["abc123"]
        assert "def456" not in result  # no keys in title

    @patch("release_manager.services.github_pr._github_get")
    def test_skips_unmerged_prs(self, mock_get):
        mock_get.return_value = [
            {
                "title": "PLCORE-978: fix",
                "body": "",
                "merged_at": None,
                "merge_commit_sha": "abc123",
            },
        ]
        result = get_merged_pr_keys(
            "org", "repo", "2026-03-01", "2026-03-31", "token"
        )
        assert result == {}

    @patch("release_manager.services.github_pr._github_get")
    def test_stops_at_older_dates(self, mock_get):
        mock_get.return_value = [
            {
                "title": "PLCORE-100: new",
                "body": "",
                "merged_at": "2026-03-15T10:00:00Z",
                "merge_commit_sha": "aaa",
            },
            {
                "title": "PLCORE-50: old",
                "body": "",
                "merged_at": "2026-02-01T10:00:00Z",
                "merge_commit_sha": "bbb",
            },
        ]
        result = get_merged_pr_keys(
            "org", "repo", "2026-03-01", "2026-03-31", "token"
        )
        assert "aaa" in result
        assert "bbb" not in result

    @patch("release_manager.services.github_pr._github_get")
    def test_handles_api_error(self, mock_get):
        mock_get.side_effect = Exception("API error")
        result = get_merged_pr_keys(
            "org", "repo", "2026-03-01", "2026-03-31", "token"
        )
        assert result == {}

    @patch("release_manager.services.github_pr._github_get")
    def test_skips_release_prs(self, mock_get):
        mock_get.return_value = [
            {
                "title": "Release 0.7.0",
                "body": "PLCORE-986 PLCORE-1008 DDEV-266",
                "merged_at": "2026-03-15T10:00:00Z",
                "merge_commit_sha": "abc123",
            },
        ]
        result = get_merged_pr_keys(
            "org", "repo", "2026-03-01", "2026-03-31", "token"
        )
        assert result == {}

    @patch("release_manager.services.github_pr._github_get")
    def test_skips_maintenance_prs(self, mock_get):
        mock_get.return_value = [
            {
                "title": "MAINTENANCE: Update deps",
                "body": "",
                "merged_at": "2026-03-15T10:00:00Z",
                "merge_commit_sha": "abc123",
            },
        ]
        result = get_merged_pr_keys(
            "org", "repo", "2026-03-01", "2026-03-31", "token"
        )
        assert result == {}

    @patch("release_manager.services.github_pr._github_get")
    def test_no_dash_format_in_pr_title(self, mock_get):
        mock_get.return_value = [
            {
                "title": "Plcore 978 fix multilang",
                "body": "",
                "merged_at": "2026-03-15T10:00:00Z",
                "merge_commit_sha": "abc123",
            },
        ]
        result = get_merged_pr_keys(
            "org", "repo", "2026-03-01", "2026-03-31", "token"
        )
        assert "abc123" in result
        assert "PLCORE-978" in result["abc123"]


class TestEnrichCommitsWithPrKeys:
    @patch("release_manager.services.github_pr.get_merged_pr_keys")
    def test_adds_keys_to_matching_commits(self, mock_pr_keys):
        mock_pr_keys.return_value = {"abc123": ["ATEAM-620"]}
        commits = [
            {"hash": "abc123", "linear_keys": []},
            {"hash": "def456", "linear_keys": []},
        ]
        result = enrich_commits_with_pr_keys(
            commits, "org", "repo", "token",
            from_date="2026-03-01", to_date="2026-03-31",
        )
        assert "ATEAM-620" in result[0]["linear_keys"]
        assert result[1]["linear_keys"] == []

    @patch("release_manager.services.github_pr.get_merged_pr_keys")
    def test_does_not_duplicate_existing_keys(self, mock_pr_keys):
        mock_pr_keys.return_value = {"abc123": ["ATEAM-620"]}
        commits = [
            {"hash": "abc123", "linear_keys": ["ATEAM-620"]},
        ]
        result = enrich_commits_with_pr_keys(
            commits, "org", "repo", "token",
            from_date="2026-03-01", to_date="2026-03-31",
        )
        assert result[0]["linear_keys"].count("ATEAM-620") == 1

    def test_skips_without_dates(self):
        commits = [{"hash": "abc123", "linear_keys": []}]
        result = enrich_commits_with_pr_keys(
            commits, "org", "repo", "token"
        )
        assert result[0]["linear_keys"] == []