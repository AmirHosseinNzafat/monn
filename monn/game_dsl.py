"""Readable .monn game-project source format."""
import json
import re
from pathlib import Path

from .game import GameProject, GameValidationError


def dumps_monn(project):
    """Serialize a game project into the native, editable MONN source format."""
    game = project if isinstance(project, GameProject) else GameProject(project)
    payload = json.dumps(game.data, ensure_ascii=False, indent=2)
    return '# Monn Game Source · نسخه ۱\nبازی "{}"\nپروژه = """\n{}\n"""\n'.format(
        game.title.replace('"', '\\"'), payload
    )


def loads_monn(source):
    """Parse a .monn game source file produced by Monn Studio."""
    if not isinstance(source, str):
        raise GameValidationError("محتوای MONN باید متن باشد")
    match = re.search(r'^پروژه\s*=\s*"""\s*\n(.*?)\n"""\s*$', source, re.M | re.S)
    if not match:
        raise GameValidationError("ساختار فایل MONN بازی معتبر نیست؛ از Monn Studio خروجی بگیر")
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise GameValidationError("ساختار داده‌های پروژه MONN خراب است: {}".format(exc)) from exc
    return GameProject(data)


def load_monn(path):
    return loads_monn(Path(path).read_text(encoding="utf-8"))
