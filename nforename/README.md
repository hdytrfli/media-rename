# NfoRename

Automatically rename movie and TV show folders by adding the year from `.nfo` files.

## Installation

### Install from GitHub

```bash
pip install git+https://github.com/hdytrfli/media-utilty.git#subdirectory=nforename
```

### Install from Local Clone

```bash
git clone https://github.com/hdytrfli/media-utilty.git
cd media-utilty/nforename
pip install -e .
```

## Features

- **Auto-detects media type** - Works with both movies (`movie.nfo` or any `.nfo`) and shows (`tvshow.nfo`)
- **Safe dry-run mode** - Preview changes before applying them
- **Smart skipping** - Ignores folders that already have a year in the name
- **Clean tabular output** - Easy to read results with statistics

## Requirements

- Python 3.10+
- tabulate (installed automatically)

## Usage

```bash
# Dry-run (default) - shows what would be renamed
nforename ./movies

# Process a single folder
nforename "Movie Folder"

# Actually rename folders
nforename ./movies --execute

# Run on current directory
nforename

# Disable progress bar
nforename ./movies --no-progress
```

## Examples

**Before:**

```
movies/
├── 12 Angry Men/
│   └── movie.nfo
├── The Matrix/
│   └── movie.nfo
└── Already Named (1999)/
    └── movie.nfo
```

**Run:**

```bash
nforename ./movies --execute
```

**After:**

```
movies/
├── 12 Angry Men (1957)/
│   └── movie.nfo
├── The Matrix (1999)/
│   └── movie.nfo
└── Already Named (1999)/
    └── movie.nfo
```

## Sample Output

```
┌──────────────────────────────┬─────────────────────────────────────┬────────┬───────────────────┐
│ OLD NAME                     │ NEW NAME                            │ TYPE   │ STATUS            │
├──────────────────────────────┼─────────────────────────────────────┼────────┼───────────────────┤
│ 12 Angry Men                 │ 12 Angry Men (1957)                 │ movie  │ Dry run           │
├──────────────────────────────┼─────────────────────────────────────┼────────┼───────────────────┤
│ The Matrix                   │ The Matrix (1999)                   │ movie  │ Dry run           │
├──────────────────────────────┼─────────────────────────────────────┼────────┼───────────────────┤
│ Already Named (1999)         │ -                                   │ -      │ Skipped: Has year │
└──────────────────────────────┴─────────────────────────────────────┴────────┴───────────────────┘

Statistics:
  Renamed:  0
  Dry-run:  2
  Skipped:  1
  Errors:   0
  Total:    3
```

## How It Works

1. Scans the target path (single folder or directory) for folders
2. Looks for `.nfo` files in each folder:
   - First checks for `movie.nfo` or `tvshow.nfo`
   - Falls back to any `.nfo` file
3. Reads the `<year>` tag from the `.nfo` file
4. Auto-detects media type from the XML root element (`<movie>` or `<tvshow>`)
5. Adds the year to the folder name in format: `Folder Name (YYYY)`
6. Skips folders that already have a year in the name

## Supported .nfo Formats

### Movies

```xml
<?xml version="1.0" encoding="utf-8"?>
<movie>
  <title>Movie Title</title>
  <year>2023</year>
</movie>
```

### TV Shows

```xml
<?xml version="1.0" encoding="utf-8"?>
<tvshow>
  <title>Show Title</title>
  <year>2023</year>
</tvshow>
```

## License

MIT License
