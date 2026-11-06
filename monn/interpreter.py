"""Monn interpreter backed by Tkinter."""
import tkinter as tk
from tkinter import messagebox
import time

from .errors import MonnRuntimeError
from .lexer import Lexer
from .parser import Parser
from .widgets import Calculator, FloatingWindow


class MonnInterpreter:
    def __init__(self):
        self.root = None
        self.vars = {}
        self.widgets = []
        self._owns_root = True

    def run(self, code):
        try:
            tree = Parser(Lexer().tokenize(code)).parse()
            self._exec_children(tree)
            if self.root is not None:
                self.root.mainloop()
            return self.vars
        except MonnRuntimeError:
            raise
        except Exception as exc:
            raise MonnRuntimeError(str(exc)) from exc

    def _ensure_root(self):
        if self.root is None:
            self.root = tk.Tk()
            self.root.title("Monn Window")
            self.root.geometry("400x300")

    def _exec_children(self, node):
        for child in node.children:
            self._exec_node(child)

    def _exec_node(self, node):
        op, params = node.op, node.params
        if op == "LOOP_COUNT":
            for _ in range(max(0, min(params["n"], 10000))):
                self._exec_children(node)
        elif op == "LOOP_START":
            # Safe initial behavior: a loop block executes once.
            self._exec_children(node)
        elif op == "IF_START":
            # Conditional evaluation is not defined in the supplied syntax yet.
            self._exec_children(node)
        elif op in ("ELSE", "BLOCK_END", "IF_END"):
            return
        elif op == "CREATE_WINDOW":
            if self.root is None:
                self._ensure_root()
        elif op == "FLOATING_CENTERED":
            self._ensure_root()
            FloatingWindow(self.root, params["n"])
        elif op in ("CREATE_BUTTON", "CREATE_LABEL"):
            self._ensure_root()
            text = params.get("t", params.get("text", ""))
            widget_cls = tk.Button if op == "CREATE_BUTTON" else tk.Label
            widget = widget_cls(self.root, text=text)
            widget.pack(padx=5, pady=4)
            self.widgets.append(widget)
        elif op == "CREATE_ENTRY":
            self._ensure_root()
            widget = tk.Entry(self.root)
            widget.pack(padx=5, pady=4)
            self.widgets.append(widget)
        elif op == "CREATE_TEXTBOX":
            self._ensure_root()
            widget = tk.Text(self.root, height=5, width=35)
            widget.pack(padx=5, pady=4)
            self.widgets.append(widget)
        elif op == "CREATE_CHECKBOX":
            self._ensure_root()
            widget = tk.Checkbutton(self.root, text="گزینه")
            widget.pack(padx=5, pady=4)
            self.widgets.append(widget)
        elif op == "SET_SIZE":
            self._ensure_root()
            self.root.geometry(f"{params['w']}x{params['h']}")
        elif op == "SET_TITLE":
            self._ensure_root()
            self.root.title(params["t"])
        elif op == "SET_BG":
            self._ensure_root()
            self.root.configure(bg=params["c"])
        elif op == "SET_FG":
            self._ensure_root()
            for widget in self.widgets:
                try:
                    widget.configure(fg=params["c"])
                except tk.TclError:
                    pass
        elif op == "SET_FONT":
            self._ensure_root()
            for widget in self.widgets:
                try:
                    widget.configure(font=("Arial", params["s"]))
                except tk.TclError:
                    pass
        elif op == "CREATE_CALCULATOR":
            self._ensure_root()
            Calculator(self.root)
        elif op == "SET_VAR":
            self.vars[params["name"]] = params["val"]
        elif op == "PRINT":
            print(self.vars)
        elif op in ("WINDOW_MINIMIZE", "WINDOW_HIDE"):
            if self.root:
                self.root.iconify()
        elif op in ("WINDOW_MAXIMIZE", "WINDOW_SHOW"):
            self._ensure_root()
            self.root.deiconify()
            try:
                self.root.state("zoomed")
            except tk.TclError:
                pass
        elif op in ("WINDOW_CLOSE", "QUIT"):
            if self.root:
                self.root.destroy()
                self.root = None
        elif op == "WINDOW_TOPMOST":
            self._ensure_root()
            self.root.attributes("-topmost", True)
        elif op == "SLEEP":
            time.sleep(max(0, min(params["s"], 30)))
        elif op == "SHOW_MESSAGE":
            self._ensure_root()
            messagebox.showinfo("Monn", "پیام Monn")
        elif op == "CLEAR_ALL":
            for widget in self.widgets:
                try:
                    widget.destroy()
                except tk.TclError:
                    pass
            self.widgets.clear()
        else:
            print(f"[Monn] دستور {op} هنوز پیاده‌سازی نشده (خط {node.line_no})")
