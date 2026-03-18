from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, patch

from release_manager.services.git_ops import (
    check_for_newer_tags,
    get_commits_between_tags,
    get_tags,
)


class TestGetTags:
    @patch("release_manager.services.git_ops.Repo")
    def test_returns_tags_sorted_by_date(self, mock_repo_cls):
        tag1 = MagicMock()
        tag1.name = "20250101-1"
        tag1.tag = None
        tag1.commit.committed_date = 1704067200  # 2024-01-01
        tag1.commit.hexsha = "aaa"

        tag2 = MagicMock()
        tag2.name = "20250201-1"
        tag2.tag = None
        tag2.commit.committed_date = 1706745600  # 2024-02-01
        tag2.commit.hexsha = "bbb"

        mock_repo = MagicMock()
        mock_repo.tags = [tag1, tag2]
        mock_repo_cls.return_value = mock_repo

        tags = get_tags("/fake/path")
        assert len(tags) == 2
        assert tags[0].name == "20250201-1"  # newest first
        assert tags[1].name == "20250101-1"

    @patch("release_manager.services.git_ops.Repo")
    def test_release_tag_detection(self, mock_repo_cls):
        release_tag = MagicMock()
        release_tag.name = "20250115-3"
        release_tag.tag = None
        release_tag.commit.committed_date = 1704067200
        release_tag.commit.hexsha = "aaa"

        semver_tag = MagicMock()
        semver_tag.name = "v1.2.3"
        semver_tag.tag = None
        semver_tag.commit.committed_date = 1704067201
        semver_tag.commit.hexsha = "bbb"

        other_tag = MagicMock()
        other_tag.name = "some-random-tag"
        other_tag.tag = None
        other_tag.commit.committed_date = 1704067202
        other_tag.commit.hexsha = "ccc"

        mock_repo = MagicMock()
        mock_repo.tags = [release_tag, semver_tag, other_tag]
        mock_repo_cls.return_value = mock_repo

        tags = get_tags("/fake/path")
        by_name = {t.name: t for t in tags}
        assert by_name["20250115-3"].is_release is True
        assert by_name["v1.2.3"].is_release is True
        assert by_name["some-random-tag"].is_release is False

    @patch("release_manager.services.git_ops.Repo")
    def test_empty_tags(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo.tags = []
        mock_repo_cls.return_value = mock_repo

        tags = get_tags("/fake/path")
        assert tags == []


class TestGetCommitsBetweenTags:
    @patch("release_manager.services.git_ops.Repo")
    def test_returns_commits_with_linear_keys(self, mock_repo_cls):
        commit1 = MagicMock()
        commit1.hexsha = "abcdef1234567890"
        commit1.message = "DM-123 Fix dialog flow"
        commit1.author = "Dev"
        commit1.committed_date = 1704067200

        commit2 = MagicMock()
        commit2.hexsha = "1234567890abcdef"
        commit2.message = "Regular commit no key"
        commit2.author = "Dev2"
        commit2.committed_date = 1704067100

        mock_repo = MagicMock()
        mock_repo.iter_commits.return_value = [commit1, commit2]
        mock_repo_cls.return_value = mock_repo

        commits = get_commits_between_tags("/fake", "tag1", "tag2")
        assert len(commits) == 2
        assert commits[0].linear_keys == ["DM-123"]
        assert commits[1].linear_keys == []
        mock_repo.iter_commits.assert_called_once_with("tag1..tag2")

    @patch("release_manager.services.git_ops.Repo")
    def test_empty_range(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo.iter_commits.return_value = []
        mock_repo_cls.return_value = mock_repo

        commits = get_commits_between_tags("/fake", "tag1", "tag2")
        assert commits == []


class TestCheckForNewerTags:
    @patch("release_manager.services.git_ops.Repo")
    def test_finds_newer_release_tag(self, mock_repo_cls):
        tag_new = MagicMock()
        tag_new.name = "20260225-1"
        tag_new.tag = None
        tag_new.commit.committed_date = 1740500000
        tag_new.commit.hexsha = "ccc"

        tag_current = MagicMock()
        tag_current.name = "20260220-1"
        tag_current.tag = None
        tag_current.commit.committed_date = 1740000000
        tag_current.commit.hexsha = "bbb"

        tag_old = MagicMock()
        tag_old.name = "20260215-1"
        tag_old.tag = None
        tag_old.commit.committed_date = 1739500000
        tag_old.commit.hexsha = "aaa"

        mock_repo = MagicMock()
        mock_repo.tags = [tag_new, tag_current, tag_old]
        mock_repo_cls.return_value = mock_repo

        result = check_for_newer_tags("/fake", "20260220-1")
        assert result is not None
        assert result.name == "20260225-1"

    @patch("release_manager.services.git_ops.Repo")
    def test_returns_none_when_no_newer_tags(self, mock_repo_cls):
        tag_current = MagicMock()
        tag_current.name = "20260220-1"
        tag_current.tag = None
        tag_current.commit.committed_date = 1740000000
        tag_current.commit.hexsha = "bbb"

        tag_old = MagicMock()
        tag_old.name = "20260215-1"
        tag_old.tag = None
        tag_old.commit.committed_date = 1739500000
        tag_old.commit.hexsha = "aaa"

        mock_repo = MagicMock()
        mock_repo.tags = [tag_current, tag_old]
        mock_repo_cls.return_value = mock_repo

        result = check_for_newer_tags("/fake", "20260220-1")
        assert result is None

    @patch("release_manager.services.git_ops.Repo")
    def test_returns_none_when_tag_not_found(self, mock_repo_cls):
        tag1 = MagicMock()
        tag1.name = "20260220-1"
        tag1.tag = None
        tag1.commit.committed_date = 1740000000
        tag1.commit.hexsha = "aaa"

        mock_repo = MagicMock()
        mock_repo.tags = [tag1]
        mock_repo_cls.return_value = mock_repo

        result = check_for_newer_tags("/fake", "nonexistent-tag")
        assert result is None

    @patch("release_manager.services.git_ops.Repo")
    def test_skips_non_release_tags(self, mock_repo_cls):
        tag_feature = MagicMock()
        tag_feature.name = "some-feature-tag"
        tag_feature.tag = None
        tag_feature.commit.committed_date = 1740500000
        tag_feature.commit.hexsha = "ccc"

        tag_current = MagicMock()
        tag_current.name = "20260220-1"
        tag_current.tag = None
        tag_current.commit.committed_date = 1740000000
        tag_current.commit.hexsha = "bbb"

        mock_repo = MagicMock()
        mock_repo.tags = [tag_feature, tag_current]
        mock_repo_cls.return_value = mock_repo

        result = check_for_newer_tags("/fake", "20260220-1")
        assert result is None
