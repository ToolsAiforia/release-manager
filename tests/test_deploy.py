"""Tests for deploy service."""

import base64
import json
from unittest.mock import patch

from release_manager.services.deploy import (
    IMAGE_TAG_RE,
    EXTRA_FILE_COMPONENTS,
    _get_tag_commit_info,
    _scan_extra_components,
    fetch_deployed_versions,
    fetch_infra_info,
)


class TestImageTagRegex:
    def test_matches_standard_image_tag(self):
        content = "image:\n  repository: foo\n  tag: 20260221-3\n"
        match = IMAGE_TAG_RE.search(content)
        assert match
        assert match.group(1) == "20260221-3"

    def test_matches_tag_with_fix_suffix(self):
        content = "image:\n  tag: 20260305-2-fix1\n"
        match = IMAGE_TAG_RE.search(content)
        assert match
        assert match.group(1) == "20260305-2-fix1"

    def test_no_match_without_image_block(self):
        content = "tag: 20260221-3\nother: value\n"
        match = IMAGE_TAG_RE.search(content)
        assert match is None


class TestExtraFileComponents:
    def test_rasa_oss_defined(self):
        names = [e["name"] for e in EXTRA_FILE_COMPONENTS]
        assert "rasa-oss" in names

    def test_rasa_oss_points_to_rasa_dir(self):
        for e in EXTRA_FILE_COMPONENTS:
            if e["name"] == "rasa-oss":
                assert e["dir"] == "rasa"
                assert e["file"] == "rasa_server_values.yaml"


class TestFetchDeployedVersions:
    @patch("release_manager.services.deploy._github_get")
    def test_returns_components_with_tags(self, mock_get):
        mock_get.side_effect = self._mock_github_api
        result = fetch_deployed_versions(
            "owner", "repo", "clusters/qa", "token"
        )
        assert result["commit"]["sha"] == "abc1234"
        names = [c["name"] for c in result["components"]]
        assert "dialog-manager" in names
        # extra component rasa-oss should be present
        assert "rasa-oss" in names

    @patch("release_manager.services.deploy._github_get")
    def test_empty_commits_returns_empty(self, mock_get):
        mock_get.return_value = []
        result = fetch_deployed_versions(
            "owner", "repo", "clusters/qa", "token"
        )
        assert result["components"] == []
        assert result["commit"] is None

    @patch("release_manager.services.deploy._github_get")
    def test_passes_branch_to_commits(self, mock_get):
        calls = []

        def tracking(url, token):
            calls.append(url)
            return self._mock_github_api(url, token)

        mock_get.side_effect = tracking
        fetch_deployed_versions(
            "owner", "repo", "clusters/qa", "token", branch="dev"
        )
        commits_calls = [u for u in calls if "/commits?" in u]
        assert any("sha=dev" in u for u in commits_calls)

    @patch("release_manager.services.deploy._github_get")
    def test_without_branch_no_sha_param(self, mock_get):
        calls = []

        def tracking(url, token):
            calls.append(url)
            return self._mock_github_api(url, token)

        mock_get.side_effect = tracking
        fetch_deployed_versions("owner", "repo", "clusters/qa", "token")
        # First commits call (for cluster dir discovery) should not have sha=
        first_commits = next(u for u in calls if "/commits?" in u)
        assert "sha=" not in first_commits

    @patch("release_manager.services.deploy._github_get")
    def test_components_have_author_and_date(self, mock_get):
        mock_get.side_effect = self._mock_github_api
        result = fetch_deployed_versions(
            "owner", "repo", "clusters/qa", "token"
        )
        dm = next(c for c in result["components"] if c["name"] == "dialog-manager")
        assert dm["author"] == "Test User"
        assert dm["updated_at"] == "2026-04-01"

    def _mock_github_api(self, url, token):
        if "commits?" in url:
            return [{
                "sha": "abc1234567890",
                "commit": {
                    "message": "Update tag",
                    "author": {"name": "Test User"},
                    "committer": {"date": "2026-04-01T10:00:00Z"},
                },
                "html_url": "https://github.com/o/r/commit/abc1234",
            }]
        if "contents/clusters/qa?" in url:
            return [
                {"name": "dialog-manager", "type": "dir"},
                {"name": "rasa", "type": "dir"},
            ]
        if "contents/clusters/qa/dialog-manager" in url and "ref=" in url:
            return [
                {
                    "name": "values.yaml",
                    "type": "file",
                    "url": "https://api.github.com/file/dm-values",
                }
            ]
        if "contents/clusters/qa/rasa?" in url:
            return [
                {
                    "name": "rasa_action_server_values.yaml",
                    "type": "file",
                    "url": "https://api.github.com/file/rasa-action",
                },
                {
                    "name": "rasa_server_values.yaml",
                    "type": "file",
                    "url": "https://api.github.com/file/rasa-server",
                },
            ]
        if "file/dm-values" in url:
            content = base64.b64encode(
                b"image:\n  repository: dm\n  tag: 20260319-1\n"
            ).decode()
            return {"content": content}
        if "file/rasa-action" in url:
            content = base64.b64encode(
                b"image:\n  tag: 20260113-1\n"
            ).decode()
            return {"content": content}
        if "file/rasa-server" in url:
            content = base64.b64encode(
                b"image:\n  tag: 20251205-1\n"
            ).decode()
            return {"content": content}
        if "contents/clusters/qa/rasa/rasa_server_values.yaml" in url:
            content = base64.b64encode(
                b"image:\n  tag: 20251205-1\n"
            ).decode()
            return {"content": content}
        return []


