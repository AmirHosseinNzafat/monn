"""MonnLang: Persian-friendly language for desktop and web applications."""
from pathlib import Path
from .errors import MonnError, MonnRuntimeError, MonnSyntaxError
from .interpreter import MonnInterpreter
from .game import GameEngine, GameProject, GameError, GameStateError, GameValidationError, load_project
from .web_game import compile_game_to_html
موتور_بازی = GameEngine
پروژه_بازی = GameProject
بارگذاری_بازی = load_project
ساخت_بازی_وب = compile_game_to_html
__version__ = "1.2.0"
__all__ = ["MonnInterpreter", "MonnError", "MonnRuntimeError", "MonnSyntaxError", "GameEngine", "GameProject", "GameError", "GameStateError", "GameValidationError", "load_project", "run_code", "run_file", "compile_web", "compile_game_to_html", "موتور_بازی", "پروژه_بازی", "بارگذاری_بازی", "ساخت_بازی_وب"]
def run_code(code: str):
    """Parse and execute Monn source code."""
    return MonnInterpreter().run(code)
def run_file(path):
    """Execute a UTF-8 .monn file."""
    file_path=Path(path)
    if file_path.suffix.lower() != ".monn":
        raise MonnError("فایل باید پسوند .monn داشته باشد")
    try: source=file_path.read_text(encoding="utf-8")
    except OSError as exc: raise MonnError(f"خواندن فایل ناموفق بود: {exc}") from exc
    return run_code(source)
def compile_web(code: str, title="Monn Web App"):
    """Compile a portable Monn program into a standalone HTML document."""
    from .web import compile_to_html
    return compile_to_html(code,title)
