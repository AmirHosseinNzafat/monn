"""Ten practical styling helpers for Monn Tkinter applications."""
from tkinter import colorchooser, ttk
import tkinter as tk


class StyleManager:
    def __init__(self, interpreter):
        self.app = interpreter

    def _widgets(self):
        return [w for w in self.app.widgets if w.winfo_exists()]

    def set_background(self, color):
        self.app._ensure_root()
        self.app.root.configure(bg=color)
        for widget in self._widgets():
            try:
                widget.configure(bg=color)
            except tk.TclError:
                pass

    def set_foreground(self, color):
        for widget in self._widgets():
            try:
                widget.configure(fg=color)
            except tk.TclError:
                pass

    def set_font(self, size, family="Arial"):
        size = max(6, min(int(size), 72))
        for widget in self._widgets():
            try:
                widget.configure(font=(family, size))
            except tk.TclError:
                pass

    def choose_color(self, target="background"):
        chosen = colorchooser.askcolor(parent=self.app.root, title="انتخاب رنگ")[1]
        if chosen:
            (self.set_foreground if target == "foreground" else self.set_background)(chosen)
        return chosen

    def set_padding(self, value):
        value = max(0, min(int(value), 100))
        for widget in self._widgets():
            try:
                widget.pack_configure(padx=value, pady=value)
            except tk.TclError:
                pass

    def set_relief(self, relief):
        allowed = {"flat", "raised", "sunken", "ridge", "groove", "solid"}
        relief = relief.lower()
        if relief not in allowed:
            raise ValueError("relief must be one of: " + ", ".join(sorted(allowed)))
        for widget in self._widgets():
            try:
                widget.configure(relief=relief)
            except tk.TclError:
                pass

    def set_cursor(self, cursor):
        allowed = {"arrow", "hand2", "cross", "watch", "xterm", " fleur", "plus"}
        cursor = cursor.strip()
        if cursor not in allowed:
            raise ValueError("Unsupported cursor")
        self.app.root.configure(cursor=cursor)
        for widget in self._widgets():
            try:
                widget.configure(cursor=cursor)
            except tk.TclError:
                pass

    def set_alpha(self, alpha):
        alpha = max(0.2, min(float(alpha), 1.0))
        self.app.root.attributes("-alpha", alpha)

    def set_resizable(self, enabled):
        self.app.root.resizable(bool(enabled), bool(enabled))

    def apply_theme(self, theme):
        dark = theme.lower() == "dark"
        bg, fg, field = ("#20242b", "#f3f4f6", "#303640") if dark else ("#f4f6f8", "#20242b", "#ffffff")
        self.set_background(bg)
        self.set_foreground(fg)
        for widget in self._widgets():
            try:
                widget.configure(insertbackground=fg)
                if isinstance(widget, (tk.Entry, tk.Text, tk.Listbox)):
                    widget.configure(bg=field, fg=fg)
            except tk.TclError:
                pass
        try:
            style = ttk.Style(self.app.root)
            style.theme_use("clam")
            style.configure(".", background=bg, foreground=fg)
        except tk.TclError:
            pass
