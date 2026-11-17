"""Nitro: local-first, permission-gated assistant for Monn projects.

Nitro never executes generated code. It accepts a small allow-list of structured
project-editing operations, validates the resulting project, and requires an
explicit approval request before returning the edited project.
"""
import copy
import hashlib
import json
import math
import secrets
import ipaddress
from urllib.parse import urlsplit
import urllib.error
import urllib.request

from .game import GameProject


def project_fingerprint(project):
    raw = json.dumps(project, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class NitroError(Exception):
    """A safe, user-facing Nitro error."""


class NitroAgent:
    DEFAULT_URL = "http://127.0.0.1:11434/api/chat"
    DEFAULT_MODEL = "qwen2.5:7b"

    def __init__(self, endpoint=None, model=None, timeout=120):
        self.endpoint = (endpoint or self.DEFAULT_URL).strip()
        parsed = urlsplit(self.endpoint)
        host = (parsed.hostname or "").lower()
        is_loopback = host == "localhost"
        try:
            is_loopback = is_loopback or ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        if parsed.scheme != "http" or not is_loopback or not parsed.port or not parsed.path.startswith("/"):
            raise NitroError("نیترو در این نسخه فقط به سرویس HTTP محلی روی localhost یا loopback وصل می‌شود.")
        self.model = (model or self.DEFAULT_MODEL).strip()
        if not self.model or len(self.model) > 120:
            raise NitroError("نام مدل محلی معتبر نیست.")
        self.timeout = max(5, min(int(timeout), 300))

    @staticmethod
    def vocabulary():
        return {
            "scene": "صحنه؛ یک بخش مستقل از بازی",
            "choice": "انتخاب؛ مسیر یا کنش بازیکن برای رفتن به صحنه دیگر",
            "character": "شخصیت؛ بازیگر یا NPC دارای نام و نقش",
            "npc": "شخصیت غیرقابل‌بازی؛ موجودیت دارای رفتار در جهان",
            "branch": "شاخه؛ مسیر جایگزین در روایت",
            "quest": "مأموریت؛ هدف چندمرحله‌ای بازیکن",
            "stat": "ویژگی؛ مقدار عددی مانند جان، امتیاز یا سکه",
            "flag": "پرچم؛ وضعیت روشن/خاموش یک رویداد",
            "inventory": "کوله‌پشتی؛ فهرست آیتم‌های بازیکن",
            "asset": "دارایی؛ تصویر، صدا، ویدیو، فونت یا مدل",
            "sprite": "اسپرایت؛ تصویر دوبعدی یک شیء یا شخصیت",
            "tilemap": "نقشه کاشی‌ای؛ چیدمان مرحله با قطعه‌های تکرارشونده",
            "camera": "دوربین؛ نمای دید بازیکن یا قاب صحنه",
            "collision": "برخورد؛ تشخیص تماس اجسام در جهان بازی",
            "rigid_body": "جسم صلب؛ شیء دارای جرم و واکنش فیزیکی",
            "raycast": "پرتوکاوی؛ بررسی برخورد در امتداد یک خط",
            "projectile": "پرتابه؛ گلوله یا شیء پرتاب‌شده",
            "weapon": "سلاح؛ ابزار حمله با نرخ شلیک و آسیب",
            "damage": "آسیب؛ کاهش جان هدف",
            "health": "جان؛ میزان سلامت بازیکن یا دشمن",
            "enemy": "دشمن؛ عامل مخالف با جان و رفتار",
            "pathfinding": "مسیریابی؛ پیدا کردن مسیر حرکت عامل",
            "animation": "انیمیشن؛ تغییر حالت یا حرکت در طول زمان",
            "keyframe": "فریم کلیدی؛ نقطه تعیین‌شده در انیمیشن",
            "material": "متریال؛ ویژگی ظاهری سطح مدل",
            "texture": "بافت؛ تصویر پوشاننده سطح مدل",
            "lighting": "نورپردازی؛ نور و سایه صحنه",
            "scene_graph": "درخت صحنه؛ ساختار والد و فرزند اشیا",
            "prefab": "نمونه آماده؛ الگوی قابل استفاده مجدد از اشیا",
            "input": "ورودی؛ فرمان صفحه‌کلید، ماوس، کنترلر یا لمس",
            "audio": "صدا؛ موسیقی، افکت و گفتار",
            "save": "ذخیره؛ نگهداری پیشرفت بازی",
            "build": "خروجی؛ بسته قابل اجرا یا انتشار بازی",
            "plugin": "افزونه؛ قابلیت مستقل قابل اضافه شدن",
            "3d_model": "مدل سه‌بعدی؛ دارایی هندسی قابل نمایش در صحنه",
            "ui": "رابط کاربری؛ منو، دکمه، متن و ورودی",
            "timeline": "تایم‌لاین؛ زمان‌بندی ویدیو، صدا و انیمیشن",
            "multiplayer": "چندنفره؛ همگام‌سازی بازی میان چند دستگاه",
            "physics": "فیزیک؛ حرکت، نیرو، جرم و برخورد اجسام",
            "fps": "نرخ فریم؛ تعداد فریم‌های نمایش در هر ثانیه",
            "third_person": "سوم‌شخص؛ دوربین پشت یا کنار شخصیت",
            "first_person": "اول‌شخص؛ دوربین از دید چشم بازیکن",
        }

    def _system_prompt(self):
        vocabulary = json.dumps(self.vocabulary(), ensure_ascii=False)
        return (
            "تو نیترو هستی؛ دستیار فارسی‌زبان طراحی بازی در Monn Studio. "
            "وظیفه‌ات فهم درخواست سازنده و پیشنهاد تغییرهای دقیق و کوچک در پروژه است. "
            "فقط JSON معتبر و بدون Markdown برگردان، با ساختار "
            '{"summary":"توضیح فارسی","operations":[...]}. '
            "هیچ کد اجرایی، اسکریپت، HTML، JavaScript، Python، مسیر فایل دلخواه، "
            "دستور سیستم‌عامل، درخواست شبکه یا ابزار خارجی تولید نکن. "
            "فقط از عملیات مجاز استفاده کن: "
            "set_title {value}; set_scene_text {scene_id,value}; "
            "add_scene {id,title,text}; add_choice {scene_id,id,text,target}; "
            "add_character {id,name,role}; set_player_stat {name,value}; "
            "add_quest {id,title}; add_world_sprite {id,x,y,width,height,solid}; "
            "add_ui_element {id,element_type,text,x,y,width,height}; "
            "add_dialogue {scene_id,character,text}; set_scene_media {scene_id,field,value}; "
            "add_world3d_object {id,shape,position,scale,color,solid,role,model,health}; "
            "set_world3d_player {position,speed,sensitivity}; set_world3d_gravity {value}. "
            "برای add_world3d_object شکل box یا sphere یا model انتخاب کن؛ position و scale آرایه سه‌عددی‌اند؛ "
            "role یکی از decoration یا obstacle یا enemy یا target است. برای enemy مقدارهای health و speed و damage را هم تنظیم کن. "
            "برای بازیکن سه‌بعدی position سه‌بعدی، speed بین ۰٫۵ تا ۴۰ و sensitivity بین ۰٫۰۲ تا ۱ است؛ "
            "گرانش بین صفر تا ۱۰۰ قرار می‌گیرد. "
            "شناسه‌ها باید انگلیسی ساده و یکتا باشند. مقصد انتخاب باید شناسه صحنه موجود "
            "یا صحنه‌ای باشد که در همین پیشنهاد ساخته می‌شود. "
            "اگر اطلاعات کافی نیست، operations را خالی بگذار و در summary سؤال روشن بپرس. "
            "از فارسی روان و اصطلاحات زیر استفاده کن: " + vocabulary
        )

    def propose(self, project, prompt):
        if not isinstance(prompt, str) or not prompt.strip():
            raise NitroError("درخواستت را برای نیترو بنویس.")
        if len(prompt) > 6000:
            raise NitroError("درخواست نیترو بیش از حد طولانی است.")
        validated = GameProject(project)
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": "پروژه فعلی:\n" +
                 json.dumps(validated.data, ensure_ascii=False) +
                 "\n\nدرخواست سازنده:\n" + prompt.strip()},
            ],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise NitroError(
                "به مدل محلی وصل نشدم. مطمئن شو Ollama روشن است و مدل را نصب کرده‌ای. "
                "جزئیات: " + str(exc)
            ) from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise NitroError("پاسخ مدل محلی قابل خواندن نبود.") from exc
        content = (result.get("message") or {}).get("content", "")
        try:
            plan = json.loads(content)
        except (TypeError, ValueError) as exc:
            raise NitroError("نیترو نتوانست پیشنهاد ساختاریافته بسازد؛ دوباره تلاش کن.") from exc
        if not isinstance(plan, dict) or not isinstance(plan.get("operations", []), list):
            raise NitroError("ساختار پیشنهاد نیترو معتبر نیست.")
        operations = plan.get("operations", [])
        if len(operations) > 30:
            raise NitroError("هر پیشنهاد حداکثر می‌تواند ۳۰ تغییر داشته باشد.")
        candidate = self.apply_operations(validated.data, operations)
        return {
            "id": secrets.token_urlsafe(18),
            "summary": str(plan.get("summary", "پیشنهاد آماده بررسی است"))[:1200],
            "operations": operations,
            "project": candidate,
            "before": project_fingerprint(validated.data),
            "after": project_fingerprint(candidate),
        }

    @staticmethod
    def apply_operations(project, operations):
        candidate = copy.deepcopy(project)
        scenes = candidate.setdefault("scenes", [])
        characters = candidate.setdefault("characters", [])
        scene_ids = {scene.get("id") for scene in scenes}
        character_ids = {character.get("id") for character in characters}
        allowed = {"set_title", "set_scene_text", "add_scene", "add_choice", "add_character", "set_player_stat", "add_quest", "add_dialogue", "add_ui_element", "add_world_sprite", "set_scene_media", "add_world3d_object", "set_world3d_player", "set_world3d_gravity"}
        for index, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise NitroError("تغییر شماره {} معتبر نیست.".format(index + 1))
            kind = operation.get("type")
            if kind not in allowed:
                raise NitroError("این نوع تغییر مجاز نیست: {}".format(kind))
            if kind == "set_title":
                value = operation.get("value")
                if not isinstance(value, str) or not value.strip() or len(value) > 160:
                    raise NitroError("عنوان بازی باید متن ۱ تا ۱۶۰ نویسه‌ای باشد.")
                candidate.setdefault("meta", {})["title"] = value.strip()
            elif kind == "set_scene_text":
                scene = next((item for item in scenes if item.get("id") == operation.get("scene_id")), None)
                value = operation.get("value")
                if scene is None or not isinstance(value, str) or len(value) > 12000:
                    raise NitroError("صحنه یا متن ویرایش‌شده معتبر نیست.")
                scene["text"] = value
            elif kind == "add_scene":
                scene_id = operation.get("id")
                title, text = operation.get("title"), operation.get("text", "")
                if not isinstance(scene_id, str) or not scene_id.isascii() or not scene_id.replace("_", "").replace("-", "").isalnum() or scene_id in scene_ids:
                    raise NitroError("شناسه صحنه جدید باید انگلیسی، یکتا و ساده باشد.")
                if not isinstance(title, str) or not title.strip() or len(title) > 160 or not isinstance(text, str) or len(text) > 12000:
                    raise NitroError("عنوان یا متن صحنه جدید معتبر نیست.")
                scenes.append({"id": scene_id, "title": title.strip(), "text": text, "choices": []})
                scene_ids.add(scene_id)
            elif kind == "add_choice":
                scene = next((item for item in scenes if item.get("id") == operation.get("scene_id")), None)
                choice_id, target = operation.get("id"), operation.get("target")
                text = operation.get("text")
                if scene is None or target not in scene_ids or not isinstance(choice_id, str) or not choice_id.isascii() or not choice_id.replace("_", "").replace("-", "").isalnum() or not isinstance(text, str) or not text.strip():
                    raise NitroError("انتخاب جدید باید شناسه، متن و مقصد معتبر داشته باشد.")
                if any(choice.get("id") == choice_id for item in scenes for choice in item.get("choices", [])):
                    raise NitroError("شناسه انتخاب تکراری است.")
                scene.setdefault("choices", []).append({
                    "id": choice_id, "text": text.strip(), "target": target,
                    "conditions": [], "effects": [],
                })
            elif kind == "add_character":
                character_id, name = operation.get("id"), operation.get("name")
                role = operation.get("role", "")
                if not isinstance(character_id, str) or not character_id.isascii() or not character_id.replace("_", "").replace("-", "").isalnum() or character_id in character_ids:
                    raise NitroError("شناسه شخصیت جدید باید انگلیسی و یکتا باشد.")
                if not isinstance(name, str) or not name.strip() or len(name) > 120 or not isinstance(role, str) or len(role) > 500:
                    raise NitroError("نام یا نقش شخصیت معتبر نیست.")
                characters.append({"id": character_id, "name": name.strip(), "role": role})
                character_ids.add(character_id)
            elif kind == "set_player_stat":
                name, value = operation.get("name"), operation.get("value")
                if not isinstance(name, str) or not name.strip() or len(name) > 80 or isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise NitroError("نام یا مقدار ویژگی بازیکن معتبر نیست.")
                candidate.setdefault("player", {}).setdefault("stats", {})[name.strip()] = value
            elif kind == "add_quest":
                quest_id, title = operation.get("id"), operation.get("title")
                quests = candidate.setdefault("quests", [])
                if not isinstance(quest_id, str) or not quest_id.isascii() or not quest_id.replace("_", "").replace("-", "").isalnum() or any(q.get("id") == quest_id for q in quests):
                    raise NitroError("شناسه مأموریت باید انگلیسی و یکتا باشد.")
                if not isinstance(title, str) or not title.strip() or len(title) > 160:
                    raise NitroError("عنوان مأموریت معتبر نیست.")
                quests.append({"id": quest_id, "title": title.strip()})
            elif kind == "add_dialogue":
                scene = next((item for item in scenes if item.get("id") == operation.get("scene_id")), None)
                character, line = operation.get("character"), operation.get("text")
                if scene is None or character not in character_ids or not isinstance(line, str) or not line.strip() or len(line) > 4000:
                    raise NitroError("گفت‌وگو باید به صحنه و شخصیت موجود متصل باشد.")
                scene.setdefault("dialogue", []).append({"character": character, "text": line.strip()})
            elif kind == "add_ui_element":
                element_id, element_type = operation.get("id"), operation.get("element_type", "text")
                ui = candidate.setdefault("ui", {"elements": []})
                elements = ui.setdefault("elements", [])
                if not isinstance(element_id, str) or not element_id.isascii() or not element_id.replace("_", "").replace("-", "").isalnum() or any(el.get("id") == element_id for el in elements):
                    raise NitroError("شناسه عنصر رابط باید انگلیسی و یکتا باشد.")
                if element_type not in ("text", "button", "name_input", "location", "image", "panel"):
                    raise NitroError("نوع عنصر رابط مجاز نیست.")
                element = {"id": element_id, "type": element_type, "text": str(operation.get("text", ""))[:500]}
                for field, default in (("x", 5), ("y", 5), ("width", 30), ("height", 12)):
                    value = operation.get(field, default)
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
                        raise NitroError("مختصات و اندازه رابط باید بین صفر تا صد باشند.")
                    element[field] = value
                elements.append(element)
            elif kind == "add_world_sprite":
                sprite_id = operation.get("id")
                world = candidate.setdefault("world", {"enabled": True, "width": 800, "height": 450, "sprites": []})
                sprites = world.setdefault("sprites", [])
                if not isinstance(sprite_id, str) or not sprite_id.isascii() or not sprite_id.replace("_", "").replace("-", "").isalnum() or any(item.get("id") == sprite_id for item in sprites):
                    raise NitroError("شناسه شیء دوبعدی باید انگلیسی و یکتا باشد.")
                sprite = {"id": sprite_id, "solid": bool(operation.get("solid", False))}
                for field, default in (("x", 40), ("y", 40), ("width", 32), ("height", 32)):
                    value = operation.get(field, default)
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 10000:
                        raise NitroError("موقعیت و اندازه شیء دوبعدی معتبر نیست.")
                    sprite[field] = value
                sprites.append(sprite)
                world["enabled"] = True
            elif kind == "add_world3d_object":
                object_id = operation.get("id")
                world = candidate.setdefault("world3d", {"enabled": True, "objects": []})
                objects = world.setdefault("objects", [])
                if not isinstance(object_id, str) or not object_id.isascii() or not object_id.replace("_", "").replace("-", "").isalnum() or any(item.get("id") == object_id for item in objects):
                    raise NitroError("شناسه شیء سه‌بعدی باید انگلیسی و یکتا باشد.")
                shape = operation.get("shape", "box")
                role = operation.get("role", "decoration")
                if shape not in ("box", "sphere", "model") or role not in ("decoration", "obstacle", "enemy", "target"):
                    raise NitroError("شکل یا نقش شیء سه‌بعدی معتبر نیست.")
                def vector(field, default, positive=False):
                    value = operation.get(field, default)
                    if not isinstance(value, (list, tuple)) or len(value) != 3:
                        raise NitroError("مقدار {} باید سه عدد داشته باشد.".format(field))
                    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or (positive and v <= 0) for v in value):
                        raise NitroError("مقادیر {} معتبر نیستند.".format(field))
                    return [float(v) for v in value]
                color = operation.get("color", "#6b91b8")
                if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
                    raise NitroError("رنگ شیء سه‌بعدی باید به صورت #RRGGBB باشد.")
                try:
                    int(color[1:], 16)
                except ValueError as exc:
                    raise NitroError("کد رنگ شیء سه‌بعدی معتبر نیست.") from exc
                entry = {
                    "id": object_id, "shape": shape,
                    "position": vector("position", [0, 0, 0]),
                    "scale": vector("scale", [1, 1, 1], positive=True),
                    "color": color, "solid": bool(operation.get("solid", role == "obstacle")),
                    "role": role,
                }
                if shape == "model":
                    model = operation.get("model")
                    if not isinstance(model, str) or not model.strip() or "://" in model or ".." in model.split("/"):
                        raise NitroError("مدل باید مسیر فایل محلی معتبر باشد.")
                    entry["model"] = model
                if role in ("enemy", "target"):
                    health = operation.get("health", 3)
                    if isinstance(health, bool) or not isinstance(health, int) or not 1 <= health <= 100000:
                        raise NitroError("جان دشمن یا هدف باید عددی بین ۱ تا ۱۰۰۰۰۰ باشد.")
                    entry["health"] = health
                if role == "enemy":
                    speed = operation.get("speed", 2.2)
                    damage = operation.get("damage", 8)
                    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not math.isfinite(speed) or not 0 <= speed <= 20:
                        raise NitroError("سرعت دشمن باید عددی بین صفر تا ۲۰ باشد.")
                    if isinstance(damage, bool) or not isinstance(damage, int) or not 0 <= damage <= 10000:
                        raise NitroError("آسیب دشمن باید عددی بین صفر تا ۱۰۰۰۰ باشد.")
                    entry["speed"] = float(speed)
                    entry["damage"] = damage
                objects.append(entry)
                world["enabled"] = True
                from .engine3d import validate_world3d
                validate_world3d(candidate)
            elif kind == "set_world3d_player":
                world = candidate.setdefault("world3d", {"enabled": True, "objects": []})
                player = world.setdefault("player", {})
                position = operation.get("position", player.get("position", [0, -8, 1.7]))
                if not isinstance(position, (list, tuple)) or len(position) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in position):
                    raise NitroError("موقعیت بازیکن سه‌بعدی باید سه عدد معتبر داشته باشد.")
                player["position"] = [float(v) for v in position]
                for field, low, high in (("speed", 0.5, 40), ("sensitivity", 0.02, 1)):
                    if field in operation:
                        value = operation[field]
                        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                            raise NitroError("مقدار {} خارج از محدوده مجاز است.".format(field))
                        player[field] = float(value)
                world["enabled"] = True
                from .engine3d import validate_world3d
                validate_world3d(candidate)
            elif kind == "set_world3d_gravity":
                value = operation.get("value")
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
                    raise NitroError("گرانش باید عددی بین صفر تا ۱۰۰ باشد.")
                world = candidate.setdefault("world3d", {"enabled": True, "objects": []})
                world["gravity"] = float(value)
                world["enabled"] = True
                from .engine3d import validate_world3d
                validate_world3d(candidate)
            elif kind == "set_scene_media":
                scene = next((item for item in scenes if item.get("id") == operation.get("scene_id")), None)
                field, value = operation.get("field"), operation.get("value")
                if scene is None or field not in ("image", "video", "music") or not isinstance(value, str) or len(value) > 2000 or "://" in value or ".." in value:
                    raise NitroError("رسانه باید مسیر دارایی محلی معتبر باشد.")
                scene[field] = value
        try:
            return GameProject(candidate).data
        except Exception as exc:
            raise NitroError("اعتبارسنجی تغییرهای پیشنهادی ناموفق بود: " + str(exc)) from exc

    @staticmethod
    def approve(proposal, current_project):
        if not isinstance(proposal, dict) or proposal.get("before") != project_fingerprint(current_project):
            raise NitroError("پروژه پس از تهیه پیشنهاد تغییر کرده؛ برای جلوگیری از بازنویسی، دوباره پیشنهاد بگیر.")
        candidate = proposal.get("project")
        if not isinstance(candidate, dict) or project_fingerprint(candidate) != proposal.get("after"):
            raise NitroError("پیشنهاد دست‌کاری شده یا معتبر نیست.")
        return GameProject(candidate).data
