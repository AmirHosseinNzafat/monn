"""Small block parser for counted and single-pass loop blocks."""
from .errors import MonnSyntaxError


class Node:
    def __init__(self, op, params, line_no):
        self.op = op
        self.params = params
        self.line_no = line_no
        self.children = []

    def __repr__(self):
        return f"Node({self.op!r}, {self.params!r}, children={self.children!r})"


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
                stack[-1].children.append(node)
                stack.append(node)
            elif token.op in ("BLOCK_END", "IF_END"):
                if len(stack) == 1:
                    raise MonnSyntaxError(token.line_no, token.raw, "پایان بلوک بدون شروع بلوک")
                stack.pop()
            elif token.op == "ELSE":
                # ELSE is retained as a node for future conditional support.
                stack[-1].children.append(Node(token.op, token.params, token.line_no))
            else:
                stack[-1].children.append(Node(token.op, token.params, token.line_no))
        if len(stack) != 1:
            opener = stack[-1]
            raise MonnSyntaxError(opener.line_no, opener.op, "بلوک بسته نشده است")
        return root
