"""Optional image and 3D model viewers."""
from pathlib import Path
import base64
import tkinter as tk
from tkinter import filedialog, messagebox


def save_generated_image(image_data, directory="generated"):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if image_data.get("b64_json"):
        raw = base64.b64decode(image_data["b64_json"])
        path = directory / "monn-image.png"
        path.write_bytes(raw)
        return path
    if image_data.get("url"):
        raise RuntimeError("این API فقط URL تصویر داده؛ برای دانلود، کتابخانه requests را نصب کنید یا خروجی را دستی ذخیره کنید.")
    raise RuntimeError("خروجی تصویر فاقد b64_json یا url است.")


def show_image(master, path):
    try:
        from PIL import Image, ImageTk
    except ImportError as exc:
        raise RuntimeError("برای نمایش تصویر، Pillow را نصب کنید: pip install Pillow") from exc
    win = tk.Toplevel(master)
    win.title("Monn Image Viewer")
    image = Image.open(path)
    image.thumbnail((1000, 800))
    photo = ImageTk.PhotoImage(image)
    label = tk.Label(win, image=photo)
    label.image = photo
    label.pack(fill="both", expand=True)
    return win


def show_3d_model(master, path):
    try:
        import trimesh
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    except ImportError as exc:
        raise RuntimeError("برای مدل سه‌بعدی نصب کنید: pip install trimesh matplotlib") from exc
    model = trimesh.load(str(path), force="mesh")
    if model.is_empty:
        raise RuntimeError("فایل مدل سه‌بعدی خالی یا نامعتبر است.")
    figure = plt.figure(figsize=(7, 5))
    axis = figure.add_subplot(111, projection="3d")
    vertices = model.vertices
    faces = model.faces
    axis.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2],
                      triangles=faces, linewidth=0.15, alpha=0.9)
    axis.set_title(Path(path).name)
    win = tk.Toplevel(master)
    win.title("Monn 3D Viewer")
    canvas = FigureCanvasTkAgg(figure, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    return win


def choose_file(master, filetypes=None):
    return filedialog.askopenfilename(parent=master, filetypes=filetypes or [("All files", "*.*")])
