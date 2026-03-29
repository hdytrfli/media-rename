"""Tests for MKV processor module."""

import tempfile
from pathlib import Path

import pytest

from extractsub.mkv_processor import (
    extract_subtitles,
    find_mkv_files,
    process_path,
    sanitize_filename,
)
from extractsub.models import Status


class TestFindMkvFiles:
    """Tests for find_mkv_files function."""

    def test_finds_mkv_files(self, tmp_path):
        """Should find MKV files in directory."""
        (tmp_path / "movie1.mkv").touch()
        (tmp_path / "movie2.mkv").touch()
        (tmp_path / "other.txt").touch()

        result = find_mkv_files(tmp_path)
        assert len(result) == 2
        assert all(f.suffix == ".mkv" for f in result)

    def test_returns_empty_if_no_mkv(self, tmp_path):
        """Should return empty list if no MKV files."""
        (tmp_path / "file.txt").touch()
        (tmp_path / "file.mp4").touch()

        result = find_mkv_files(tmp_path)
        assert len(result) == 0

    def test_returns_sorted_files(self, tmp_path):
        """Should return files sorted by name."""
        (tmp_path / "z_movie.mkv").touch()
        (tmp_path / "a_movie.mkv").touch()
        (tmp_path / "m_movie.mkv").touch()

        result = find_mkv_files(tmp_path)
        assert result[0].name == "a_movie.mkv"
        assert result[1].name == "m_movie.mkv"
        assert result[2].name == "z_movie.mkv"


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Normal Title", "Normal Title"),
            ("Title: Subtitle", "Title_ Subtitle"),
            ("Title<With>Special", "Title_With_Special"),
            ("Path\\With\\Backslash", "Path_With_Backslash"),
            ("Path/With/Slash", "Path_With_Slash"),
            ("Question?Mark", "Question_Mark"),
            ("Star*Asterisk", "Star_Asterisk"),
            ("Pipe|Symbol", "Pipe_Symbol"),
        ],
    )
    def test_sanitizes_special_characters(self, name, expected):
        """Should remove invalid filename characters."""
        assert sanitize_filename(name) == expected


class TestExtractSubtitles:
    """Tests for extract_subtitles function."""

    def test_returns_error_no_mkv(self, tmp_path):
        """Should return error for nonexistent file."""
        result = extract_subtitles(tmp_path / "nonexistent.mkv")
        assert result.status == Status.ERROR_NO_MKV

    def test_dry_run_returns_tracks(self, tmp_path, monkeypatch):
        """Should return track info in dry-run mode."""
        mkv_file = tmp_path / "test.mkv"
        mkv_file.touch()

        def mock_probe(path):
            return [
                {
                    "id": 1,
                    "codec": "SRT",
                    "language": "eng",
                    "title": "",
                    "forced": False,
                    "default": True,
                }
            ], True

        monkeypatch.setattr("extractsub.mkv_processor.probe_mkv_file", mock_probe)
        monkeypatch.setattr("extractsub.mkv_processor.check_mkvtoolnix_installed", lambda: True)

        result = extract_subtitles(mkv_file, dry_run=True)
        assert result.status == Status.DRY_RUN
        assert len(result.subtitle_tracks) == 1
        assert result.subtitle_tracks[0].track_id == 1
        assert result.subtitle_tracks[0].language == "eng"

    def test_skips_no_subtitles(self, tmp_path, monkeypatch):
        """Should skip file with no subtitle tracks."""
        mkv_file = tmp_path / "test.mkv"
        mkv_file.touch()

        def mock_probe(path):
            return [], False

        monkeypatch.setattr("extractsub.mkv_processor.probe_mkv_file", mock_probe)
        monkeypatch.setattr("extractsub.mkv_processor.check_mkvtoolnix_installed", lambda: True)

        result = extract_subtitles(mkv_file, dry_run=True)
        assert result.status == Status.SKIPPED_NO_SUBS
        assert len(result.subtitle_tracks) == 0


class TestProcessPath:
    """Tests for process_path function."""

    def test_processes_multiple_mkv_files(self, tmp_path, monkeypatch):
        """Should process multiple MKV files."""
        (tmp_path / "movie1.mkv").touch()
        (tmp_path / "movie2.mkv").touch()
        (tmp_path / "movie3.mkv").touch()

        def mock_extract(path, output_dir=None, track_ids=None, dry_run=True, remove_original=False):
            from extractsub.models import ExtractResult
            return ExtractResult(path, None, [], Status.DRY_RUN)

        monkeypatch.setattr("extractsub.mkv_processor.extract_subtitles", mock_extract)

        results = process_path(tmp_path)
        assert len(results) == 3
        assert all(r.status == Status.DRY_RUN for r in results)

    def test_ignores_non_mkv_files(self, tmp_path, monkeypatch):
        """Should ignore non-MKV files."""
        (tmp_path / "movie.mkv").touch()
        (tmp_path / "video.mp4").touch()
        (tmp_path / "file.txt").touch()

        def mock_extract(path, output_dir=None, track_ids=None, dry_run=True, remove_original=False):
            from extractsub.models import ExtractResult
            return ExtractResult(path, None, [], Status.DRY_RUN)

        monkeypatch.setattr("extractsub.mkv_processor.extract_subtitles", mock_extract)

        results = process_path(tmp_path)
        assert len(results) == 1
        assert results[0].file_path.name == "movie.mkv"

    def test_raises_on_nonexistent_path(self):
        """Should raise FileNotFoundError for nonexistent path."""
        with pytest.raises(FileNotFoundError):
            process_path(Path("/nonexistent/path"))

    def test_processes_single_mkv_file(self, tmp_path, monkeypatch):
        """Should process single MKV file."""
        mkv_file = tmp_path / "movie.mkv"
        mkv_file.touch()

        def mock_extract(path, output_dir=None, track_ids=None, dry_run=True, remove_original=False):
            from extractsub.models import ExtractResult
            return ExtractResult(path, None, [], Status.DRY_RUN)

        monkeypatch.setattr("extractsub.mkv_processor.extract_subtitles", mock_extract)

        results = process_path(mkv_file)
        assert len(results) == 1
        assert results[0].status == Status.DRY_RUN

    def test_returns_empty_for_non_mkv_file(self, tmp_path, monkeypatch):
        """Should return empty list for non-MKV file."""
        txt_file = tmp_path / "file.txt"
        txt_file.write_text("test")

        results = process_path(txt_file)
        assert len(results) == 0

    def test_respects_show_progress_false(self, tmp_path, monkeypatch):
        """Should work without progress bar."""
        (tmp_path / "movie.mkv").touch()

        def mock_extract(path, output_dir=None, track_ids=None, dry_run=True, remove_original=False):
            from extractsub.models import ExtractResult
            return ExtractResult(path, None, [], Status.DRY_RUN)

        monkeypatch.setattr("extractsub.mkv_processor.extract_subtitles", mock_extract)

        results = process_path(tmp_path, show_progress=False)
        assert len(results) == 1
