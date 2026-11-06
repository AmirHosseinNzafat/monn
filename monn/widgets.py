"""Reusable Tkinter widgets used by the Monn interpreter."""
import ast
import operator
import tkinter as tk


class FloatingWindow:
    def __init__(self, master, text, width=300, height=200):
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry(f"{width}x{height}")
        self.win.configure(bg="#111111")
        self.label = tk.Label(
            self.win, text=text, font=("Arial", 24),
            fg="#00ff66", bg="#111111"
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")
        self.win.bind("<Button-1>", lambda _event: self.win.destroy())


class Calculator(tk.Toplevel):
    """A small calculator without Python eval()."""
    OPS = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg, ast.UAdd: operator.pos,
    }

    def __init__(self, master):
        super().__init__(master)
        self.title("Monn Calculator")
        self.geometry("300x390")
        self.expr = tk.StringVar()
        tk.Entry(self, textvariable=self.expr, font=("Arial", 22),
                 justify="right").pack(fill="x", padx=6, pady=6)
        frame = tk.Frame(self)
        frame.pack(expand=True, fill="both")
        for row in [["7", "8", "9", "/"], ["4", "5", "6", "*"],
                    ["1", "2", "3", "-"], ["C", "0", "=", "+"]]:
            line = tk.Frame(frame)
            line.pack(expand=True, fill="both")
            for char in row:
                tk.Button(line, text=char, font=("Arial", 18),
                          command=lambda c=char: self._press(c)
                          ).pack(side="left", expand=True, fill="both")

    @classmethod
    def _calculate(cls, expression):
        def visit(node):
            if isinstance(node, ast.Expression):
                return visit(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in cls.OPS:
                return cls.OPS[type(node.op)](visit(node.left), visit(node.right))
            if isinstance(node, ast.UnaryOp) and type(node.op) in cls.OPS:
                return cls.OPS[type(node.op)](visit(node.operand))
            raise ValueError("عبارت مجاز نیست")
        return visit(ast.parse(expression, mode="eval"))

    def _press(self, char):
        if char == "C":
            self.expr.set("")
        elif char == "=":
            try:
                self.expr.set(str(self._calculate(self.expr.get())))
            except Exception:
                self.expr.set("ERR")
        else:
            self.expr.set(self.expr.get() + char)
