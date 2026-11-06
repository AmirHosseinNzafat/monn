"""Monn interpreter backed by Tkinter."""
import tkinter as tk
from tkinter import messagebox
from .errors import MonnRuntimeError
from .lexer import Lexer
from .parser import Parser
from .widgets import Calculator, FloatingWindow
from .style import StyleManager
from .features import FeatureManager

class MonnInterpreter:
    COMPARATORS = {
        "==": lambda a,b: a == b, "=": lambda a,b: a == b, "!=": lambda a,b: a != b,
        ">": lambda a,b: a > b, "<": lambda a,b: a < b, ">=": lambda a,b: a >= b,
        "<=": lambda a,b: a <= b, "برابر": lambda a,b: a == b,
        "بزرگتر": lambda a,b: a > b, "کوچکتر": lambda a,b: a < b,
    }
    def __init__(self):
        self.root, self.vars, self.widgets = None, {}, []
        self._owns_root, self.last_widget = True, None
        self.style, self.features = StyleManager(self), FeatureManager(self)
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
            self.root.title("Monn")
            self.root.geometry("720x520")
    def _value(self, raw):
        if raw is None: return None
        text = str(raw).strip()
        if text.startswith("$"): return self.vars.get(text[1:], "")
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
            return text[1:-1]
        lowered = text.lower()
        if lowered in ("درست", "true"): return True
        if lowered in ("نادرست", "false"): return False
        try: return float(text) if "." in text else int(text)
        except ValueError: return self.vars.get(text, text)
    def _condition(self, params):
        if not params: return True
        left, right, op = self._value(params.get("left")), self._value(params.get("right")), params.get("op")
        if op not in self.COMPARATORS:
            raise MonnRuntimeError(f"عملگر شرط ناشناخته: {op}")
        try: return self.COMPARATORS[op](left, right)
        except TypeError: return self.COMPARATORS[op](str(left), str(right))
    def _run_action(self, action):
        """Run a small safe set of built-in button actions."""
        if not action:
            return
        kind, separator, value = action.partition(":")
        kind, value = kind.strip(), value.strip()
        if kind in ("پیام", "message"):
            messagebox.showinfo("Monn", value)
        elif kind in ("تنظیم", "set") and "=" in value:
            name, raw = value.split("=", 1)
            self.vars[name.strip()] = self._value(raw.strip())
        elif kind in ("افزایش", "increase", "کاهش", "decrease") and "=" in value:
            name, raw = value.split("=", 1)
            delta = float(raw.strip())
            current = float(self.vars.get(name.strip(), 0))
            self.vars[name.strip()] = current + delta if kind in ("افزایش", "increase") else current - delta
        elif kind in ("خروج", "quit"):
            if self.root:
                self.root.destroy()
                self.root = None
        else:
            messagebox.showinfo("Monn", f"کنش ناشناخته: {action}")

    def _exec_children(self, node):
        for child in node.children: self._exec_node(child)
    def _exec_node(self, node):
        op, p = node.op, node.params
        if op == "LOOP_COUNT":
            count = max(0, min(int(p["n"]), 10000))
            for index in range(count):
                self.vars["شماره_تکرار"] = index + 1
                self.vars["loop_index"] = index
                self._exec_children(node)
        elif op == "LOOP_START":
            # An unbounded loop is intentionally not implicit; legacy block runs once.
            self._exec_children(node)
        elif op == "IF_START":
            self._exec_children(node) if self._condition(p) else self._exec_nodes(node.alternate)
        elif op in ("ELSE", "BLOCK_END", "IF_END"): return
        elif op == "SET_VAR":
            self.vars[p["name"]] = self._value(p["val"])
        elif op == "PRINT":
            print(self.vars)
        elif op in ("PACK_LEFT","PACK_RIGHT","PACK_TOP","PACK_BOTTOM","PLACE_CENTER"):
            if self.last_widget is None: raise MonnRuntimeError("ابتدا یک ابزار بساز، سپس چیدمان را تعیین کن")
            self.last_widget.pack_forget()
            if op == "PLACE_CENTER": self.last_widget.place(relx=0.5, rely=0.5, anchor="center")
            else:
                side = {"PACK_LEFT":"left","PACK_RIGHT":"right","PACK_TOP":"top","PACK_BOTTOM":"bottom"}[op]
                self.last_widget.pack(side=side, padx=6, pady=5)
        elif op == "CREATE_WINDOW": self._ensure_root()
        elif op == "FLOATING_CENTERED":
            self._ensure_root(); self.last_widget = FloatingWindow(self.root, p["n"])
        elif op in ("CREATE_BUTTON", "CREATE_LABEL"):
            self._ensure_root()
            text = p.get("t", p.get("text", ""))
            cls = tk.Button if op == "CREATE_BUTTON" else tk.Label
            widget = (tk.Button(self.root, text=text, command=lambda a=p.get("action", ""): self._run_action(a)) if op == "CREATE_BUTTON" else tk.Label(self.root, text=text)); widget.pack(padx=5, pady=4); self.widgets.append(widget); self.last_widget = widget
        elif op == "CREATE_ENTRY":
            self._ensure_root(); widget=tk.Entry(self.root); widget.pack(padx=5,pady=4); self.widgets.append(widget); self.last_widget=widget
        elif op == "CREATE_TEXTBOX":
            self._ensure_root(); widget=tk.Text(self.root,height=5,width=35); widget.pack(padx=5,pady=4); self.widgets.append(widget); self.last_widget=widget
        elif op == "CREATE_CHECKBOX":
            self._ensure_root(); widget=tk.Checkbutton(self.root,text="گزینه"); widget.pack(padx=5,pady=4); self.widgets.append(widget); self.last_widget=widget
        elif op == "CREATE_RADIO":
            self._ensure_root(); self.features.add_radio()
        elif op == "CREATE_SLIDER":
            self._ensure_root(); self.features.add_slider()
        elif op == "CREATE_PROGRESS":
            self._ensure_root(); self.features.add_progress()
        elif op in ("CREATE_FRAME","CREATE_CANVAS"):
            self._ensure_root(); widget=tk.Frame(self.root,bd=1,relief="groove") if op=="CREATE_FRAME" else tk.Canvas(self.root,height=120)
            widget.pack(fill="both",expand=True,padx=5,pady=5); self.widgets.append(widget); self.last_widget=widget
        elif op in ("CREATE_MENU","ADD_MENU"): self._ensure_root(); self.features.add_menu()
        elif op == "CREATE_COMBOBOX": self._ensure_root(); self.features.add_combobox()
        elif op == "CREATE_LISTBOX": self._ensure_root(); self.features.add_listbox()
        elif op == "CREATE_TABS": self._ensure_root(); self.features.add_tabs()
        elif op == "CREATE_CHAT": self._ensure_root(); self.features.add_chat()
        elif op == "GENERATE_IMAGE": self._ensure_root(); self.features.generate_image(p["prompt"])
        elif op == "OPEN_IMAGE": self._ensure_root(); self.features.open_image(p.get("path"))
        elif op == "OPEN_3D": self._ensure_root(); self.features.open_3d(p.get("path"))
        elif op == "CREATE_3D": self._ensure_root(); self.features.create_3d_model(p["shape"])
        elif op == "ASK_TEXT": self._ensure_root(); self.vars["input"] = self.features.ask_text(p["prompt"])
        elif op == "SET_SIZE": self._ensure_root(); self.root.geometry(f"{p['w']}x{p['h']}")
        elif op == "SET_TITLE": self._ensure_root(); self.root.title(p["t"])
        elif op == "SET_BG": self._ensure_root(); self.style.set_background(p["c"])
        elif op == "SET_FG": self._ensure_root(); self.style.set_foreground(p["c"])
        elif op == "SET_FONT": self._ensure_root(); self.style.set_font(p["s"])
        elif op == "CHOOSE_COLOR": self._ensure_root(); self.style.choose_color()
        elif op == "SET_PADDING": self._ensure_root(); self.style.set_padding(p["n"])
        elif op == "SET_RELIEF": self._ensure_root(); self.style.set_relief(p["r"])
        elif op == "SET_CURSOR": self._ensure_root(); self.style.set_cursor(p["c"])
        elif op == "SET_ALPHA": self._ensure_root(); self.style.set_alpha(p["a"])
        elif op == "SET_RESIZABLE": self._ensure_root(); self.style.set_resizable(p["v"] == "1")
        elif op == "THEME_DARK": self._ensure_root(); self.style.apply_theme("dark")
        elif op == "THEME_LIGHT": self._ensure_root(); self.style.apply_theme("light")
        elif op == "CREATE_CALCULATOR": self._ensure_root(); Calculator(self.root)
        elif op in ("WINDOW_MINIMIZE","WINDOW_HIDE"):
            if self.root: self.root.iconify()
        elif op in ("WINDOW_MAXIMIZE","WINDOW_SHOW"):
            self._ensure_root(); self.root.deiconify()
            try: self.root.state("zoomed")
            except tk.TclError: pass
        elif op in ("WINDOW_CLOSE","QUIT"):
            if self.root: self.root.destroy(); self.root=None
        elif op == "WINDOW_TOPMOST": self._ensure_root(); self.root.attributes("-topmost",True)
        elif op == "SLEEP":
            if self.root: self.root.after(max(0,min(p["s"],30))*1000,lambda:None)
        elif op == "SHOW_MESSAGE": self._ensure_root(); messagebox.showinfo("Monn", p.get("text", "پیام Monn"))
        elif op == "CLEAR_ALL":
            for widget in self.widgets:
                try: widget.destroy()
                except tk.TclError: pass
            self.widgets.clear(); self.last_widget=None
        else: raise MonnRuntimeError(f"دستور {op} پیاده‌سازی نشده (خط {node.line_no})")
    def _exec_nodes(self, nodes):
        for child in nodes: self._exec_node(child)
