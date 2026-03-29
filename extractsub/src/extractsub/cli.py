'''
Command-line interface for extractsub.
'''

import argparse
from pathlib import Path

from tabulate import tabulate

from extractsub.mkv_processor import check_mkvtoolnix_installed, process_path
from extractsub.models import Status


def print_table(results) -> None:
    '''Print results in tabular format.'''
    if not results:
        print("No MKV files found")
        return

    table_data = []
    for r in sorted(results, key=lambda x: x.file_path.name):
        filename = r.file_path.name
        output = r.output_path.name if r.output_path else "-"
        tracks = len(r.subtitle_tracks)
        status = r.status.value
        table_data.append([filename, output, tracks, status])

    print()
    print(tabulate(table_data, headers=["FILE NAME", "OUTPUT", "TRACKS", "STATUS"], tablefmt="simple_grid"))
    print()
    print_statistics(results)


def print_statistics(results) -> None:
    '''Print summary statistics.'''
    stats = {
        "extracted": sum(1 for r in results if r.status == Status.EXTRACTED),
        "dry_run": sum(1 for r in results if r.status == Status.DRY_RUN),
        "skipped": sum(
            1
            for r in results
            if r.status in (Status.SKIPPED_NO_SUBS,)
        ),
        "errors": sum(
            1
            for r in results
            if r.status in (Status.ERROR_NO_MKV, Status.ERROR_NO_SUBS, Status.ERROR_PROBE, Status.ERROR_EXTRACT)
        ),
    }

    print("Statistics:")
    print(f"  Extracted:  {stats['extracted']}")
    print(f"  Dry-run:    {stats['dry_run']}")
    print(f"  Skipped:    {stats['skipped']}")
    print(f"  Errors:     {stats['errors']}")
    print(f"  Total:      {len(results)}")


def main():
    '''
    Main entry point.
    '''
    parser = argparse.ArgumentParser(
        description="Extract embedded subtitles from MKV files"
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("."),
        help="MKV file or directory to process (default: current directory)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually extract subtitles (default: dry-run)"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output directory for extracted subtitles (default: current directory)"
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove subtitles from original file after extraction"
    )

    args = parser.parse_args()

    if not check_mkvtoolnix_installed():
        print("Error: MKVToolNix (mkvmerge/mkvextract) not found.")
        print("Please install from: https://mkvtoolnix.download/")
        return 1

    output_dir = args.output if args.output else Path(".")

    try:
        results = process_path(args.path, dry_run=not args.execute, show_progress=not args.no_progress, output_dir=output_dir, remove_original=args.remove)
        print_table(results)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
