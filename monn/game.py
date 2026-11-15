"""Portable narrative-game runtime for MonnLang.

The engine is UI-agnostic: the same project and state model can power a CLI,
Tkinter front-end, browser export, or a future multiplayer transport.
"""
import copy
import hashlib
import json
import os
import tempfile
from urllib.parse import urlsplit

ENGINE_VERSION = 1
MAX_HEALTH = 1000000
MAX_ITEMS = 1000000
COMPARATORS = {
    "==": lambda a, b: a == b,
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
}


class GameError(Exception):
    """Base error raised by the Monn game engine."""


class GameValidationError(GameError):
    """The game project is malformed or references missing content."""


class GameStateError(GameError):
    """An action is invalid for the current game state."""


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise GameValidationError("{} باید متن غیرخالی باشد".format(label))
    return value.strip()


def _safe_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GameValidationError("{} باید عدد باشد".format(label))
    if value != value or value in (float("inf"), float("-inf")):
        raise GameValidationError("{} باید عدد متناهی باشد".format(label))
    return value



PERSIAN_VALUE_ALIASES = {
    "ویژگی": "stat", "جان": "health", "پرچم": "flag",
    "آیتم": "item", "مأموریت": "quest", "ماموریت": "quest", "دفترچه": "journal",
    "افزودن": "add", "تنظیم": "set", "کاهش": "subtract",
    "مصرف": "remove", "شروع": "start", "تکمیل": "complete",
    "شکست": "fail", "برابر": "==", "نابرابر": "!=",
    "بزرگتر": ">", "کوچکتر": "<",
    "بزرگتر_مساوی": ">=", "کوچکتر_مساوی": "<=",
}


def _rename_fields(value, aliases):
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        english = aliases.get(key, key)
        if english not in result or key == english:
            result[english] = item
    return result


def normalize_project_data(data):
    """Accept Persian field names alongside the canonical JSON schema."""
    root = _rename_fields(data, {
        "اطلاعات": "meta", "مشخصات": "meta", "بازیکن": "player",
        "شخصیت‌ها": "characters", "شخصیت_ها": "characters",
        "مأموریت‌ها": "quests", "ماموریت‌ها": "quests",
        "صحنه‌ها": "scenes", "صحنه_ها": "scenes",
    })
    if not isinstance(root, dict):
        return root
    if "meta" in root:
        root["meta"] = _rename_fields(root["meta"], {
            "شناسه": "id", "عنوان": "title", "صحنه_شروع": "start_scene",
            "شروع": "start_scene",
        })
    if "player" in root:
        root["player"] = _rename_fields(root["player"], {
            "جان": "health", "حداکثر_جان": "max_health",
            "ویژگی‌ها": "stats", "ویژگی_ها": "stats",
            "کوله_پشتی": "inventory", "کوله‌پشتی": "inventory",
        })
    for field in ("quests", "characters"):
        if field in root and isinstance(root[field], list):
            normalized = []
            for item in root[field]:
                aliases = {"شناسه": "id", "عنوان": "title", "نام": "name",
                           "پرتره": "portrait"}
                normalized.append(_rename_fields(item, aliases))
            root[field] = normalized
    if "scenes" in root and isinstance(root["scenes"], list):
        scenes = []
        for raw_scene in root["scenes"]:
            scene = _rename_fields(raw_scene, {
                "شناسه": "id", "عنوان": "title", "روایت": "text",
                "متن": "text", "انتخاب‌ها": "choices", "انتخاب_ها": "choices",
                "تصویر": "image", "موسیقی": "music", "گفتگو": "dialogue",
                "گفت‌وگو": "dialogue",
            })
            if isinstance(scene, dict):
                if isinstance(scene.get("dialogue"), list):
                    scene["dialogue"] = [
                        _rename_fields(line, {
                            "شخصیت": "character", "گوینده": "speaker",
                            "متن": "text", "پرتره": "portrait",
                        }) for line in scene["dialogue"]
                    ]
                choices = scene.get("choices", [])
                if isinstance(choices, list):
                    normalized_choices = []
                    for raw_choice in choices:
                        choice = _rename_fields(raw_choice, {
                            "شناسه": "id", "متن": "text", "مقصد": "target",
                            "شرط‌ها": "conditions", "شرط_ها": "conditions",
                            "اثرها": "effects", "اثر_ها": "effects",
                        })
                        if isinstance(choice, dict):
                            conditions = choice.get("conditions", [])
                            if isinstance(conditions, list):
                                choice["conditions"] = [
                                    _normalize_condition(item) for item in conditions
                                ]
                            effects = choice.get("effects", [])
                            if isinstance(effects, list):
                                choice["effects"] = [
                                    _normalize_effect(item) for item in effects
                                ]
                        normalized_choices.append(choice)
                    scene["choices"] = normalized_choices
            scenes.append(scene)
        root["scenes"] = scenes
    return root


