"""Deterministic, offline project builder for Monn Studio.

No model, network, API key, or external process is required.
"""
import base64
import copy
import re
import unicodedata


def _svg_data(title, sky, ground, accent, scene):
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
<defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="{sky}"/><stop offset="1" stop-color="#111827"/></linearGradient><linearGradient id="ground" x2="0" y2="1"><stop stop-color="{ground}"/><stop offset="1" stop-color="#080d16"/></linearGradient></defs>
<rect width="960" height="540" fill="url(#sky)"/><circle cx="760" cy="105" r="52" fill="{accent}" opacity=".75"/>
<path d="M0 350 Q180 240 360 350 T720 330 T960 350 V540 H0Z" fill="url(#ground)"/>
<path d="M0 425 Q230 350 470 420 T960 400 V540 H0Z" fill="{ground}" opacity=".8"/>
<g fill="{accent}" opacity=".8"><circle cx="110" cy="90" r="3"/><circle cx="205" cy="150" r="2"/><circle cx="420" cy="70" r="3"/><circle cx="600" cy="170" r="2"/></g>
<rect x="48" y="42" width="360" height="74" rx="16" fill="#07101dcc" stroke="{accent}" stroke-opacity=".7"/>
<text x="72" y="88" fill="#fff" font-size="30" font-family="sans-serif">{title}</text>
<text x="72" y="500" fill="#dce8f7" font-size="18" font-family="sans-serif">{scene}</text></svg>""".format(title=title, sky=sky, ground=ground, accent=accent, scene=scene)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _base(title, ident, scenes):
    return {
        "meta": {"id": ident, "title": title, "start_scene": scenes[0]["id"]},
        "ui": {"menu_enabled": True, "menu_title": title, "start_label": "شروع بازی",
               "settings_label": "تنظیمات", "show_health": True, "show_inventory": True,
               "show_quests": True, "elements": []},
        "player": {"health": 100, "max_health": 100, "stats": {"سکه": 0}, "inventory": []},
        "characters": [], "quests": [], "assets": [], "scenes": scenes,
        "world": {"enabled": False, "width": 960, "height": 540, "sprites": [],
                  "player": {"x": 40, "y": 40, "width": 28, "height": 40, "speed": 3, "color": "#42d7e8"}},
        "world3d": {"enabled": False, "title": "جهان سه‌بعدی", "objects": [],
                    "player": {"position": [0, 1, 6], "camera_mode": "third_person",
                               "camera_distance": 7, "speed": 5, "sensitivity": 0.2},
                    "gravity": 9.81,
                    "lighting": {"ambient": 0.45, "directional": 0.9, "direction": [-0.5, -1, -0.3]}}
    }


def _scene(scene_id, title, text, image, choices=None):
    return {"id": scene_id, "title": title, "text": text, "image": image,
            "choices": choices or []}


def templates():
    """Return lightweight, ready-to-open starter projects."""
    romance = _base("نامه‌ای زیر باران", "rainy-letter", [
        _scene("station", "ایستگاه آخر", "باران آرام روی سقف ایستگاه می‌بارد. نامه‌ای خیس کنار نیمکت افتاده است.", _svg_data("نامه‌ای زیر باران", "#243c66", "#334155", "#f5c77b", "ایستگاه قطار، ساعت ۸ شب"),
               [{"id": "read", "text": "نامه را بخوان", "target": "letter", "conditions": [], "effects": []},
                {"id": "leave", "text": "به خانه برگرد", "target": "ending_home", "conditions": [], "effects": []}]),
        _scene("letter", "دستخط آشنا", "«اگر هنوز صدای باران را دوست داری، فردا همان‌جا منتظرت می‌مانم.» امضا: سارا.", _svg_data("دستخط آشنا", "#493d63", "#25243d", "#f3b6c8", "یک نامه و خاطره‌ای قدیمی"),
               [{"id": "meet", "text": "فردا به دیدار برو", "target": "ending_together", "conditions": [], "effects": []},
                {"id": "wait", "text": "این بار عجله نکن", "target": "ending_home", "conditions": [], "effects": []}]),
        _scene("ending_together", "پایان؛ دوباره", "فردا، زیر همان باران، دو نفر پس از سال‌ها سکوت لبخند می‌زنند. گاهی یک نامه برای شروع دوباره کافی است.", _svg_data("دوباره", "#7b536b", "#392b43", "#ffd6a5", "پایان کوتاه عاشقانه")),
        _scene("ending_home", "پایان؛ خاطره", "نامه را تا می‌کنی و در جیب می‌گذاری. شاید بعضی داستان‌ها هنوز تمام نشده باشند.", _svg_data("خاطره", "#35435c", "#202b3c", "#a7c7e7", "پایانی آرام"))
    ])
    workshop = _base("کارگاه شماره ۷", "workshop-07", [
        _scene("arrival", "ورود به کارگاه", "چراغ‌های سقفی یکی‌یکی روشن می‌شوند. بوی روغن و فلز در هواست. دستگاه اصلی از کار افتاده است.", _svg_data("کارگاه شماره ۷", "#4b5c70", "#27394b", "#f5b942", "سوله صنعتی با نور سقفی"),
               [{"id": "inspect", "text": "تابلو برق را بررسی کن", "target": "panel", "conditions": [], "effects": []},
                {"id": "tools", "text": "جعبه ابزار را بردار", "target": "tools", "conditions": [], "effects": [{"type": "item", "name": "آچار", "action": "add", "count": 1}]}]),
        _scene("panel", "تابلو برق", "سه چراغ هشدار قرمز روشن‌اند. صدای فن از اتاق کنترل می‌آید.", _svg_data("تابلو برق", "#283b55", "#111d2c", "#ff6b6b", "پنل کنترل و چراغ‌های هشدار"),
               [{"id": "reset", "text": "کلید اضطراری را بزن", "target": "restart", "conditions": [], "effects": []},
                {"id": "back", "text": "بازگشت به ورودی", "target": "arrival", "conditions": [], "effects": []}]),
        _scene("tools", "جعبه ابزار", "آچار سنگین و چراغ‌قوه را برمی‌داری. روی میز نقشه‌ای از موتورخانه دیده می‌شود.", _svg_data("جعبه ابزار", "#42566b", "#1a2937", "#e9b44c", "ابزارها روی میز فلزی"),
               [{"id": "engine", "text": "به موتورخانه برو", "target": "engine", "conditions": [], "effects": []}]),
        _scene("engine", "موتورخانه", "لرزش موتور بیشتر شده است. با آچار پیچ شل‌شده را محکم می‌کنی و دستگاه آرام می‌شود.", _svg_data("موتورخانه", "#354b61", "#182431", "#f5b942", "موتور صنعتی و نور حجمی")),
        _scene("restart", "راه‌اندازی مجدد", "چراغ‌ها سبز می‌شوند و کارگاه دوباره جان می‌گیرد. مأموریت با موفقیت انجام شد.", _svg_data("سیستم پایدار", "#315b55", "#142d2b", "#8be0b1", "چراغ‌های سبز و پایان مأموریت"))
    ])
    workshop["world3d"].update({"enabled": True, "title": "کارگاه صنعتی"})
    workshop["world3d"]["objects"] = [
        {"id": "floor", "shape": "box", "position": [0, -0.5, 0], "scale": [18, 1, 14], "color": "#354353", "role": "obstacle", "solid": True},
        {"id": "machine_body", "shape": "box", "position": [0, 1.1, 0], "scale": [3.2, 2.2, 2.4], "color": "#718096", "role": "obstacle", "solid": True},
        {"id": "warning_light", "shape": "sphere", "position": [0, 2.6, 0], "scale": [0.35, 0.35, 0.35], "color": "#ff5b5b", "role": "decoration", "solid": False},
        {"id": "tool_crate", "shape": "box", "position": [3, 0.5, 2], "scale": [1.2, 1, 1], "color": "#c18b45", "role": "obstacle", "solid": True}
    ]
    workshop["world3d"]["lighting"] = {"ambient": 0.32, "directional": 1.2, "direction": [-0.6, -1, -0.25]}
    battle = _base("پایگاه نبرد", "battle-base", [
        _scene("briefing", "اتاق فرماندهی", "پایگاه در وضعیت هشدار است. سه هدف آموزشی را پیدا کن و مسیر امن را باز نگه دار.", _svg_data("پایگاه نبرد", "#263d56", "#172333", "#56cfe1", "اتاق فرماندهی پایگاه")),
        _scene("debrief", "پایان تمرین", "تمرین تمام شد. حالا می‌توانی نقشه، دشمن‌ها و نورپردازی را در جهان سه‌بعدی تغییر بدهی.", _svg_data("تمرین کامل شد", "#315b55", "#142d2b", "#8be0b1", "پایان مرحله آموزشی"))
    ])
    battle["world3d"].update({"enabled": True, "title": "پایگاه نبرد"})
    battle["world3d"]["objects"] = [
        {"id": "base_floor", "shape": "box", "position": [0, -0.5, 0], "scale": [24, 1, 24], "color": "#35485c", "role": "obstacle", "solid": True},
        {"id": "command_center", "shape": "box", "position": [0, 1.5, -5], "scale": [7, 3, 3], "color": "#52677c", "role": "obstacle", "solid": True},
        {"id": "training_enemy", "shape": "box", "position": [4, 0.8, 3], "scale": [1, 1.8, 1], "color": "#d64b59", "role": "enemy", "solid": True, "health": 30, "speed": 1.6, "damage": 5},
        {"id": "target_01", "shape": "sphere", "position": [-4, 1, 2], "scale": [0.7, 0.7, 0.7], "color": "#e5b84b", "role": "target", "solid": True}
    ]
    return {
        "داستان عاشقانه کوتاه": romance,
        "کارگاه متوسط سه‌بعدی": workshop,
        "بتل‌بیس سه‌بعدی": battle,
        "داستان آموزشی": _base("ماجراجویی تازه", "starter-story", [
            _scene("start", "شروع", "این پروژه برای یادگیری صحنه، انتخاب و مسیر داستان آماده شده است.", _svg_data("ماجراجویی تازه", "#294765", "#172333", "#70d6ff", "پروژه آموزشی Monn"),
                   [{"id": "next", "text": "ادامه", "target": "finish", "conditions": [], "effects": []}]),
            _scene("finish", "پایان", "حالا متن و انتخاب‌ها را تغییر بده و بازی خودت را بساز.", _svg_data("پایان", "#315b55", "#142d2b", "#8be0b1", "پایان نمونه"))
        ])
    }


def build_offline_project(prompt="", template="starter"):
    """Build a complete project using deterministic templates and rule-based parsing."""
    catalog = templates()
    key = str(template or "").strip().lower()
    aliases = {
        "romance": "داستان عاشقانه کوتاه", "romance_short": "داستان عاشقانه کوتاه",
        "workshop": "کارگاه متوسط سه‌بعدی", "workshop_medium": "کارگاه متوسط سه‌بعدی",
        "battle": "بتل‌بیس سه‌بعدی", "battle_base": "بتل‌بیس سه‌بعدی",
        "story": "داستان آموزشی", "starter": "داستان آموزشی",
    }
    selected = catalog.get(aliases.get(key, template), catalog["داستان آموزشی"])
    result = copy.deepcopy(selected)
    text = unicodedata.normalize("NFKC", str(prompt or "")).strip()
    if text:
        result["meta"]["title"] = text[:64]
        words = set(re.findall(r"[\wآ-ی]+", text.lower()))
        if words.intersection({"جنگ", "نبرد", "دشمن", "اسلحه", "پایگاه", "بتل", "battle"}):
            result = copy.deepcopy(catalog["بتل‌بیس سه‌بعدی"])
            result["meta"]["title"] = text[:64]
        elif words.intersection({"کارگاه", "کارخانه", "مکانیک", "ماشین", "صنعتی"}):
            result = copy.deepcopy(catalog["کارگاه متوسط سه‌بعدی"])
            result["meta"]["title"] = text[:64]
        elif words.intersection({"عشق", "عاشقانه", "نامه", "باران", "قرار"}):
            result = copy.deepcopy(catalog["داستان عاشقانه کوتاه"])
            result["meta"]["title"] = text[:64]
        elif len(text) > 24:
            first = result["scenes"][0]
            first["text"] = text[:420] + " این ایده با الگوهای داخلی Monn به یک پروژهٔ قابل ویرایش تبدیل شده است."
    return result