class TestGetTagCommitInfo:
    @patch("release_manager.services.deploy._github_get")
    def test_finds_commit_by_tag_in_diff(self, mock_get):
        commits_list = [
            {
                "url": "https://api.github.com/repos/o/r/commits/aaa",
                "commit": {
                    "message": "reduce replicas",
                    "author": {"name": "Other"},
                    "committer": {"date": "2026-03-20T12:00:00Z"},
                },
            },
            {
                "url": "https://api.github.com/repos/o/r/commits/bbb",
                "commit": {
                    "message": "Update image tag",
                    "author": {"name": "Anna M"},
                    "committer": {"date": "2026-02-11T10:00:00Z"},
                },
            },
        ]
        commit_detail_aaa = {"files": [{"patch": "@@ -1 +1 @@\n-replicas: 2\n+replicas: 1"}]}
        commit_detail_bbb = {"files": [{"patch": "@@ -1 +1 @@\n-  tag: 20260101-1\n+  tag: 20260211-1"}]}

        def side_effect(url, token):
            if "commits?" in url:
                return commits_list
            if "commits/aaa" in url:
                return commit_detail_aaa
            if "commits/bbb" in url:
                return commit_detail_bbb
            return []

        mock_get.side_effect = side_effect
        author, date = _get_tag_commit_info(
            "https://api.github.com/repos/o/r",
            "clusters/qa/dm/values.yaml",
            "20260211-1",
            "token",
            "abc",
        )
        assert author == "Anna M"
        assert date == "2026-02-11"

    @patch("release_manager.services.deploy._github_get")
    def test_falls_back_to_latest_commit(self, mock_get):
        mock_get.return_value = [{
            "commit": {
                "message": "unrelated change",
                "author": {"name": "Bob"},
                "committer": {"date": "2026-03-15T12:00:00Z"},
            }
        }]
        author, date = _get_tag_commit_info(
            "https://api.github.com/repos/o/r",
            "clusters/qa/dm/values.yaml",
            "20260211-1",
            "token",
            "abc",
        )
        assert author == "Bob"
        assert date == "2026-03-15"

    @patch("release_manager.services.deploy._github_get")
    def test_returns_none_on_error(self, mock_get):
        mock_get.side_effect = Exception("API error")
        author, date = _get_tag_commit_info(
            "https://api.github.com/repos/o/r",
            "clusters/qa/dm/values.yaml",
            "20260211-1",
            "token",
            "ref",
        )
        assert author is None
        assert date is None

    def test_returns_none_without_file_path(self):
        author, date = _get_tag_commit_info(
            "https://api.github.com/repos/o/r", None, "20260211-1", "token", "ref"
        )
        assert author is None
        assert date is None


