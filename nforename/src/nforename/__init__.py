'''
NfoRename - Rename movie/show folders by adding year from .nfo files.
'''

from nforename.models import MediaType, Status, RenameResult
from nforename.nfo_parser import find_nfo_file, detect_media_type, extract_year
from nforename.folder_processor import process_folder, process_path
from nforename.cli import main

__version__ = "1.0.0"
__all__ = [
    "MediaType",
    "Status",
    "RenameResult",
    "find_nfo_file",
    "detect_media_type",
    "extract_year",
    "process_folder",
    "process_path",
    "main",
]
