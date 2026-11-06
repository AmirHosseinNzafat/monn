"""Monn interpreter backed by Tkinter."""
import tkinter as tk
from tkinter import messagebox
import time

from .errors import MonnRuntimeError
from .lexer import Lexer
from .parser import Parser
from .widgets import Calculator, FloatingWindow
from .style import StyleManager
from .features import FeatureManager


class MonnInterpreter:
    def __init__(self):
        self.root = None
        self.vars = {}
        self.widgets = []
        self._owns_root = True
        self.style = StyleManager(self)
        self.features = FeatureManager(self)

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
            self.root.geometry("640x480")

    def _exec_children(self, node):
        for child in node.children:
            self._exec_node(child)

    def _exec_node(self, node):
        op, params = node.op, node.params
        if op == "LOOP_COUNT":
            for _ in range(max(0, min(params["n"], 10000))):
                self._exec_children(node)
        elif op == "LOOP_START":
            self._exec_children(node)
        elif op == "IF_START":
            self._exec_children(node)
        elif op in ("ELSE", "BLOCK_END", "IF_END"):
            return
        elif op == "CREATE_WINDOW":
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
        elif op == "CREATE_RADIO":
            self._ensure_root()
            self.features.add_radio()
        elif op == "CREATE_SLIDER":
            self._ensure_root()
            self.features.add_slider()
        elif op == "CREATE_PROGRESS":
            self._ensure_root()
            self.features.add_progress()
        elif op in ("CREATE_FRAME", "CREATE_CANVAS"):
            self._ensure_root()
            widget = tk.Frame(self.root, bd=1, relief="groove") if op == "CREATE_FRAME" else tk.Canvas(self.root, height=120)
            widget.pack(fill="both", expand=True, padx=5, pady=5)
            self.widgets.append(widget)
        elif op in ("CREATE_MENU", "ADD_MENU"):
            self._ensure_root()
            self.features.add_menu()
        elif op in ("CREATE_COMBOBOX",):
            self._ensure_root()
            self.features.add_combobox()
        elif op == "CREATE_LISTBOX":
            self._ensure_root()
            self.features.add_listbox()
        elif op == "CREATE_TABS":
            self._ensure_root()
            self.features.add_tabs()
        elif op == "CREATE_CHAT":
            self._ensure_root()
            self.features.add_chat()
        elif op == "GENERATE_IMAGE":
            self._ensure_root()
            self.features.generate_image(params["prompt"])
        elif op == "OPEN_IMAGE":
            self._ensure_root()
            self.features.open_image(params.get("path"))
        elif op == "OPEN_3D":
            self._ensure_root()
            self.features.open_3d(params.get("path"))
        elif op == "CREATE_3D":
            self._ensure_root()
            self.features.create_3d_model(params["shape"])
        elif op == "ASK_TEXT":
            self._ensure_root()
            self.vars["input"] = self.features.ask_text(params["prompt"])
        elif op == "SET_SIZE":
            self._ensure_root()
            self.root.geometry(f"{params['w']}x{params['h']}")
        elif op == "SET_TITLE":
            self._ensure_root()
            self.root.title(params["t"])
        elif op == "SET_BG":
            self._ensure_root()
            self.style.set_background(params["c"])
        elif op == "SET_FG":
            self._ensure_root()
            self.style.set_foreground(params["c"])
        elif op == "SET_FONT":
            self._ensure_root()
            self.style.set_font(params["s"])
        elif op == "CHOOSE_COLOR":
            self._ensure_root()
            self.style.choose_color()
        elif op == "SET_PADDING":
            self._ensure_root()
            self.style.set_padding(params["n"])
        elif op == "SET_RELIEF":
            self._ensure_root()
            self.style.set_relief(params["r"])
        elif op == "SET_CURSOR":
            self._ensure_root()
            self.style.set_cursor(params["c"])
        elif op == "SET_ALPHA":
            self._ensure_root()
            self.style.set_alpha(params["a"])
        elif op == "SET_RESIZABLE":
            self._ensure_root()
            self.style.set_resizable(params["v"] == "1")
        elif op == "THEME_DARK":
            self._ensure_root()
            self.style.apply_theme("dark")
        elif op == "THEME_LIGHT":
            self._ensure_root()
            self.style.apply_theme("light")
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
            self.root.after(max(0, min(params["s"], 30)) * 1000, lambda: None)
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
