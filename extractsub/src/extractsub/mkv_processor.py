'''
MKV subtitle extraction utilities.
'''

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from tqdm import tqdm

from extractsub.models import ExtractResult, Status, SubtitleTrack


def find_mkv_files(path: Path) -> List[Path]:
    '''Find all MKV files in directory (non-recursive) or return single file.'''
    if path.is_file():
        if path.suffix.lower() == '.mkv':
            return [path]
        return []
    if path.is_dir():
        return sorted(path.glob("*.mkv"))
    return []


def check_mkvtoolnix_installed() -> bool:
    '''Check if mkvmerge is available in PATH.'''
    return shutil.which("mkvmerge") is not None


def get_mkvmerge_path() -> Optional[str]:
    '''Get the path to mkvmerge executable.'''
    return shutil.which("mkvmerge")


def probe_mkv_file(mkv_path: Path) -> Tuple[List[dict], bool]:
    '''
    Probe MKV file to get track information.
    
    Returns:
        Tuple of (list of subtitle track info, has_subtitles)
    '''
    mkvmerge = get_mkvmerge_path()
    if not mkvmerge:
        raise RuntimeError("mkvmerge not found")
    
    try:
        result = subprocess.run(
            [mkvmerge, "-J", str(mkv_path)],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        
        subtitle_tracks = []
        for track in data.get("tracks", []):
            if track.get("type") == "subtitles":
                codec = track.get("codec", "")
                subtitle_tracks.append({
                    "id": track.get("id", 0),
                    "codec": codec,
                    "language": track.get("language", "und"),
                    "title": track.get("track_name", ""),
                    "forced": track.get("forced", False),
                    "default": track.get("default_track", False),
                })
        
        return subtitle_tracks, len(subtitle_tracks) > 0
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to probe MKV: {e.stderr}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from mkvmerge: {e}")


def extract_subtitles(
    mkv_path: Path,
    output_dir: Optional[Path] = None,
    track_ids: Optional[List[int]] = None,
    dry_run: bool = False,
    remove_original: bool = False
) -> ExtractResult:
    '''
    Extract subtitles from MKV file.

    Args:
        mkv_path: Path to MKV file
        output_dir: Directory for extracted subtitles (default: same as MKV)
        track_ids: Specific track IDs to extract (default: all subtitle tracks)
        dry_run: If True, don't actually extract
        remove_original: If True, remove subtitles from original file after extraction

    Returns:
        ExtractResult with status and information
    '''
    mkv_path = mkv_path.resolve()
    
    if not mkv_path.exists():
        return ExtractResult(mkv_path, None, [], Status.ERROR_NO_MKV)
    
    if not check_mkvtoolnix_installed():
        raise RuntimeError("mkvmerge not found. Please install MKVToolNix.")
    
    try:
        subtitle_info, has_subs = probe_mkv_file(mkv_path)
    except RuntimeError as e:
        return ExtractResult(mkv_path, None, [], Status.ERROR_PROBE)
    
    if not has_subs:
        return ExtractResult(mkv_path, None, [], Status.SKIPPED_NO_SUBS)

    if track_ids is not None:
        subtitle_info = [t for t in subtitle_info if t["id"] in track_ids]
        if not subtitle_info:
            return ExtractResult(mkv_path, None, [], Status.ERROR_NO_SUBS)
    
    tracks = [
        SubtitleTrack(
            track_id=t["id"],
            language=t["language"],
            codec=t["codec"],
            title=t["title"] if t["title"] else None,
            is_forced=t["forced"],
            is_default=t["default"]
        )
        for t in subtitle_info
    ]
    
    if dry_run:
        return ExtractResult(mkv_path, output_dir, tracks, Status.DRY_RUN)

    output_dir = output_dir or mkv_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    mkvextract = shutil.which("mkvextract")
    if not mkvextract:
        return ExtractResult(mkv_path, None, tracks, Status.ERROR_EXTRACT)

    extracted_files = []
    for track in tracks:
        ext = _get_subtitle_extension(track.codec)
        video_name = _sanitize_video_name(mkv_path.stem)
        title_part = f".{sanitize_filename(track.title)}" if track.title else ""
        lang = track.language if track.language and track.language != "und" else ""
        lang_part = f".{lang}" if lang else ""
        output_name = f"{video_name}{lang_part}{title_part}{ext}"
        output_path = output_dir / output_name

        try:
            result = subprocess.run(
                [mkvextract, "tracks", str(mkv_path), f"{track.track_id}:{output_path}"],
                capture_output=True,
                text=True,
                check=True
            )
            extracted_files.append(output_path)
        except subprocess.CalledProcessError as e:
            return ExtractResult(mkv_path, None, tracks, Status.ERROR_EXTRACT)

    if remove_original:
        try:
            _remove_subtitles_from_file(mkv_path, [t.track_id for t in tracks])
        except RuntimeError:
            return ExtractResult(mkv_path, output_dir, tracks, Status.ERROR_EXTRACT)

    return ExtractResult(mkv_path, output_dir, tracks, Status.EXTRACTED)


def _remove_subtitles_from_file(mkv_path: Path, subtitle_track_ids: List[int]) -> None:
    '''
    Remove subtitle tracks from MKV file using mkvmerge.
    
    Args:
        mkv_path: Path to MKV file
        subtitle_track_ids: List of subtitle track IDs to remove (not used, all subtitles are removed)
    '''
    mkvmerge = shutil.which("mkvmerge")
    if not mkvmerge:
        raise RuntimeError("mkvmerge not found")

    temp_path = mkv_path.with_suffix(".mkv.tmp")
    
    try:
        result = subprocess.run(
            [
                mkvmerge, "-o", str(temp_path),
                "--no-subtitles",
                "--no-chapters", "--no-global-tags",
                str(mkv_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )

        mkv_path.unlink()
        temp_path.rename(mkv_path)
    except subprocess.CalledProcessError as e:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed to remove subtitles: {e.stderr}")


def _extract_with_mkvmerge(
    mkv_path: Path,
    output_dir: Path,
    tracks: List[SubtitleTrack]
) -> ExtractResult:
    '''Fallback extraction using mkvmerge remux.'''
    return ExtractResult(mkv_path, None, tracks, Status.ERROR_EXTRACT)


def _get_subtitle_extension(codec: str) -> str:
    '''Get file extension for subtitle codec.'''
    codec_lower = codec.lower()
    
    if "srt" in codec_lower or "subrip" in codec_lower:
        return ".srt"
    if "ass" in codec_lower or "ssa" in codec_lower:
        return ".ass"
    if "pgs" in codec_lower or "sup" in codec_lower:
        return ".sup"
    if "vobsub" in codec_lower:
        return ".idx"
    if "webvtt" in codec_lower or "vtt" in codec_lower:
        return ".vtt"
    if "ttf" in codec_lower or "tt" in codec_lower:
        return ".ttf"
    
    return ".sup"


def sanitize_filename(name: str) -> str:
    '''Remove invalid characters from filename.'''
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def _sanitize_video_name(name: str) -> str:
    '''
    Clean video filename by removing common quality/release group tags.
    
    Examples:
        "My.Show.S01E01.1080p.WEB.H264-Group" -> "My.Show.S01E01"
        "Movie.Name.2023.2160p.UHD.BluRay.x265" -> "Movie.Name.2023"
    '''
    patterns_to_remove = [
        r'\.?\d{3,4}p\b.*',
        r'\.?\bWEB\b.*',
        r'\.?\bBluRay\b.*',
        r'\.?\bBDRip\b.*',
        r'\.?\bHDRip\b.*',
        r'\.?\bHDTV\b.*',
        r'\.?\bDVDRip\b.*',
        r'\.?\bUHD\b.*',
        r'\.?\bHEVC\b.*',
        r'\.?\bH\.?26[456]\b.*',
        r'\.?\bx26[456]\b.*',
        r'\.?\bAAC\b.*',
        r'\.?\bAC3\b.*',
        r'\.?\bDTS\b.*',
        r'\.?\bFLAC\b.*',
        r'\.?\bDDP\b.*',
        r'\.?\bDD\b.*',
        r'\.?\b10bit\b.*',
        r'\.?\b8bit\b.*',
        r'\.?\bHi10p\b.*',
        r'\.?\bHi444p\b.*',
        r'\s*\(.*?\)\s*$',
    ]
    
    result = name
    for pattern in patterns_to_remove:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)

    result = re.sub(r'[\.\-_ ]+$', '', result)
    
    return result if result else name


def process_path(
    path: Path,
    dry_run: bool = True,
    show_progress: bool = True,
    output_dir: Optional[Path] = None,
    remove_original: bool = False
) -> List[ExtractResult]:
    '''
    Process MKV file or directory containing MKV files.

    Args:
        path: MKV file or directory to process
        dry_run: If True, don't actually extract
        show_progress: If True, show progress bar
        output_dir: Output directory for extracted subtitles
        remove_original: If True, remove subtitles from original file after extraction

    Returns:
        List of ExtractResult for each file
    '''
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    mkv_files = find_mkv_files(path)

    results = []
    iterator = tqdm(mkv_files, desc="Processing", unit="file") if show_progress else mkv_files
    for mkv_file in iterator:
        results.append(extract_subtitles(mkv_file, output_dir, dry_run=dry_run, remove_original=remove_original))

    return results
