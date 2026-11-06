"""Block parser for loops and if/else statements."""
from .errors import MonnSyntaxError

class Node:
    def __init__(self, op, params, line_no):
        self.op, self.params, self.line_no = op, params, line_no
        self.children, self.alternate = [], []
        self.in_else = False
    def add(self, node):
        (self.alternate if self.in_else else self.children).append(node)
    def __repr__(self):
        return f"Node({self.op!r}, {self.params!r}, children={self.children!r}, alternate={self.alternate!r})"

class Parser:
    OPENERS = {"LOOP_START", "LOOP_COUNT", "IF_START"}
    def __init__(self, tokens):
        self.tokens = tokens
    def parse(self):
        root = Node("PROGRAM", {}, 0)
        stack = [root]
        for token in self.tokens:
            if token.op in self.OPENERS:
                node = Node(token.op, token.params, token.line_no)
                stack[-1].add(node)
                stack.append(node)
            elif token.op == "ELSE":
                if len(stack) == 1 or stack[-1].op != "IF_START":
                    raise MonnSyntaxError(token.line_no, token.raw, "وگرنه فقط داخل شرط مجاز است")
                if stack[-1].in_else:
                    raise MonnSyntaxError(token.line_no, token.raw, "هر شرط فقط یک وگرنه دارد")
                stack[-1].in_else = True
            elif token.op in ("BLOCK_END", "IF_END"):
                if len(stack) == 1:
                    raise MonnSyntaxError(token.line_no, token.raw, "پایان بلوک بدون شروع بلوک")
                expected = "IF_START" if token.op == "IF_END" else None
                if expected and stack[-1].op != expected:
                    raise MonnSyntaxError(token.line_no, token.raw, "پایان شرط با پایان حلقه اشتباه شده است")
                if token.op == "BLOCK_END" and stack[-1].op == "IF_START":
                    raise MonnSyntaxError(token.line_no, token.raw, "برای شرط از ????? یا پایان استفاده کن")
                stack.pop()
            else:
                if token.op == "BREAK_LOOP" and not any(n.op in ("LOOP_START", "LOOP_COUNT") for n in stack):
                    raise MonnSyntaxError(token.line_no, token.raw, "توقف حلقه فقط داخل حلقه مجاز است")
                stack[-1].add(Node(token.op, token.params, token.line_no))
        if len(stack) != 1:
            opener = stack[-1]
            raise MonnSyntaxError(opener.line_no, opener.op, "بلوک بسته نشده است")
        return root
