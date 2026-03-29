"""Tests for SRT processor module."""

import tempfile
from pathlib import Path

import pytest

from offsetsub.srt_processor import (
    find_srt_files,
    format_timestamp,
    offset_srt_content,
    parse_timestamp,
    process_path,
    process_srt_file,
)
from offsetsub.models import Status


class TestFindSrtFiles:
    """Tests for find_srt_files function."""

    def test_finds_single_file(self, tmp_path):
        """Should find single SRT file."""
        srt_file = tmp_path / "test.srt"
        srt_file.touch()
        
        result = find_srt_files(srt_file)
        assert len(result) == 1
        assert result[0] == srt_file

    def test_ignores_non_srt_file(self, tmp_path):
        """Should ignore non-SRT file."""
        txt_file = tmp_path / "test.txt"
        txt_file.touch()
        
        result = find_srt_files(txt_file)
        assert len(result) == 0

    def test_finds_multiple_files_in_dir(self, tmp_path):
        """Should find multiple SRT files in directory."""
        (tmp_path / "sub1.srt").touch()
        (tmp_path / "sub2.srt").touch()
        (tmp_path / "other.txt").touch()
        
        result = find_srt_files(tmp_path)
        assert len(result) == 2

    def test_returns_empty_for_empty_dir(self, tmp_path):
        """Should return empty list for directory with no SRT files."""
        (tmp_path / "file.txt").touch()
        
        result = find_srt_files(tmp_path)
        assert len(result) == 0


class TestParseTimestamp:
    """Tests for parse_timestamp function."""

    @pytest.mark.parametrize(
        "timestamp,expected",
        [
            ("00:00:00,000", 0),
            ("00:00:01,000", 1000),
            ("00:01:00,000", 60000),
            ("01:00:00,000", 3600000),
            ("00:00:00,500", 500),
            ("00:01:23,456", 83456),
            ("01:23:45,678", 5025678),
            ("00:00:00.000", 0),
            ("00:00:01.500", 1500),
        ],
    )
    def test_parse_valid_timestamps(self, timestamp, expected):
        """Should parse valid timestamps correctly."""
        assert parse_timestamp(timestamp) == expected

    def test_parse_invalid_timestamp(self):
        """Should raise error for invalid timestamp."""
        with pytest.raises(ValueError):
            parse_timestamp("invalid")


class TestFormatTimestamp:
    """Tests for format_timestamp function."""

    @pytest.mark.parametrize(
        "ms,expected",
        [
            (0, "00:00:00,000"),
            (1000, "00:00:01,000"),
            (60000, "00:01:00,000"),
            (3600000, "01:00:00,000"),
            (500, "00:00:00,500"),
            (83456, "00:01:23,456"),
            (5025678, "01:23:45,678"),
        ],
    )
    def test_format_valid_timestamps(self, ms, expected):
        """Should format milliseconds correctly."""
        assert format_timestamp(ms) == expected

    def test_format_negative_ms(self):
        """Should clamp negative values to 0."""
        assert format_timestamp(-1000) == "00:00:00,000"


class TestOffsetSrtContent:
    """Tests for offset_srt_content function."""

    def test_positive_offset(self):
        """Should delay subtitles with positive offset."""
        content = """1
00:00:01,000 --> 00:00:03,000
Hello World

2
00:00:04,000 --> 00:00:06,000
Test subtitle
"""
        result, count = offset_srt_content(content, 500)
        
        assert count == 2
        assert "00:00:01,500 --> 00:00:03,500" in result
        assert "00:00:04,500 --> 00:00:06,500" in result

    def test_negative_offset(self):
        """Should sync earlier with negative offset."""
        content = """1
00:00:01,500 --> 00:00:03,500
Hello World
"""
        result, count = offset_srt_content(content, -500)
        
        assert count == 1
        assert "00:00:01,000 --> 00:00:03,000" in result

    def test_negative_clamped_to_zero(self):
        """Should clamp negative results to 0."""
        content = """1
00:00:00,500 --> 00:00:01,500
Hello World
"""
        result, count = offset_srt_content(content, -1000)
        
        assert count == 1
        assert "00:00:00,000 --> 00:00:00,500" in result

    def test_preserves_text(self):
        """Should preserve subtitle text."""
        content = """1
00:00:01,000 --> 00:00:03,000
Hello World
With multiple lines
"""
        result, count = offset_srt_content(content, 100)
        
        assert "Hello World" in result
        assert "With multiple lines" in result


class TestProcessSrtFile:
    """Tests for process_srt_file function."""

    def test_dry_run_does_not_write(self, tmp_path):
        """Should not write file in dry-run mode."""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:01,000 --> 00:00:03,000\nTest\n")
        
        result = process_srt_file(srt_file, 500, dry_run=True)
        
        assert result.status == Status.DRY_RUN
        assert result.cues_modified == 1

    def test_applies_offset(self, tmp_path):
        """Should apply offset to file."""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:01,000 --> 00:00:03,000\nTest\n")
        
        result = process_srt_file(srt_file, 500, dry_run=False)
        
        assert result.status == Status.OFFSET
        assert result.cues_modified == 1
        
        content = result.output_path.read_text()
        assert "00:00:01,500" in content

    def test_returns_error_for_missing_file(self, tmp_path):
        """Should return error for missing file."""
        result = process_srt_file(tmp_path / "nonexistent.srt", 500)
        assert result.status == Status.ERROR_FILE


class TestProcessPath:
    """Tests for process_path function."""

    def test_processes_single_file(self, tmp_path, monkeypatch):
        """Should process single SRT file."""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:01,000 --> 00:00:03,000\nTest\n")
        
        results = process_path(srt_file, 500)
        
        assert len(results) == 1
        assert results[0].status == Status.DRY_RUN

    def test_processes_directory(self, tmp_path):
        """Should process all SRT files in directory."""
        (tmp_path / "sub1.srt").write_text("1\n00:00:01,000 --> 00:00:03,000\nTest\n")
        (tmp_path / "sub2.srt").write_text("1\n00:00:01,000 --> 00:00:03,000\nTest\n")
        
        results = process_path(tmp_path, 500)
        
        assert len(results) == 2

    def test_returns_empty_for_no_srt(self, tmp_path):
        """Should return empty list for no SRT files."""
        (tmp_path / "file.txt").touch()
        
        results = process_path(tmp_path, 500)
        assert len(results) == 0

    def test_raises_on_nonexistent_path(self):
        """Should raise FileNotFoundError for nonexistent path."""
        with pytest.raises(FileNotFoundError):
            process_path(Path("/nonexistent/path"), 500)
