from pathlib import Path
from unittest.mock import MagicMock, patch

from release_manager.services.scanner import scan_repos


class TestScanRepos:
    def test_empty_directory(self, tmp_path):
        result = scan_repos(str(tmp_path))
        assert result == []

    def test_nonexistent_directory(self):
        result = scan_repos("/nonexistent/path")
        assert result == []

    def test_skips_hidden_directories(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        result = scan_repos(str(tmp_path))
        assert result == []

    def test_skips_non_git_directories(self, tmp_path):
        (tmp_path / "not-a-repo").mkdir()
        result = scan_repos(str(tmp_path))
        assert result == []

    @patch("release_manager.services.scanner.Repo")
    def test_finds_git_repos(self, mock_repo_cls, tmp_path):
        repo_dir = tmp_path / "my-service"
        repo_dir.mkdir()

        mock_repo = MagicMock()
        mock_repo.active_branch.name = "main"
        mock_repo.is_dirty.return_value = False
        mock_repo_cls.return_value = mock_repo

        result = scan_repos(str(tmp_path))
        assert len(result) == 1
        assert result[0].name == "my-service"
        assert result[0].current_branch == "main"
        assert result[0].has_uncommitted is False

    @patch("release_manager.services.scanner.Repo")
    def test_detects_dirty_repo(self, mock_repo_cls, tmp_path):
        repo_dir = tmp_path / "dirty-repo"
        repo_dir.mkdir()

        mock_repo = MagicMock()
        mock_repo.active_branch.name = "feature"
        mock_repo.is_dirty.return_value = True
        mock_repo_cls.return_value = mock_repo

        result = scan_repos(str(tmp_path))
        assert result[0].has_uncommitted is True

    @patch("release_manager.services.scanner.Repo")
    def test_sorted_by_name(self, mock_repo_cls, tmp_path):
        for name in ["zebra", "alpha", "middle"]:
            (tmp_path / name).mkdir()

        mock_repo = MagicMock()
        mock_repo.active_branch.name = "main"
        mock_repo.is_dirty.return_value = False
        mock_repo_cls.return_value = mock_repo

        result = scan_repos(str(tmp_path))
        names = [r.name for r in result]
        assert names == ["alpha", "middle", "zebra"]
