'''
Subtitle filename naming utilities for Emby/Jellyfin compatibility.
'''

from typing import List, Optional

from extractsub.models import SubtitleTrack


def get_lang_code(lang: str, title: str) -> str:
    '''
    Get language code with variant differentiation.

    Args:
        lang: Language code from mkvmerge
        title: Track title/name

    Returns:
        Differentiated language code (e.g., cht, chs, lav, pob)
    '''
    if not lang or lang == "und":
        return ""

    lang_lower = lang.lower()
    title_lower = title.lower() if title else ""

    if lang_lower == "chi" or lang_lower == "zho":
        if "traditional" in title_lower:
            return "cht"
        if "simplified" in title_lower:
            return "chs"
        return "chi"

    if lang_lower == "spa":
        if "latin" in title_lower or "latinoamérica" in title_lower:
            return "lav"
        return "spa"

    if lang_lower == "por":
        if "brazil" in title_lower or "brasil" in title_lower:
            return "pob"
        return "por"

    return lang_lower


def get_subtitle_tags(track: SubtitleTrack) -> List[str]:
    '''
    Extract subtitle tags from track metadata.

    Args:
        track: SubtitleTrack object

    Returns:
        List of tags (forced, sdh, dub)
    '''
    tags = []
    title_lower = (track.title or "").lower()

    if track.is_forced or "forced" in title_lower:
        tags.append("forced")
    if "sdh" in title_lower or "hearing impaired" in title_lower:
        tags.append("sdh")
    elif "dub" in title_lower:
        tags.append("dub")

    return tags


def build_subtitle_filename(
    video_name: str,
    lang: str,
    tags: List[str],
    track_index: int,
    total_non_tagged: int,
    ext: str
) -> str:
    '''
    Build subtitle filename following Emby/Jellyfin convention.

    Format: {video_name}.{lang}.{tags}.{index}.{ext}

    Args:
        video_name: Sanitized video filename without extension
        lang: Language code
        tags: List of tags (forced, sdh, default, dub)
        track_index: Index of this track among non-tagged tracks
        total_non_tagged: Total number of non-tagged tracks for this language
        ext: File extension (.srt, .ass, etc.)

    Returns:
        Complete subtitle filename
    '''
    lang_part = f".{lang}" if lang else ""
    tags_part = f".{'.'.join(tags)}" if tags else ""

    if tags:
        track_part = ""
    else:
        track_part = f".{track_index}" if total_non_tagged > 1 else ""

    return f"{video_name}{lang_part}{tags_part}{track_part}{ext}"
