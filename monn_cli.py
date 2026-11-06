#!/usr/bin/env python3
"""Command-line runner for .monn files."""
import argparse
import sys

from monn import MonnError, run_file


def main():
    parser = argparse.ArgumentParser(description="Run a MonnLang .monn file")
    parser.add_argument("file", help="Path to a .monn source file")
    args = parser.parse_args()
    try:
        run_file(args.file)
    except MonnError as exc:
        print(f"Monn error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