class TestScanExtraComponents:
    @patch("release_manager.services.deploy._github_get")
    def test_extracts_rasa_oss_tag(self, mock_get):
        content = base64.b64encode(
            b"image:\n  tag: 20251205-1\n"
        ).decode()
        mock_get.return_value = {"content": content}
        extras = _scan_extra_components(
            "https://api.github.com/repos/o/r", "clusters/qa", "token", "abc"
        )
        assert len(extras) >= 1
        rasa_oss = next(e for e in extras if e["name"] == "rasa-oss")
        assert rasa_oss["tag"] == "20251205-1"
        assert rasa_oss["file"] == "rasa_server_values.yaml"

    @patch("release_manager.services.deploy._github_get")
    def test_handles_api_error_gracefully(self, mock_get):
        mock_get.side_effect = Exception("Not found")
        extras = _scan_extra_components(
            "https://api.github.com/repos/o/r", "clusters/qa", "token", "abc"
        )
        assert len(extras) >= 1
        rasa_oss = next(e for e in extras if e["name"] == "rasa-oss")
        assert rasa_oss["tag"] is None


class TestFetchInfraInfo:
    def _mock_github(self, until=None):
        """Return a side_effect function that validates until parameter."""
        def side_effect(url, token):
            # Verify until is passed to commits endpoint
            if "commits?" in url and until:
                assert f"until={until}" in url, (
                    f"Expected until={until} in URL: {url}"
                )

            if "commits?" in url:
                return [{
                    "sha": "abc1234567890",
                    "commit": {
                        "message": "Update adapter",
                        "author": {"name": "Test"},
                        "committer": {"date": "2026-03-15T10:00:00Z"},
                    },
                    "html_url": "https://github.com/acclaim-ai/sip-deploy/commit/abc",
                }]
            if "playbook.yml" in url:
                content = base64.b64encode(
                    b"adapter_git_version: v1.7.2\n"
                ).decode()
                return {"content": content}
            if "ansible-role-fsgrpc/defaults/main.yml" in url:
                content = base64.b64encode(
                    b"freeswitch_version: 1.10.12\n"
                ).decode()
                return {"content": content}
            if "/tags" in url:
                return [{"name": "v1.0.0"}]
            return []
        return side_effect

    @patch("release_manager.services.deploy._github_get")
    def test_returns_sip_proxy_version(self, mock_get):
        mock_get.side_effect = self._mock_github()
        result = fetch_infra_info("token")
        assert result["sip_proxy_version"] == "v1.7.2"

    @patch("release_manager.services.deploy._github_get")
    def test_returns_freeswitch_version(self, mock_get):
        mock_get.side_effect = self._mock_github()
        result = fetch_infra_info("token")
        assert result["freeswitch_version"] == "1.10.12"

    @patch("release_manager.services.deploy._github_get")
    def test_returns_sip_deploy_commit(self, mock_get):
        mock_get.side_effect = self._mock_github()
        result = fetch_infra_info("token")
        assert result["sip_deploy"] is not None
        assert result["sip_deploy"]["sha"] == "abc1234"

    @patch("release_manager.services.deploy._github_get")
    def test_returns_sip_deploy_tag(self, mock_get):
        mock_get.side_effect = self._mock_github()
        result = fetch_infra_info("token")
        assert result["sip_deploy_tag"] == "v1.0.0"

    @patch("release_manager.services.deploy._github_get")
    def test_passes_until_date_to_commits(self, mock_get):
        mock_get.side_effect = self._mock_github(until="2026-03-15T23:59:59Z")
        result = fetch_infra_info("token", until="2026-03-15")
        assert result["sip_deploy"] is not None

    @patch("release_manager.services.deploy._github_get")
    def test_without_until_no_date_filter(self, mock_get):
        mock_get.side_effect = self._mock_github()
        result = fetch_infra_info("token")
        # Should still work without until
        assert result["sip_proxy_version"] == "v1.7.2"

    @patch("release_manager.services.deploy._github_get")
    def test_files_fetched_at_commit_ref(self, mock_get):
        """Verify playbook.yml and defaults/main.yml are fetched at the commit ref."""
        calls = []
        original = self._mock_github()
        def tracking_side_effect(url, token):
            calls.append(url)
            return original(url, token)
        mock_get.side_effect = tracking_side_effect

        fetch_infra_info("token")

        playbook_calls = [u for u in calls if "playbook.yml" in u]
        assert len(playbook_calls) == 1
        assert "ref=abc1234567890" in playbook_calls[0]

        fsgrpc_calls = [u for u in calls if "ansible-role-fsgrpc" in u]
        assert len(fsgrpc_calls) == 1
        assert "ref=abc1234567890" in fsgrpc_calls[0]