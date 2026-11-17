"""Nitro: local-first, permission-gated assistant for Monn projects.

Nitro never executes generated code. It accepts a small allow-list of structured
project-editing operations, validates the resulting project, and requires an
explicit approval request before returning the edited project.
"""
import copy
import hashlib
import json
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
            "branch": "شاخه؛ مسیر جایگزین در روایت",
            "quest": "مأموریت؛ هدف چندمرحله‌ای بازیکن",
            "stat": "ویژگی؛ مقدار عددی مانند جان، امتیاز یا سکه",
            "flag": "پرچم؛ وضعیت روشن/خاموش یک رویداد",
            "asset": "دارایی؛ تصویر، صدا، ویدیو یا مدل",
            "sprite": "اسپرایت؛ تصویر دوبعدی یک شیء یا شخصیت",
            "collision": "برخورد؛ تشخیص تماس اجسام در جهان بازی",
            "3d_model": "مدل سه‌بعدی؛ دارایی هندسی قابل نمایش در صحنه",
            "ui": "رابط کاربری؛ منو، دکمه، متن و ورودی",
            "timeline": "تایم‌لاین؛ زمان‌بندی ویدیو، صدا و انیمیشن",
            "multiplayer": "چندنفره؛ همگام‌سازی بازی میان چند دستگاه",
            "physics": "فیزیک؛ حرکت، نیرو، جرم و برخورد اجسام",
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
            "add_character {id,name,role}. "
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
        allowed = {"set_title", "set_scene_text", "add_scene", "add_choice", "add_character"}
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
