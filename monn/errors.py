"""Exception types raised by MonnLang."""


class MonnError(Exception):
    """Base exception for Monn."""


class MonnSyntaxError(MonnError):
    """A source line does not match a known command."""
    def __init__(self, line_no, line, message="دستور Monn ناشناخته"):
        super().__init__(f"خط {line_no}: {message}\n  → {line}")
        self.line_no = line_no
        self.line = line


class MonnRuntimeError(MonnError):
    """An error occurred while executing a Monn instruction."""
