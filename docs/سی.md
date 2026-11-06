```markdown
# MonnLang 1.1 Comprehensive Guide

This document is the language command reference. In this version, Monn has two execution paths:
1. **Desktop**: Direct execution with the Python interpreter and Tkinter interface
2. **Web**: Compilation of the portable portion of the program into a standalone HTML file

## 1. File Structure and Writing Rules
- Each command is written on a separate line.
- The file is saved with UTF-8 encoding and the `.monn` extension.
- Empty lines are allowed.
- A line starting with `# ` is a comment.
- Leading and trailing whitespace on a line is ignored.
- Persian text, numbers, and common symbols are allowed in values.
- Variable names should preferably contain no spaces; use underscores for multi-part names.

## 2. Installation and Running the Program

### Windows
```powershell
git clone https://github.com/AmirHosseinNzafat/monn.git
cd monn
py -m pip install -e ".[all]"
monn examples/hello.monn
```

### Linux / macOS
```bash
git clone https://github.com/AmirHosseinNzafat/monn.git
cd monn
python3 -m pip install -e ".[all]"
monn examples/hello.monn
```

Basic installation without media libraries:
```bash
python -m pip install -e .
```

## 3. Window and Appearance

| Persian Command | Symbolic Command | Description |
|---|---|---|
| `پنجره` | `...` | Create the main window |
| `عنوان متن` | `##title:text` | Window title |
| `اندازه 800 در 600` | `##size:800x600` | Width and height |
| `پس‌زمینه #101827` | `##bg:#101827` | Background color |
| `رنگ متن #ffffff` | `##fg:#ffffff` | Base text color |
| `فونت 14` | `##font:14` | Font size |
| `فاصله 8` | `##padding:8` | Widget spacing |
| `انتخاب رنگ` | `##color` | Open the color picker |
| `شفافیت 0.9` | `##alpha:0.9` | Window opacity |
| `##relief:groove` | same | Frame style |
| `##cursor:hand2` | same | Mouse cursor shape |
| `##resizable:1` | same | Enable resizing |
| `تم تاریک` | `...theme:dark` | Dark theme |
| `تم روشن` | `...theme:light` | Light theme |

## 4. User Interface Widgets

| Persian Command | Symbolic Equivalent | Purpose |
|---|---|---|
| `دکمه شروع` | `.... 'شروع'` | Button |
| `متن سلام` | `..... 'سلام'` | Label |
| `ورودی` | `......` | Single-line input |
| `کادرمتن` | `.......` | Multi-line text |
| `چک‌باکس` | `........` | Checkbox option |
| `گزینه‌ها` | `.........` | Radio option group |
| `نوارلغزنده` | `..........` | Numeric selection |
| `پیشرفت` | `...........` | Progress bar |
| `قاب` | `............` | Grouping frame |
| `بوم` | `.............` | Canvas surface |
| `فهرست` | `................` | Selection list |
| `کشویی` | `...............` | Dropdown list |
| `زبانه‌ها` | `.................` | Tabs |
| `گفتگو` | `..................` | AI chat interface |
| `ماشین حساب` | `..calc` | Desktop calculator |

## 5. Variables and Values

```text
متغیر نام = امیر
متغیر امتیاز = 120
متغیر فعال = درست
چاپ
```

To use a variable in a condition, write its name with a dollar sign: `$امتیاز`.
Numeric values are converted to numbers. True/false values are written as `درست` and `نادرست`. To print the state of variables, use `چاپ` or `$$print`.

## 6. Conditions

```text
اگر $امتیاز >= 100
متن عالی بود!
وگرنه
متن هنوز جا برای پیشرفت هست.
پایان
```

Operators:
- `==` or `=`: equal
- `!=`: not equal
- `>`: greater than
- `<`: less than
- `>=`: greater than or equal
- `<=`: less than or equal

Symbolic equivalent:
```text
???? 10 > 5
..... 'شرط درست است'
?!?! 
..... 'شرط نادرست است'
?????
```
The old short form `????` without a parameter is always considered true for compatibility; for an actual condition, use the form with an operator.

## 7. Loops

A counted loop is executed with "تکرار عدد" (repeat number). An open loop starts with "شروع حلقه" (start loop) or `......[` and must execute "توقف حلقه" (stop loop) via a condition:

```text
متغیر شمارنده = 0
شروع حلقه
متن دور تازه
اگر $شماره_تکرار >= 3
توقف حلقه
پایان
پایان حلقه
```

