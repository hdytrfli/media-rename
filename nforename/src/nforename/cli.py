'''
Command-line interface for nforename.
'''

import argparse
from pathlib import Path

from tabulate import tabulate

from nforename.folder_processor import process_path
from nforename.models import Status


def print_table(results) -> None:
    '''Print results in tabular format.'''
    if not results:
        print("No folders found")
        return

    table_data = []
    for r in sorted(results, key=lambda x: x.old_path.name):
        old = r.old_path.name
        new = r.new_path.name if r.new_path else "-"
        mtype = r.media_type.value if r.media_type else "-"
        table_data.append([old, new, mtype, r.status.value])

    print()
    print(tabulate(table_data, headers=["OLD NAME", "NEW NAME", "TYPE", "STATUS"], tablefmt="simple_grid"))
    print()
    print_statistics(results)


def print_statistics(results) -> None:
    '''Print summary statistics.'''
    stats = {
        "renamed": sum(1 for r in results if r.status == Status.RENAMED),
        "dry_run": sum(1 for r in results if r.status == Status.DRY_RUN),
        "skipped": sum(
            1
            for r in results
            if r.status in (Status.SKIPPED_NO_NFO, Status.SKIPPED_HAS_YEAR, Status.SKIPPED_WRONG_TYPE, Status.SKIPPED_NO_YEAR)
        ),
        "errors": sum(1 for r in results if r.status in (Status.ERROR_CONFLICT, Status.ERROR_RENAME)),
    }

    print("Statistics:")
    print(f"  Renamed:  {stats['renamed']}")
    print(f"  Dry-run:  {stats['dry_run']}")
    print(f"  Skipped:  {stats['skipped']}")
    print(f"  Errors:   {stats['errors']}")
    print(f"  Total:    {len(results)}")


def main():
    '''
    Main entry point.
    '''
    parser = argparse.ArgumentParser(
        description="Rename movie/show folders by adding year from .nfo files"
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("."),
        help="Folder or directory to process (default: current directory)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually rename folders (default: dry-run)"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar"
    )
    args = parser.parse_args()

    try:
        results = process_path(args.path, dry_run=not args.execute, show_progress=not args.no_progress)
        print_table(results)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
