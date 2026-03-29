# ExtractSub

Automatically extract embedded subtitles from MKV files and optionally remove them from the original file.

## Installation

### Install from GitHub

```bash
pip install git+https://github.com/hdytrfli/media-utilty.git#subdirectory=extractsub
```

### Install from Local Clone

```bash
git clone https://github.com/hdytrfli/media-utilty.git
cd media-utilty/extractsub
pip install -e .
```

## Features

- **Auto-detects subtitle tracks** - Finds all embedded subtitle streams in MKV files
- **Safe dry-run mode** - Preview what would be extracted before applying
- **Multiple codec support** - Works with SRT, ASS, PGS, VobSub, WebVTT, and more
- **Clean output** - Extracts to current directory by default
- **Automatic filename sanitization** - Removes quality tags for clean names
- **Optional removal** - Remove subtitles from original file after extraction

## Requirements

- Python 3.10+
- MKVToolNix (mkvmerge/mkvextract) - [Download here](https://mkvtoolnix.download/)
- tabulate (installed automatically)
- tqdm (installed automatically)

## Usage

```bash
# Dry-run (default) - shows what would be extracted
extractsub ./movies

# Process a single MKV file
extractsub movie.mkv

# Actually extract subtitles
extractsub ./movies --execute

# Extract and remove from original file
extractsub ./movies --execute --remove

# Specify output directory
extractsub ./movies --execute --output ./subtitles

# Run on current directory
extractsub

# Disable progress bar
extractsub ./movies --no-progress
```

## Examples

**Before:**

```
movies/
├── The Matrix (1999).mkv
│   └── (embedded subtitles: English, Spanish, French)
├── Inception (2010).mkv
│   └── (embedded subtitles: English)
└── No Subs (2020).mkv
    └── (no embedded subtitles)
```

**Run:**

```bash
extractsub ./movies --execute --remove
```

**After:**

```
movies/
├── The Matrix (1999).mkv  (subtitles removed if --remove used)
├── Inception (2010).mkv   (subtitles removed if --remove used)
├── No Subs (2020).mkv
└── extracted/
    ├── The Matrix (1999).eng.srt
    ├── The Matrix (1999).spa.srt
    ├── The Matrix (1999).fra.srt
    └── Inception (2010).eng.srt
```

## Sample Output

```
┌──────────────────────────────┬───────────┬──────────┬───────────┐
│ FILE NAME                    │ OUTPUT    │   TRACKS │ STATUS    │
├──────────────────────────────┼───────────┼──────────┼───────────┤
│ Inception (2010).mkv         │ extracted │        1 │ Extracted │
├──────────────────────────────┼───────────┼──────────┼───────────┤
│ No Subs (2020).mkv           │ -         │        0 │ Skipped   │
├──────────────────────────────┼───────────┼──────────┼───────────┤
│ The Matrix (1999).mkv        │ extracted │        3 │ Extracted │
└──────────────────────────────┴───────────┴──────────┴───────────┘

Statistics:
  Extracted:  2
  Dry-run:    0
  Skipped:    1
  Errors:     0
  Total:      3
```

## How It Works

1. Scans the target path (single MKV file or directory) for `.mkv` files
2. Uses `mkvmerge` to probe each file for subtitle tracks
3. Identifies all subtitle streams with their language, codec, and properties
4. Extracts subtitles using `mkvextract` to current directory (or specified output)
5. Optionally removes subtitles from original file with `--remove` flag

### Filename Format

Output files are named as: `{video_name}.{language}.{codec}.srt`

- Language is omitted if undefined (`und`)
- Quality tags (1080p, WEB, H264, etc.) are automatically removed from video names

Examples:
- `Movie.Name.2023.1080p.WEB.H264.mkv` → `Movie.Name.2023.en.srt`
- `Show.S01E01.2160p.UHD.BluRay.x265.mkv` → `Show.S01E01.srt` (no language)

## Supported Subtitle Codecs

| Codec | Extension | Description |
|-------|-----------|-------------|
| SubRip | `.srt` | Text-based subtitles |
| ASS/SSA | `.ass` | Advanced SubStation Alpha |
| PGS | `.sup` | Picture-based subtitles (Blu-ray) |
| VobSub | `.idx` | DVD subtitles |
| WebVTT | `.vtt` | Web Video Text Tracks |
| TTML | `.ttf` | Timed Text Markup Language |

## License

MIT License
