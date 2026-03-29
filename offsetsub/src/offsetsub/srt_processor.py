'''
SRT subtitle offset utilities.
'''

import re
from pathlib import Path
from typing import List, Optional, Tuple

from tqdm import tqdm

from offsetsub.models import OffsetResult, Status


def find_srt_files(path: Path) -> List[Path]:
    '''Find all SRT files in directory (non-recursive) or return single file.'''
    if path.is_file():
        if path.suffix.lower() == '.srt':
            return [path]
        return []
    if path.is_dir():
        return sorted(path.glob('*.srt'))
    return []


def parse_timestamp(timestamp: str) -> int:
    '''
    Parse SRT timestamp to milliseconds.
    
    Format: HH:MM:SS,mmm
    '''
    timestamp = timestamp.strip()
    match = re.match(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})', timestamp)
    if not match:
        raise ValueError(f"Invalid timestamp format: {timestamp}")
    
    hours, minutes, seconds, millis = map(int, match.groups())
    return (hours * 3600 + minutes * 60 + seconds) * 1000 + millis


def format_timestamp(ms: int) -> str:
    '''
    Format milliseconds to SRT timestamp.
    
    Format: HH:MM:SS,mmm
    '''
    if ms < 0:
        ms = 0
    
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    millis = ms % 1000
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def offset_timestamp(timestamp: str, offset_ms: int) -> str:
    '''Apply offset to a single timestamp.'''
    ms = parse_timestamp(timestamp)
    ms += offset_ms
    return format_timestamp(ms)


def offset_srt_content(content: str, offset_ms: int) -> Tuple[str, int]:
    '''
    Apply offset to SRT content.

    Returns:
        Tuple of (modified content, number of cues modified)
    '''
    cues_modified = 0
    lines = content.splitlines(keepends=True)
    result_lines = []

    timestamp_pattern = re.compile(
        r'^(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})'
    )

    for line in lines:
        match = timestamp_pattern.match(line.strip())
        if match:
            start_ts, end_ts = match.groups()
            new_start = offset_timestamp(start_ts, offset_ms)
            new_end = offset_timestamp(end_ts, offset_ms)

            line_stripped = line.rstrip('\r\n')
            line_match = timestamp_pattern.match(line_stripped)
            if line_match:
                line_ending = line[len(line_stripped):]
                prefix = line[:line.index(line_match.group(0))]
                suffix = line_stripped[line.index(line_match.group(0)) + len(line_match.group(0)):]
                line = f"{prefix}{new_start} --> {new_end}{suffix}{line_ending}"

            cues_modified += 1

        result_lines.append(line)
    
    return ''.join(result_lines), cues_modified


def process_srt_file(
    srt_path: Path,
    offset_ms: int,
    dry_run: bool = True,
    output_dir: Optional[Path] = None
) -> OffsetResult:
    '''
    Apply offset to a single SRT file.

    Args:
        srt_path: Path to SRT file
        offset_ms: Offset in milliseconds (positive or negative)
        dry_run: If True, don't actually write changes
        output_dir: Output directory (default: same as input)

    Returns:
        OffsetResult with status and information
    '''
    srt_path = srt_path.resolve()
    output_dir = output_dir or srt_path.parent

    if not srt_path.exists():
        return OffsetResult(srt_path, output_dir, offset_ms, 0, Status.ERROR_FILE)

    content = None
    for encoding in ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']:
        try:
            content = srt_path.read_text(encoding=encoding)
            break
        except (IOError, UnicodeDecodeError):
            continue

    if content is None:
        return OffsetResult(srt_path, output_dir, offset_ms, 0, Status.ERROR_FILE)
    
    try:
        new_content, cues_modified = offset_srt_content(content, offset_ms)
    except ValueError:
        return OffsetResult(srt_path, output_dir, offset_ms, 0, Status.ERROR_FILE)
    
    if dry_run:
        return OffsetResult(srt_path, output_dir, offset_ms, cues_modified, Status.DRY_RUN)
    
    try:
        output_path = output_dir / srt_path.name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(new_content, encoding='utf-8')
        return OffsetResult(srt_path, output_path, offset_ms, cues_modified, Status.OFFSET)
    except IOError:
        return OffsetResult(srt_path, output_dir, offset_ms, cues_modified, Status.ERROR_WRITE)


def process_path(
    path: Path,
    offset_ms: int,
    dry_run: bool = True,
    show_progress: bool = True,
    output_dir: Optional[Path] = None
) -> List[OffsetResult]:
    '''
    Process SRT files in path (file or directory).
    
    Args:
        path: File or directory to process
        offset_ms: Offset in milliseconds
        dry_run: If True, don't actually write changes
        show_progress: If True, show progress bar
        output_dir: Output directory
        
    Returns:
        List of OffsetResult for each file
    '''
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    
    srt_files = find_srt_files(path)
    
    if not srt_files:
        return []
    
    results = []
    iterator = tqdm(srt_files, desc="Processing", unit="file") if show_progress else srt_files
    for srt_file in iterator:
        results.append(process_srt_file(srt_file, offset_ms, dry_run=dry_run, output_dir=output_dir))
    
    return results
