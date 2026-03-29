'''
ExtractSub - Extract embedded subtitles from MKV files.
'''

from extractsub.models import Status, ExtractResult, SubtitleTrack
from extractsub.mkv_processor import (
    find_mkv_files,
    check_mkvtoolnix_installed,
    probe_mkv_file,
    extract_subtitles,
    process_path,
)
from extractsub.subtitle_naming import get_lang_code, get_subtitle_tags, build_subtitle_filename
from extractsub.cli import main

__version__ = "1.0.0"
__all__ = [
    "Status",
    "ExtractResult",
    "SubtitleTrack",
    "find_mkv_files",
    "check_mkvtoolnix_installed",
    "probe_mkv_file",
    "extract_subtitles",
    "process_path",
    "get_lang_code",
    "get_subtitle_tags",
    "build_subtitle_filename",
    "main",
]