def _normalize_condition(value):
    item = _rename_fields(value, {
        "نوع": "type", "نام": "name", "شناسه": "id",
        "عملگر": "op", "مقدار": "value",
    })
    if isinstance(item, dict):
        item["type"] = PERSIAN_VALUE_ALIASES.get(item.get("type"), item.get("type"))
        item["op"] = PERSIAN_VALUE_ALIASES.get(item.get("op"), item.get("op"))
    return item


def _normalize_effect(value):
    item = _rename_fields(value, {
        "نوع": "type", "نام": "name", "شناسه": "id",
        "عملیات": "op", "کنش": "action", "مقدار": "value",
        "تعداد": "count", "متن": "text",
    })
    if isinstance(item, dict):
        item["type"] = PERSIAN_VALUE_ALIASES.get(item.get("type"), item.get("type"))
        item["op"] = PERSIAN_VALUE_ALIASES.get(item.get("op"), item.get("op"))
        item["action"] = PERSIAN_VALUE_ALIASES.get(item.get("action"), item.get("action"))
    return item


class GameProject:
    """Validated, immutable-by-convention story content."""

    def __init__(self, data):
        if not isinstance(data, dict):
            raise GameValidationError("ریشه پروژه بازی باید یک شیء JSON باشد")
        self.data = normalize_project_data(data)
        self.meta = self.data.get("meta", {})
        if not isinstance(self.meta, dict):
            raise GameValidationError("meta باید یک شیء باشد")
        self.title = _require_text(self.meta.get("title", "بازی Monn"), "عنوان بازی")
        self.project_id = str(self.meta.get("id") or self.title)
        self.start_scene = _require_text(self.meta.get("start_scene"), "صحنه شروع")
        self.player = self.data.get("player", {})
        if not isinstance(self.player, dict):
            raise GameValidationError("player باید یک شیء باشد")
        self.scenes = {}
        raw_scenes = self.data.get("scenes")
        if not isinstance(raw_scenes, list) or not raw_scenes:
            raise GameValidationError("پروژه باید حداقل یک صحنه داشته باشد")
        for raw in raw_scenes:
            if not isinstance(raw, dict):
                raise GameValidationError("هر صحنه باید یک شیء باشد")
            scene_id = _require_text(raw.get("id"), "شناسه صحنه")
            if scene_id in self.scenes:
                raise GameValidationError("شناسه صحنه تکراری است: " + scene_id)
            scene = copy.deepcopy(raw)
            scene["title"] = str(scene.get("title") or scene_id)
            scene["text"] = str(scene.get("text") or "")
            for asset_field in ("image", "music", "video", "model", "button_sound"):
                asset = scene.get(asset_field)
                if asset is not None:
                    self._validate_asset_ref(asset, asset_field)
            for timing in ("video_start", "video_end"):
                if timing in scene and _safe_number(scene[timing], timing) < 0:
                    raise GameValidationError("{} نمی‌تواند منفی باشد".format(timing))
            if scene.get("video_end") and _safe_number(scene["video_end"], "video_end") <= _safe_number(scene.get("video_start", 0), "video_start"):
                raise GameValidationError("پایان کلیپ صحنه باید بعد از شروع آن باشد")
            dialogue = scene.get("dialogue", [])
            if not isinstance(dialogue, list):
                raise GameValidationError("dialogue صحنه باید فهرست باشد")
            for line in dialogue:
                if not isinstance(line, dict):
                    raise GameValidationError("هر خط گفتگو باید یک شیء باشد")
                _require_text(line.get("text"), "متن گفتگو")
                for media_field in ("portrait", "video", "voice"):
                    if line.get(media_field) is not None:
                        self._validate_asset_ref(line[media_field], media_field)
                for timing in ("video_start", "video_end"):
                    if timing in line and _safe_number(line[timing], timing) < 0:
                        raise GameValidationError("{} دیالوگ نمی‌تواند منفی باشد".format(timing))
                if line.get("video_end") and _safe_number(line["video_end"], "video_end") <= _safe_number(line.get("video_start", 0), "video_start"):
                    raise GameValidationError("پایان کلیپ دیالوگ باید بعد از شروع آن باشد")
            choices = scene.get("choices", [])
            if not isinstance(choices, list):
                raise GameValidationError("choices صحنه باید فهرست باشد")
            choice_ids = set()
            for choice in choices:
                if not isinstance(choice, dict):
                    raise GameValidationError("هر انتخاب باید یک شیء باشد")
                _require_text(choice.get("text"), "متن انتخاب")
                if choice.get("id") is not None:
                    choice_id = _require_text(choice.get("id"), "شناسه انتخاب")
                    if choice_id in choice_ids:
                        raise GameValidationError("شناسه انتخاب تکراری است: " + choice_id)
                    choice_ids.add(choice_id)
                target = choice.get("target")
                if target is not None:
                    _require_text(target, "مقصد انتخاب")
                if choice.get("sound") is not None:
                    self._validate_asset_ref(choice["sound"], "choice sound")
                if not isinstance(choice.get("effects", []), list):
                    raise GameValidationError("effects باید فهرست باشد")
                if not isinstance(choice.get("conditions", []), list):
                    raise GameValidationError("conditions باید فهرست باشد")
            self.scenes[scene_id] = scene
        if self.start_scene not in self.scenes:
            raise GameValidationError("صحنه شروع در پروژه وجود ندارد")
        for scene in self.scenes.values():
            for choice in scene.get("choices", []):
                target = choice.get("target")
                if target is not None and target not in self.scenes:
                    raise GameValidationError(
                        "صحنه مقصد وجود ندارد: {}".format(target)
                    )
                self._validate_conditions(choice.get("conditions", []))
                for effect in choice.get("effects", []):
                    self._validate_effect(effect)
        self.characters = {}
        raw_characters = self.data.get("characters", [])
        if not isinstance(raw_characters, list):
            raise GameValidationError("characters باید فهرست باشد")
        for character in raw_characters:
            if not isinstance(character, dict):
                raise GameValidationError("هر شخصیت باید یک شیء باشد")
            character_id = _require_text(character.get("id"), "شناسه شخصیت")
            if character_id in self.characters:
                raise GameValidationError("شناسه شخصیت تکراری است: " + character_id)
            for media_field in ("portrait", "video", "voice", "model"):
                if character.get(media_field) is not None:
                    self._validate_asset_ref(character[media_field], media_field)
            for timing in ("video_start", "video_end"):
                if timing in character and _safe_number(character[timing], timing) < 0:
                    raise GameValidationError("{} شخصیت نمی‌تواند منفی باشد".format(timing))
            if character.get("video_end") and _safe_number(character["video_end"], "video_end") <= _safe_number(character.get("video_start", 0), "video_start"):
                raise GameValidationError("پایان کلیپ شخصیت باید بعد از شروع آن باشد")
            if "ai" in character and not isinstance(character["ai"], dict):
                raise GameValidationError("تنظیمات AI شخصیت باید یک شیء باشد")
            ai = character.get("ai", {})
            if "api_key" in ai or "token" in ai:
                raise GameValidationError("کلید محرمانهٔ API را داخل فایل بازی ذخیره نکن؛ بازیکن هنگام اجرا آن را وارد کند")
            api_base = ai.get("api_base")
            if api_base:
                parsed_api = urlsplit(str(api_base))
                if parsed_api.scheme not in ("http", "https") or not parsed_api.netloc:
                    raise GameValidationError("نشانی API شخصیت باید HTTP یا HTTPS معتبر باشد")
            rules = ai.get("rules", [])
            if not isinstance(rules, list):
                raise GameValidationError("قواعد پاسخ AI باید فهرست باشند")
            for rule in rules:
                if not isinstance(rule, dict) or not str(rule.get("trigger", "")).strip() or not str(rule.get("response", "")).strip():
                    raise GameValidationError("هر قاعده پاسخ باید عبارت و پاسخ غیرخالی داشته باشد")
            expressions = character.get("expressions", {})
            if not isinstance(expressions, dict):
                raise GameValidationError("expressions شخصیت باید شیء باشد")
            for expression, media in expressions.items():
                self._validate_asset_ref(media, "expression:" + str(expression))
            self.characters[character_id] = copy.deepcopy(character)
        for scene in self.scenes.values():
            for line in scene.get("dialogue", []):
                character_id = line.get("character")
                if character_id is not None and self.characters and character_id not in self.characters:
                    raise GameValidationError("شخصیت گفتگو تعریف نشده: " + str(character_id))
        world = self.data.get("world", {})
        if not isinstance(world, dict):
            raise GameValidationError("world باید یک شیء باشد")
        for dimension in ("width", "height"):
            if dimension in world:
                size = _safe_number(world[dimension], "ابعاد جهان")
                if size <= 0 or size > 16384:
                    raise GameValidationError("ابعاد جهان باید بین ۱ تا ۱۶۳۸۴ باشد")
        sprites = world.get("sprites", [])
        if not isinstance(sprites, list):
            raise GameValidationError("world.sprites باید فهرست باشد")
        sprite_ids = set()
        for sprite in sprites:
            if not isinstance(sprite, dict):
                raise GameValidationError("هر شیء نقشه باید یک شیء باشد")
            sprite_id = _require_text(sprite.get("id"), "شناسه شیء نقشه")
            if sprite_id in sprite_ids:
                raise GameValidationError("شناسه شیء نقشه تکراری است: " + sprite_id)
            sprite_ids.add(sprite_id)
            for field in ("image", "model"):
                if sprite.get(field) is not None:
                    self._validate_asset_ref(sprite[field], field)
            for field in ("x", "y", "width", "height", "speed", "fps", "frames",
                          "frame_width", "frame_height"):
                if field in sprite:
                    _safe_number(sprite[field], "مختصات/اندازه شیء نقشه")
            if sprite.get("width", 1) <= 0 or sprite.get("height", 1) <= 0:
                raise GameValidationError("اندازه شیء نقشه باید مثبت باشد")
        for field in ("background", "tileset"):
            if world.get(field) is not None:
                self._validate_asset_ref(world[field], field)
        if isinstance(world.get("player"), dict):
            for field in ("image", "model"):
                if world["player"].get(field) is not None:
                    self._validate_asset_ref(world["player"][field], "world player " + field)
            for field in ("x", "y", "width", "height", "speed", "fps", "frames",
                          "frame_width", "frame_height"):
                if field in world["player"]:
                    _safe_number(world["player"][field], "تنظیم بازیکن جهان")
        ui = self.data.get("ui", {})
        if not isinstance(ui, dict):
            raise GameValidationError("ui باید یک شیء باشد")
        elements = ui.get("elements", [])
        if not isinstance(elements, list):
            raise GameValidationError("ui.elements باید فهرست باشد")
        for element in elements:
            if not isinstance(element, dict) or element.get("type") not in ("text", "button", "name_input", "location"):
                raise GameValidationError("عنصر رابط کاربری MONN نامعتبر است")
        for field in ("menu_background", "button_sound", "background_music"):
            if ui.get(field) is not None:
                self._validate_asset_ref(ui[field], field)
        self.quests = {}
        raw_quests = self.data.get("quests", [])
        if not isinstance(raw_quests, list):
            raise GameValidationError("quests باید فهرست باشد")
        for quest in raw_quests:
            if not isinstance(quest, dict):
                raise GameValidationError("هر مأموریت باید یک شیء باشد")
            qid = _require_text(quest.get("id"), "شناسه مأموریت")
            if qid in self.quests:
                raise GameValidationError("شناسه مأموریت تکراری است: " + qid)
            self.quests[qid] = copy.deepcopy(quest)
        for scene in self.scenes.values():
            for choice in scene.get("choices", []):
                for effect in choice.get("effects", []):
                    if effect.get("type") == "quest":
                        quest_id = effect.get("name", effect.get("id"))
                        if quest_id not in self.quests:
                            raise GameValidationError("مأموریت تعریف نشده: " + str(quest_id))
        canonical = json.dumps(self.data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_asset_ref(value, label):
        value = _require_text(value, label)
        parsed = urlsplit(value)
        data_asset = value.startswith((
            "data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,",
            "data:image/gif;base64,", "data:image/svg+xml;base64,", "data:audio/mpeg;base64,",
            "data:audio/ogg;base64,", "data:audio/wav;base64,", "data:audio/mp4;base64,",
            "data:video/mp4;base64,", "data:video/webm;base64,", "data:video/ogg;base64,",
            "data:model/gltf-binary;base64,", "data:model/gltf+json;base64,",
            "data:application/octet-stream;base64,"
        ))
        if (parsed.scheme not in ("", "http", "https") and not data_asset) or value.startswith("//"):
            raise GameValidationError("دارایی باید مسیر نسبی، HTTP(S) یا دادهٔ تصویری، صوتی، ویدیویی یا مدل مجاز باشد")

    @staticmethod
    def _validate_conditions(conditions):
        for condition in conditions:
            if not isinstance(condition, dict):
                raise GameValidationError("هر شرط انتخاب باید یک شیء باشد")
            kind = condition.get("type", "stat")
            if kind not in ("stat", "flag", "item", "health", "quest"):
                raise GameValidationError("نوع شرط ناشناخته: " + str(kind))
            if condition.get("op", "==") not in COMPARATORS:
                raise GameValidationError("عملگر شرط نامعتبر است")
            if kind in ("stat", "health"):
                _safe_number(condition.get("value"), "مقدار شرط")
            if kind in ("stat", "flag", "item", "quest"):
                _require_text(condition.get("name", condition.get("id")), "نام شرط")

    @staticmethod
    def _validate_effect(effect):
        if not isinstance(effect, dict):
            raise GameValidationError("هر اثر انتخاب باید یک شیء باشد")
        kind = effect.get("type")
        if kind not in ("stat", "health", "item", "flag", "quest", "journal"):
            raise GameValidationError("نوع اثر ناشناخته: " + str(kind))
        if kind in ("stat", "health"):
            if effect.get("op", "add") not in ("add", "set", "subtract"):
                raise GameValidationError("عملیات مقدار نامعتبر است")
            _safe_number(effect.get("value", 0), "مقدار اثر")
            if kind == "stat":
                _require_text(effect.get("name"), "نام ویژگی")
        elif kind in ("item", "flag", "quest"):
            _require_text(effect.get("name", effect.get("id")), "نام اثر")
            if kind == "item":
                action = effect.get("action", "add")
                if action not in ("add", "remove", "set"):
                    raise GameValidationError("عملیات آیتم نامعتبر است")
                count = effect.get("count", 1)
                if isinstance(count, bool) or not isinstance(count, int) or count < (0 if action == "set" else 1) or count > MAX_ITEMS:
                    raise GameValidationError("تعداد آیتم نامعتبر است")
            if kind == "quest" and effect.get("action") not in ("start", "complete", "fail"):
                raise GameValidationError("عملیات مأموریت نامعتبر است")
            if kind == "flag" and not isinstance(effect.get("value", True), (bool, int, float, str)):
                raise GameValidationError("مقدار پرچم نامعتبر است")
        elif kind == "journal":
            _require_text(effect.get("text"), "متن دفترچه")


class GameEngine:
    """Deterministic narrative engine with inventory, quests and save files."""

    def __init__(self, project):
        self.project = project if isinstance(project, GameProject) else GameProject(project)
        self.reset()

    def reset(self):
        initial = self.project.player
        health = _safe_number(initial.get("health", 100), "جان اولیه")
        max_health = _safe_number(initial.get("max_health", max(health, 100)), "حداکثر جان")
        if health < 0 or max_health < 1 or health > max_health or max_health > MAX_HEALTH:
            raise GameValidationError("مقادیر جان اولیه نامعتبر هستند")
        stats = initial.get("stats", {})
        if not isinstance(stats, dict):
            raise GameValidationError("stats باید یک شیء باشد")
        for key, value in stats.items():
            _require_text(str(key), "نام ویژگی")
            _safe_number(value, "مقدار ویژگی")
        inventory = initial.get("inventory", [])
        if not isinstance(inventory, list):
            raise GameValidationError("inventory اولیه باید فهرست باشد")
        self.state = {
            "current_scene": self.project.start_scene,
            "health": health,
            "max_health": max_health,
            "stats": copy.deepcopy(stats),
            "flags": {},
            "inventory": {},
            "quests": {},
            "journal": [],
            "visited": [],
            "ended": False,
            "turn": 0,
        }
        for item in inventory:
            if isinstance(item, str):
                self.add_item(item, 1)
            elif isinstance(item, dict):
                self.add_item(item.get("name"), item.get("count", 1))
            else:
                raise GameValidationError("قالب آیتم اولیه نامعتبر است")
        self._enter_scene(self.project.start_scene)
        return self.snapshot()

    @property
    def scene(self):
        return copy.deepcopy(self.project.scenes[self.state["current_scene"]])

    def snapshot(self):
        return copy.deepcopy(self.state)

    def _enter_scene(self, scene_id):
        self.state["current_scene"] = scene_id
        if scene_id not in self.state["visited"]:
            self.state["visited"].append(scene_id)
        self.state["turn"] += 1

    def _condition(self, condition):
        kind = condition.get("type", "stat")
        if kind == "stat":
            actual = self.state["stats"].get(condition.get("name", condition.get("id")), 0)
        elif kind == "health":
            actual = self.state["health"]
        elif kind == "flag":
            actual = self.state["flags"].get(condition.get("name", condition.get("id")), False)
        elif kind == "item":
            actual = self.state["inventory"].get(condition.get("name", condition.get("id")), 0)
        else:
            actual = self.state["quests"].get(condition.get("name", condition.get("id")), "inactive")
        expected = condition.get("value", True)
        op = condition.get("op", "==")
        try:
            return COMPARATORS[op](actual, expected)
        except TypeError:
            return COMPARATORS[op](str(actual), str(expected))

    def available_choices(self):
        if self.state["ended"]:
            return []
        result = []
        for index, choice in enumerate(self.scene.get("choices", [])):
            if all(self._condition(c) for c in choice.get("conditions", [])):
                item = copy.deepcopy(choice)
                item["_index"] = index
                result.append(item)
        return result

    def add_item(self, name, count=1):
        name = _require_text(name, "نام آیتم")
        count = _safe_number(count, "تعداد آیتم")
        if count < 1 or count != int(count):
            raise GameStateError("تعداد آیتم باید عدد صحیح مثبت باشد")
        current = self.state["inventory"].get(name, 0)
        if current + count > MAX_ITEMS:
            raise GameStateError("تعداد آیتم از سقف مجاز بیشتر است")
        self.state["inventory"][name] = current + int(count)

    def _apply_effect(self, effect):
        kind = effect["type"]
        if kind == "stat":
            name = effect["name"]
            old = self.state["stats"].get(name, 0)
            value = effect.get("value", 0)
            op = effect.get("op", "add")
            new = value if op == "set" else old + value if op == "add" else old - value
            self.state["stats"][name] = new
        elif kind == "health":
            value = effect.get("value", 0)
            op = effect.get("op", "add")
            new = value if op == "set" else self.state["health"] + value if op == "add" else self.state["health"] - value
            self.state["health"] = max(0, min(self.state["max_health"], new))
            if self.state["health"] == 0:
                self.state["ended"] = True
        elif kind == "item":
            name = effect.get("name", effect.get("id"))
            action = effect.get("action", "add")
            count = int(effect.get("count", 1))
            if count < (0 if action == "set" else 1) or count > MAX_ITEMS:
                raise GameStateError("تعداد آیتم نامعتبر است")
            if action == "add":
                self.add_item(name, count)
            elif action == "remove":
                owned = self.state["inventory"].get(name, 0)
                if owned < count:
                    raise GameStateError("آیتم کافی در کوله‌پشتی وجود ندارد: " + name)
                if owned == count:
                    self.state["inventory"].pop(name, None)
                else:
                    self.state["inventory"][name] = owned - count
            else:
                if count > MAX_ITEMS:
                    raise GameStateError("تعداد آیتم بیش از حد مجاز است")
                if count:
                    self.state["inventory"][name] = count
                else:
                    self.state["inventory"].pop(name, None)
        elif kind == "flag":
            self.state["flags"][effect.get("name", effect.get("id"))] = effect.get("value", True)
        elif kind == "quest":
            qid, action = effect.get("name", effect.get("id")), effect["action"]
            self.state["quests"][qid] = {"start": "active", "complete": "completed", "fail": "failed"}[action]
        elif kind == "journal":
            self.state["journal"].append(effect["text"])

    def choose(self, selection):
        if self.state["ended"]:
            raise GameStateError("این بازی پایان یافته است")
        choices = self.available_choices()
        selected = None
        if isinstance(selection, int):
            selected = next((c for c in choices if c["_index"] == selection), None)
        elif isinstance(selection, str):
            selected = next((c for c in choices if c.get("id") == selection or c["text"] == selection), None)
        if selected is None:
            raise GameStateError("این انتخاب در وضعیت فعلی در دسترس نیست")
        before = self.snapshot()
        try:
            for effect in selected.get("effects", []):
                self._apply_effect(effect)
            target = selected.get("target")
            if target is None:
                self.state["ended"] = True
            else:
                self._enter_scene(target)
            return self.snapshot()
        except Exception:
            self.state = before
            raise

    def save(self, path):
        payload = {
            "engine_version": ENGINE_VERSION,
            "project_fingerprint": self.project.fingerprint,
            "project_id": self.project.project_id,
            "state": self.state,
        }
        target = os.path.abspath(os.fspath(path))
        directory = os.path.dirname(target) or "."
        os.makedirs(directory, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".monn-save-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        return target

    def load(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError) as exc:
            raise GameStateError("خواندن فایل ذخیره ناموفق بود: {}".format(exc)) from exc
        if not isinstance(payload, dict):
            raise GameStateError("ساختار فایل ذخیره نامعتبر است")
        if payload.get("engine_version") != ENGINE_VERSION:
            raise GameStateError("نسخه فایل ذخیره با موتور فعلی سازگار نیست")
        if payload.get("project_fingerprint") != self.project.fingerprint:
            raise GameStateError("این فایل ذخیره متعلق به نسخه دیگری از بازی است")
        state = payload.get("state")
        self._validate_state(state)
        self.state = copy.deepcopy(state)
        return self.snapshot()

    def _validate_state(self, state):
        if not isinstance(state, dict):
            raise GameStateError("ساختار ذخیره خراب است")
        required = ("current_scene", "health", "max_health", "stats", "flags",
                    "inventory", "quests", "journal", "visited", "ended", "turn")
        if any(key not in state for key in required):
            raise GameStateError("فایل ذخیره ناقص است")
        if state["current_scene"] not in self.project.scenes:
            raise GameStateError("صحنه ذخیره‌شده در پروژه وجود ندارد")
        if not isinstance(state["stats"], dict) or not isinstance(state["flags"], dict):
            raise GameStateError("وضعیت ویژگی‌ها خراب است")
        for name, value in state["stats"].items():
            if not isinstance(name, str) or isinstance(value, bool) or not isinstance(value, (int, float)):
                raise GameStateError("ویژگی ذخیره‌شده نامعتبر است")
        if any(not isinstance(name, str) or not isinstance(value, (bool, int, float, str)) for name, value in state["flags"].items()):
            raise GameStateError("پرچم ذخیره‌شده نامعتبر است")
        if not isinstance(state["inventory"], dict) or not isinstance(state["quests"], dict):
            raise GameStateError("وضعیت کوله‌پشتی یا مأموریت‌ها خراب است")
        if not isinstance(state["journal"], list) or not isinstance(state["visited"], list):
            raise GameStateError("دفترچه یا فهرست صحنه‌ها خراب است")
        health, maximum = state["health"], state["max_health"]
        if isinstance(health, bool) or isinstance(maximum, bool) or not isinstance(health, (int, float)) or not isinstance(maximum, (int, float)) or not 0 <= health <= maximum <= MAX_HEALTH:
            raise GameStateError("مقدار جان در فایل ذخیره نامعتبر است")
        for name, count in state["inventory"].items():
            if not isinstance(name, str) or isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_ITEMS:
                raise GameStateError("آیتم ذخیره‌شده نامعتبر است")
        if not isinstance(state["ended"], bool) or isinstance(state["turn"], bool) or not isinstance(state["turn"], int) or state["turn"] < 1:
            raise GameStateError("وضعیت پایان یا شماره نوبت نامعتبر است")
        if any(scene_id not in self.project.scenes for scene_id in state["visited"]):
            raise GameStateError("فهرست صحنه‌های بازدیدشده نامعتبر است")
        if any(qid not in self.project.quests or status not in ("active", "completed", "failed") for qid, status in state["quests"].items()):
            raise GameStateError("وضعیت مأموریت ذخیره‌شده نامعتبر است")
        if any(not isinstance(entry, str) for entry in state["journal"]):
            raise GameStateError("یادداشت ذخیره‌شده نامعتبر است")


    # Persian method aliases for Persian-first game scripts and tooling.
    def وضعیت(self):
        return self.snapshot()

    @property
    def صحنه(self):
        return self.scene

    def انتخاب_های_در_دسترس(self):
        return self.available_choices()

    def انتخاب(self, selection):
        return self.choose(selection)

    def ذخیره(self, path):
        return self.save(path)

    def بارگذاری(self, path):
        return self.load(path)

    def شروع_دوباره(self):
        return self.reset()

    def افزودن_آیتم(self, name, count=1):
        return self.add_item(name, count)


def load_project(path):
    """Load a UTF-8 JSON or native .monn game project from disk."""
    from pathlib import Path
    file_path = Path(path)
    if file_path.suffix.lower() == ".monn":
        from .game_dsl import load_monn
        return load_monn(file_path)
    with open(file_path, "r", encoding="utf-8") as handle:
        return GameProject(json.load(handle))
