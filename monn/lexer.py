"""Lexer: converts each non-empty source line into a command token."""
import re

from .commands import COMMANDS
from .errors import MonnSyntaxError


class Token:
    def __init__(self, op, params, line_no, raw):
        self.op = op
        self.params = params
        self.line_no = line_no
        self.raw = raw

    def __repr__(self):
        return f"<{self.op} {self.params}>"


def _compile_pattern(pattern):
    """Escape literal syntax while translating {field} placeholders."""
    pieces = []
    cursor = 0
    for match in re.finditer(r"\{(\w+)\}", pattern):
        pieces.append(re.escape(pattern[cursor:match.start()]))
        pieces.append(f"(?P<{match.group(1)}>.+?)")
        cursor = match.end()
    pieces.append(re.escape(pattern[cursor:]))
    return re.compile("^" + "".join(pieces) + "$")


class Lexer:
    def __init__(self):
        self.patterns = [
            (_compile_pattern(pattern), op, types, pattern)
            for pattern, (op, types) in COMMANDS.items()
        ]
        # More specific commands must be checked before their shorter prefixes.
        self.patterns.sort(key=lambda item: len(item[3]), reverse=True)

    def tokenize(self, code):
        tokens = []
        for line_no, raw_line in enumerate(code.splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("# "):
                continue
            token = self._match_line(line, line_no)
            if token is None:
                raise MonnSyntaxError(line_no, raw_line)
            tokens.append(token)
        return tokens

    def _match_line(self, line, line_no):
        for regex, op, param_types, _ in self.patterns:
            match = regex.fullmatch(line)
            if not match:
                continue
            params = {}
            try:
                for name, value_type in param_types.items():
                    raw_value = match.group(name) if name in match.groupdict() else None
                    if value_type is str:
                        params[name] = raw_value
                    else:
                        params[name] = value_type(raw_value)
            except (TypeError, ValueError) as exc:
                raise MonnSyntaxError(line_no, line, f"پارامتر نامعتبر: {exc}") from exc
            return Token(op, params, line_no, line)
        return None