```text
تکرار 3
متن این خط سه بار اجرا می‌شود
پایان حلقه
```

Symbolic form: `......[3`, body, then `......]`.
Inside the loop, the variable `$شماره_تکرار` starts from 1 up to the repeat count, and `$loop_index` starts from zero.
To prevent the program from locking up, the cap for each loop is 10,000 iterations. An open loop must be stopped with "توقف حلقه" inside a condition; if it reaches the cap, you get a runtime error.

## 8. Button Actions and Narrative Games

General form:
```text
دکمه عنوان دکمه => نوع‌کنش:مقدار
```

Built-in actions:
| Action | Example | Result |
|---|---|---|
| پیام (message) | `پیام:کلید را پیدا کردی` | Show a message |
| تنظیم (set) | `تنظیم:مرحله=2` | Change a variable's value |
| افزایش (increase) | `افزایش:سکه=5` | Increase a value |
| کاهش (decrease) | `کاهش:جان=1` | Decrease a value |
| خروج (exit) | `خروج` | Close the program |

Example:
```text
پنجره
##title:ماجرای جنگل
متغیر جان = 3
متغیر سکه = 0
متن شب شده و دو مسیر پیش روی توست.
دکمه رفتن به غار => کاهش:جان=1
دکمه برداشتن سکه => افزایش:سکه=1
دکمه خواندن یادداشت => پیام:روی کاغذ نوشته شده: به صدای آب اعتماد کن.
```

These capabilities provide an initial core for narrative and choice-driven games. Persistent game saving, an advanced scene system, dynamic music, animation, physics, user accounts, and multiplayer are still supplementary modules.

## 9. Widget Layout
After creating a widget, write the layout command so it applies to the most recently created widget:
- `..<` or `چیدمان چپ` (left layout)
- `..>` or `چیدمان راست` (right layout)
- `..^` or `چیدمان بالا` (top layout)
- `..v` or `چیدمان پایین` (bottom layout)
- `..=` or `وسط‌چین` (center alignment)

## 10. Image and 3D
Installation:
```powershell
py -m pip install Pillow trimesh matplotlib
```
Commands:
- `تصویر توضیح تصویر` or `..image:prompt`: request image generation from a compatible API
- `بازکردن تصویر` or `..openimage`: select a local image
- `نمایش سه‌بعدی` or `..model3d`: select a 3D model
- `ساخت سه‌بعدی cube` or `..create3d:cube`: generate a basic OBJ model
- Built-in generated shapes: `cube`, `pyramid`, `diamond`

Image generation requires an API with a compatible `/images/generations` endpoint. Displaying complex models depends on installing dependencies and file compatibility.

## 11. AI Chat Connection
PowerShell:
```powershell
$env:MONN_API_KEY="private key"
$env:MONN_API_BASE="https://openrouter.ai/api/v1"
$env:MONN_MODEL="openrouter/free"
monn examples/ai_chat.monn
```
Configurable variables:
- `MONN_API_KEY`: private key
- `MONN_API_BASE`: API base URL
- `MONN_MODEL`: model identifier
- `MONN_IMAGE_API_BASE`: image API URL
- `MONN_IMAGE_MODEL`: image model identifier

Do not place the key inside the program file or a public repository. Chat and image generation are two separate capabilities, and a provider may support only one of them.

## 12. Web Output
```powershell
monn examples/story_game.monn --web
monn examples/story_game.monn --web --output site/index.html
```
The HTML file can be opened directly in a browser. For public publishing, static hosting can be used. Web output supports public UI widgets, conditions, counted loops, basic appearance, and simple actions. Some desktop features, API chat, and 3D display do not yet have full equivalents in this web compiler.

## 13. Debugging and Testing
```powershell
py -m compileall monn monn_cli.py
py -m unittest discover -s tests -v
```
- Unknown line: check the command spelling and spacing.
- Unclosed block: place "پایان" (end) for every condition and "پایان حلقه" (end loop) for every loop.
- API failure: check the key, model, base URL, and provider limits.
- Missing media widget: install the relevant optional dependency.

## 14. Technical Scope of Version 1.1
Monn is a project under development, not a complete game engine or a replacement for all web languages. The desktop interpreter is based on Tkinter, and the web compiler converts an independent subset of the language into HTML/JavaScript. For a complete narrative game engine, scene system, save system, audio, assets, and visual design tools, modular additions should be made in future versions.
```
