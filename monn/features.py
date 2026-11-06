"""Ten user-interface and application features for Monn."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from .ai import AIClient
from .media import save_generated_image, show_image, show_3d_model, choose_file


class FeatureManager:
    def __init__(self, interpreter):
        self.app = interpreter
        self.ai = AIClient()

    def _add(self, widget):
        widget.pack(padx=6, pady=5, fill="x")
        self.app.widgets.append(widget)
        return widget

    def add_tabs(self):
        book = ttk.Notebook(self.app.root)
        book.pack(fill="both", expand=True, padx=6, pady=6)
        for title in ("صفحه اول", "صفحه دوم"):
            frame = ttk.Frame(book)
            book.add(frame, text=title)
            ttk.Label(frame, text=title).pack(padx=20, pady=20)
        self.app.widgets.append(book)

    def add_listbox(self):
        box = tk.Listbox(self.app.root, height=5)
        for item in ("گزینه اول", "گزینه دوم", "گزینه سوم"):
            box.insert("end", item)
        self._add(box)

    def add_combobox(self):
        combo = ttk.Combobox(self.app.root, values=("گزینه اول", "گزینه دوم", "گزینه سوم"), state="readonly")
        combo.current(0)
        self._add(combo)

    def add_radio(self):
        value = tk.StringVar(value="گزینه اول")
        frame = ttk.Frame(self.app.root)
        for item in ("گزینه اول", "گزینه دوم", "گزینه سوم"):
            ttk.Radiobutton(frame, text=item, value=item, variable=value).pack(anchor="w")
        self._add(frame)

    def add_slider(self):
        scale = tk.Scale(self.app.root, from_=0, to=100, orient="horizontal", label="مقدار")
        self._add(scale)

    def add_progress(self):
        bar = ttk.Progressbar(self.app.root, maximum=100, value=65)
        self._add(bar)

    def add_menu(self):
        menu = tk.Menu(self.app.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="انتخاب فایل", command=lambda: choose_file(self.app.root))
        file_menu.add_command(label="خروج", command=self.app.root.destroy)
        menu.add_cascade(label="فایل", menu=file_menu)
        self.app.root.configure(menu=menu)

    def ask_text(self, prompt="متن را وارد کنید"):
        return simpledialog.askstring("Monn", prompt, parent=self.app.root)

    def add_chat(self):
        win = tk.Toplevel(self.app.root)
        win.title("Monn AI Chat")
        win.geometry("650x520")
        transcript = tk.Text(win, wrap="word", state="disabled")
        transcript.pack(fill="both", expand=True, padx=8, pady=8)
        row = ttk.Frame(win)
        row.pack(fill="x", padx=8, pady=8)
        entry = ttk.Entry(row)
        entry.pack(side="left", fill="x", expand=True)

        def append(role, text):
            transcript.configure(state="normal")
            transcript.insert("end", role + ": " + text + "\n\n")
            transcript.see("end")
            transcript.configure(state="disabled")

        history = [{"role": "system", "content": "You are a helpful assistant."}]

        def send():
            prompt = entry.get().strip()
            if not prompt:
                return
            entry.delete(0, "end")
            append("شما", prompt)
            history.append({"role": "user", "content": prompt})
            send_button.configure(state="disabled")

            def worker():
                try:
                    answer = self.ai.chat(history)
                    history.append({"role": "assistant", "content": answer})
                    win.after(0, lambda: append("هوش مصنوعی", answer))
                except Exception as exc:
                    win.after(0, lambda: append("خطا", str(exc)))
                finally:
                    win.after(0, lambda: send_button.configure(state="normal"))

            threading.Thread(target=worker, daemon=True).start()

        send_button = ttk.Button(row, text="ارسال", command=send)
        send_button.pack(side="right", padx=5)
        entry.bind("<Return>", lambda _event: send())
        self.app.widgets.append(win)

    def generate_image(self, prompt):
        def worker():
            try:
                result = self.ai.generate_image(prompt)
                path = save_generated_image(result)
                self.app.root.after(0, lambda: show_image(self.app.root, path))
            except Exception as exc:
                self.app.root.after(0, lambda: messagebox.showerror("Monn AI", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def open_image(self, path=None):
        path = path or choose_file(self.app.root, [("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")])
        if path:
            show_image(self.app.root, path)

    def open_3d(self, path=None):
        path = path or choose_file(self.app.root, [("3D models", "*.obj *.stl *.ply *.glb *.gltf"), ("All files", "*.*")])
        if path:
            show_3d_model(self.app.root, path)
