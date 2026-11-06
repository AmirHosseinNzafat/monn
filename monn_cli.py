#!/usr/bin/env python3
"""Monn command-line runner and HTML exporter."""
import argparse
import sys
from pathlib import Path
from monn import MonnError, run_file

def main():
    parser = argparse.ArgumentParser(description="MonnLang: run .monn or export it to HTML")
    parser.add_argument("file", help="مسیر فایل .monn")
    parser.add_argument("--web", action="store_true", help="خروجی مستقل HTML بساز")
    parser.add_argument("-o", "--output", help="مسیر خروجی؛ پیش‌فرض کنار فایل ورودی")
    args = parser.parse_args()
    try:
        if args.web:
            from monn.web import compile_to_html
            source = Path(args.file).read_text(encoding="utf-8")
            target = Path(args.output) if args.output else Path(args.file).with_suffix(".html")
            target.write_text(compile_to_html(source, title=Path(args.file).stem), encoding="utf-8")
            print(f"خروجی وب ساخته شد: {target}")
        else:
            run_file(args.file)
    except (MonnError, OSError, ValueError) as exc:
        print(f"Monn: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
