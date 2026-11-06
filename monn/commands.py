"""Command patterns for the Monn dot-command language.

Implemented operations work in the interpreter; the rest are retained as
reserved syntax from the original language specification and emit warnings.
"""
COMMANDS = {
    # Windows
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
    ".........": ("CREATE_RADIO", {}),
    "..........": ("CREATE_SLIDER", {}),
    "...........": ("CREATE_PROGRESS", {}),
    "............": ("CREATE_FRAME", {}),
    ".............": ("CREATE_CANVAS", {}),
    "..............": ("CREATE_MENU", {}),
    "...............": ("CREATE_COMBOBOX", {}),
    "................": ("CREATE_LISTBOX", {}),
    # Layout
    "..<": ("PACK_LEFT", {}),
    "..>": ("PACK_RIGHT", {}),
    "..^": ("PACK_TOP", {}),
    "..v": ("PACK_BOTTOM", {}),
    "..=": ("PLACE_CENTER", {}),
    # Loops and conditions
    "......[": ("LOOP_START", {}),
    "......]": ("BLOCK_END", {}),
    "......[{n}": ("LOOP_COUNT", {"n": int}),
    "????": ("IF_START", {}),
    "?!?!": ("ELSE", {}),
    "?????": ("IF_END", {}),
    # Variables and arithmetic (arithmetic operators are reserved)
    "$$ {name} = {val}": ("SET_VAR", {"name": str, "val": str}),
    "$$+": ("ADD", {}),
    "$$-": ("SUB", {}),
    "$$*": ("MUL", {}),
    "$$/": ("DIV", {}),
    "$$=": ("EQ", {}),
    "$$print": ("PRINT", {}),
    "$$eval": ("EVAL", {}),
    # Calculator
    "..calc": ("CREATE_CALCULATOR", {}),
    "..calc+": ("CALC_ADD", {}),
    "..calc-": ("CALC_SUB", {}),
    "..calc*": ("CALC_MUL", {}),
    "..calc/": ("CALC_DIV", {}),
    "..calc=": ("CALC_RESULT", {}),
    "..calcC": ("CALC_CLEAR", {}),
    # Appearance
    "##bg:{c}": ("SET_BG", {"c": str}),
    "##fg:{c}": ("SET_FG", {"c": str}),
    "##font:{s}": ("SET_FONT", {"s": int}),
    "##size:{w}x{h}": ("SET_SIZE", {"w": int, "h": int}),
    "##title:{t}": ("SET_TITLE", {"t": str}),
    # Events
    "@click": ("ON_CLICK", {}),
    "@key": ("ON_KEY", {}),
    "@hover": ("ON_HOVER", {}),
    "@load": ("ON_LOAD", {}),
    # Input / output
    ">>file": ("OPEN_FILE", {}),
    "<<file": ("SAVE_FILE", {}),
    ">>msg": ("SHOW_MESSAGE", {}),
    ">>input": ("ASK_INPUT", {}),
    # Miscellaneous
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
}


def get_command_patterns():
    """Return all registered source patterns."""
    return list(COMMANDS)
