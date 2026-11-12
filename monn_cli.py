#!/usr/bin/env python3
"""Monn command-line runner, game player and HTML exporters."""
import argparse
import sys
from pathlib import Path

from monn import MonnError, run_file
from monn.game import GameEngine, load_project, GameError


def play_game(engine, save_path=None, load_path=None):
    if load_path:
        if save_path is None:
            save_path = load_path
        engine.load(load_path)
        print("ذخیره بازی بارگذاری شد.")
    print("\n=== {} ===".format(engine.project.title))
    while True:
        scene = engine.scene
        state = engine.snapshot()
        print("\n--- {} ---\n{}".format(scene["title"], scene["text"]))
        print("جان: {}/{} | ویژگی‌ها: {}".format(
            state["health"], state["max_health"], state["stats"]))
        if state["inventory"]:
            print("کوله‌پشتی: {}".format(state["inventory"]))
        if state["ended"]:
            print("\nپایان بازی.")
            break
        choices = engine.available_choices()
        if not choices:
            print("\nدر این مسیر انتخاب دیگری وجود ندارد.")
            break
        for index, choice in enumerate(choices, 1):
            print("{}. {}".format(index, choice["text"]))
        print("فرمان‌ها: شماره انتخاب | ذ: ذخیره | ب: بارگذاری | خ: خروج")
        answer = input("> ").strip()
        if answer in ("خ", "خروج", "q", "quit"):
            break
        if answer in ("ذ", "ذخیره", "s", "save"):
            if not save_path:
                save_path = "monn-save.json"
            engine.save(save_path)
            print("ذخیره شد: {}".format(save_path))
            continue
        if answer in ("ب", "بارگذاری", "l", "load"):
            path = save_path or "monn-save.json"
            engine.load(path)
            print("بارگذاری شد.")
            continue
        try:
            number = int(answer)
            if number < 1 or number > len(choices):
                raise ValueError
            engine.choose(choices[number - 1]["_index"])
        except ValueError:
            print("شماره انتخاب معتبر نیست.")
        except GameError as exc:
            print("خطای بازی: {}".format(exc))


def main():
    parser = argparse.ArgumentParser(
        description="MonnLang: اجرای برنامه، بازی داستانی یا خروجی وب"
    )
    parser.add_argument("file", help="مسیر فایل .monn یا پروژه JSON بازی")
    parser.add_argument("--web", action="store_true", help="ساخت خروجی مستقل HTML")
    parser.add_argument("--game", action="store_true", help="اجرای فایل پروژه بازی JSON")
    parser.add_argument("-o", "--output", help="مسیر فایل خروجی")
    parser.add_argument("--save", dest="save_path", help="مسیر فایل ذخیره بازی")
    parser.add_argument("--load", dest="load_path", help="بارگذاری فایل ذخیره بازی")
    args = parser.parse_args()
    try:
        if args.game:
            project = load_project(args.file)
            if args.web:
                if args.save_path or args.load_path:
                    parser.error("--save و --load با --web قابل استفاده نیستند")
                from monn.web_game import compile_game_to_html
                target = Path(args.output) if args.output else Path(args.file).with_suffix(".html")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(compile_game_to_html(project), encoding="utf-8")
                print("بازی HTML ساخته شد: {}".format(target))
            else:
                play_game(GameEngine(project), args.save_path, args.load_path)
        elif args.web:
            from monn.web import compile_to_html
            source = Path(args.file).read_text(encoding="utf-8")
            target = Path(args.output) if args.output else Path(args.file).with_suffix(".html")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(compile_to_html(source, title=Path(args.file).stem), encoding="utf-8")
            print("خروجی وب ساخته شد: {}".format(target))
        else:
            if args.save_path or args.load_path:
                parser.error("--save و --load فقط همراه --game قابل استفاده‌اند")
            run_file(args.file)
    except (MonnError, GameError, OSError, ValueError) as exc:
        print("Monn: {}".format(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nخروج از برنامه.")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
