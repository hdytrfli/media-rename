"""Tests for folder processor module."""

import tempfile
from pathlib import Path

import pytest

from nforename.folder_processor import (
    format_name_with_year,
    has_year_in_name,
    process_folder,
    process_path,
)
from nforename.models import MediaType, Status

MOVIE_XML = '<?xml version="1.0" encoding="utf-8"?><movie><year>2020</year></movie>'


class TestHasYearInName:
    """Tests for has_year_in_name function."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Movie (2020)", True),
            ("Show (1999)", True),
            ("Movie (2020) ", True),
            ("Movie", False),
            ("Movie 2020", False),
            ("(2020) Movie", False),
            ("Movie (20)", False),
            ("Movie (20202)", False),
        ],
    )
    def test_year_detection(self, name, expected):
        """Should correctly detect year in folder name."""
        assert has_year_in_name(name) == expected


class TestFormatNameWithYear:
    """Tests for format_name_with_year function."""

    def test_formats_correctly(self):
        """Should format name with year correctly."""
        result = format_name_with_year("Movie", "2020")
        assert result == "Movie (2020)"

    def test_handles_special_characters(self):
        """Should handle special characters in name."""
        result = format_name_with_year("Movie: The Sequel", "2020")
        assert result == "Movie: The Sequel (2020)"


class TestProcessFolder:
    """Tests for process_folder function."""

    def test_skips_no_nfo(self, tmp_path):
        """Should skip folder with no .nfo file."""
        folder = tmp_path / "test"
        folder.mkdir()
        result = process_folder(folder)
        assert result.status == Status.SKIPPED_NO_NFO

    def test_skips_has_year(self, tmp_path):
        """Should skip folder that already has year."""
        folder = tmp_path / "Movie (2020)"
        folder.mkdir()
        (folder / "movie.nfo").write_text(MOVIE_XML, encoding="utf-8")
        result = process_folder(folder)
        assert result.status == Status.SKIPPED_HAS_YEAR

    def test_dry_run_does_not_rename(self, tmp_path):
        """Should not rename folder in dry-run mode."""
        folder = tmp_path / "Movie"
        folder.mkdir()
        (folder / "movie.nfo").write_text(MOVIE_XML, encoding="utf-8")
        result = process_folder(folder, dry_run=True)
        assert result.status == Status.DRY_RUN
        assert folder.exists()
        assert not (tmp_path / "Movie (2020)").exists()

    def test_rename_changes_folder(self, tmp_path):
        """Should rename folder when not in dry-run mode."""
        folder = tmp_path / "Movie"
        folder.mkdir()
        (folder / "movie.nfo").write_text(MOVIE_XML, encoding="utf-8")
        result = process_folder(folder, dry_run=False)
        assert result.status == Status.RENAMED
        assert not folder.exists()
        assert (tmp_path / "Movie (2020)").exists()

    def test_conflict_when_destination_exists(self, tmp_path):
        """Should return conflict error when destination exists."""
        folder = tmp_path / "Movie"
        folder.mkdir()
        (folder / "movie.nfo").write_text(MOVIE_XML, encoding="utf-8")
        (tmp_path / "Movie (2020)").mkdir()
        result = process_folder(folder, dry_run=False)
        assert result.status == Status.ERROR_CONFLICT


class TestProcessPath:
    """Tests for process_path function."""

    def test_processes_multiple_folders(self, tmp_path):
        """Should process multiple folders in directory."""
        for name in ["Movie1", "Movie2", "Movie3"]:
            folder = tmp_path / name
            folder.mkdir()
            (folder / "movie.nfo").write_text(MOVIE_XML, encoding="utf-8")

        results = process_path(tmp_path)
        assert len(results) == 3
        assert all(r.status == Status.DRY_RUN for r in results)

    def test_ignores_files(self, tmp_path):
        """Should ignore files in directory."""
        (tmp_path / "file.txt").write_text("test")
        folder = tmp_path / "Movie"
        folder.mkdir()
        (folder / "movie.nfo").write_text(
            "<?xml?><movie><year>2020</year></movie>", encoding="utf-8"
        )

        results = process_path(tmp_path)
        assert len(results) == 1

    def test_raises_on_nonexistent_path(self):
        """Should raise FileNotFoundError for nonexistent path."""
        with pytest.raises(FileNotFoundError):
            process_path(Path("/nonexistent/path"))

    def test_processes_single_folder(self, tmp_path):
        """Should process single folder with .nfo file."""
        folder = tmp_path / "Movie"
        folder.mkdir()
        (folder / "movie.nfo").write_text(MOVIE_XML, encoding="utf-8")

        results = process_path(folder)
        assert len(results) == 1
        assert results[0].status == Status.DRY_RUN

    def test_returns_empty_for_file_path(self, tmp_path):
        """Should return empty list for file path."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        results = process_path(file_path)
        assert len(results) == 0

    def test_processes_folder_without_nfo_returns_skipped(self, tmp_path):
        """Should process single folder without .nfo and return skipped."""
        folder = tmp_path / "Movie"
        folder.mkdir()

        results = process_path(folder)
        assert len(results) == 1
        assert results[0].status == Status.SKIPPED_NO_NFO
