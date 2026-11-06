"""Command patterns for the Monn dot-command language.

This table includes implemented commands and a few reserved experimental
operations. The interpreter reports a warning for reserved operations.
"""
COMMANDS = {
    # Window operations
    "...": ("CREATE_WINDOW", {}),
    "... | /// {n} .>>...": ("FLOATING_CENTERED", {"n": str}),
    "... <<<": ("WINDOW_MINIMIZE", {}),
    "... >>>": ("WINDOW_MAXIMIZE", {}),
    "... xxx": ("WINDOW_CLOSE", {}),
    "... ???": ("WINDOW_HIDE", {}),
    "... !!!": ("WINDOW_SHOW", {}),
    "... @top": ("WINDOW_TOPMOST", {}),
    # Widgets
    "....": ("CREATE_BUTTON", {"text": str}),
    ".... '{t}'": ("CREATE_BUTTON", {"t": str}),
    ".....": ("CREATE_LABEL", {"text": str}),
    "..... '{t}'": ("CREATE_LABEL", {"t": str}),
    "......": ("CREATE_ENTRY", {}),
    ".......": ("CREATE_TEXTBOX", {}),
    "........": ("CREATE_CHECKBOX", {}),
    # Layout / blocks
    "......[": ("LOOP_START", {}),
    "......]": ("BLOCK_END", {}),
    "......[{n}": ("LOOP_COUNT", {"n": int}),
    "????": ("IF_START", {}),
    "?!?!": ("ELSE", {}),
    "?????": ("IF_END", {}),
    # Variables / output
    "$$ {name} = {val}": ("SET_VAR", {"name": str, "val": str}),
    "$$print": ("PRINT", {}),
    # Calculator
    "..calc": ("CREATE_CALCULATOR", {}),
    # Appearance
    "##bg:{c}": ("SET_BG", {"c": str}),
    "##fg:{c}": ("SET_FG", {"c": str}),
    "##font:{s}": ("SET_FONT", {"s": int}),
    "##size:{w}x{h}": ("SET_SIZE", {"w": int, "h": int}),
    "##title:{t}": ("SET_TITLE", {"t": str}),
    # Reserved / experimental operations retained from the supplied design
    "...clear": ("CLEAR_ALL", {}),
    "...quit": ("QUIT", {}),
    "...wait": ("WAIT", {}),
    "...sleep:{s}": ("SLEEP", {"s": int}),
    "...beep": ("BEEP", {}),
    "...bell": ("BELL", {}),
    "...rand": ("RANDOM", {}),
    "...time": ("TIME", {}),
    "...date": ("DATE", {}),
    "...theme:dark": ("THEME_DARK", {}),
    "...theme:light": ("THEME_LIGHT", {}),
    "@click": ("ON_CLICK", {}),
    "@key": ("ON_KEY", {}),
    "@hover": ("ON_HOVER", {}),
    "@load": ("ON_LOAD", {}),
    ">>file": ("OPEN_FILE", {}),
    "<<file": ("SAVE_FILE", {}),
    ">>msg": ("SHOW_MESSAGE", {}),
    ">>input": ("ASK_INPUT", {}),
}


def get_command_patterns():
    return list(COMMANDS)
