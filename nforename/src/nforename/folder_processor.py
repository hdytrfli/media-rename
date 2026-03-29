'''
Folder processing utilities.
'''

import re
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm

from nforename.models import MediaType, RenameResult, Status
from nforename.nfo_parser import detect_media_type, extract_year, find_nfo_file


def has_year_in_name(folder_name: str) -> bool:
    '''Check if folder name ends with (YYYY).'''
    return bool(re.search(r"\(\d{4}\)\s*$", folder_name.strip()))


def format_name_with_year(name: str, year: str) -> str:
    '''Format folder name with year.'''
    return f"{name} ({year})"


def process_folder(folder: Path, dry_run: bool = True) -> RenameResult:
    '''Process a single folder and return result.'''
    nfo_path = find_nfo_file(folder)
    if not nfo_path:
        return RenameResult(folder, None, None, None, Status.SKIPPED_NO_NFO)

    if has_year_in_name(folder.name):
        return RenameResult(folder, None, None, None, Status.SKIPPED_HAS_YEAR)

    media_type = detect_media_type(nfo_path)
    if not media_type:
        return RenameResult(folder, None, None, None, Status.SKIPPED_WRONG_TYPE)

    year = extract_year(nfo_path)
    if not year:
        return RenameResult(folder, None, None, media_type, Status.SKIPPED_NO_YEAR)

    new_name = format_name_with_year(folder.name, year)
    new_path = folder.parent / new_name

    if new_path.exists():
        return RenameResult(folder, new_path, year, media_type, Status.ERROR_CONFLICT)

    if dry_run:
        return RenameResult(folder, new_path, year, media_type, Status.DRY_RUN)

    try:
        folder.rename(new_path)
        return RenameResult(folder, new_path, year, media_type, Status.RENAMED)
    except OSError:
        return RenameResult(folder, new_path, year, media_type, Status.ERROR_RENAME)


def process_path(target: Path, dry_run: bool = True, show_progress: bool = True) -> List[RenameResult]:
    '''Process a single folder or all folders in target directory.

    If target is a folder with no subdirectories, treat it as a single folder to process.
    Otherwise, treat it as a directory and process all subfolders.
    '''
    if not target.exists():
        raise FileNotFoundError(f"Path not found: {target}")

    if target.is_file():
        return []

    has_subdirs = any(item.is_dir() for item in target.iterdir())

    if has_subdirs:
        folders = [item for item in target.iterdir() if item.is_dir()]
    else:
        folders = [target]

    results = []
    iterator = tqdm(folders, desc="Processing", unit="folder") if show_progress else folders
    for item in iterator:
        results.append(process_folder(item, dry_run))

    return results
