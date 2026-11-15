"""Native, readable MONN game language.

The parser also accepts the legacy v1 JSON payload block for backwards compatibility.
"""
import json
import re
from pathlib import Path

from .game import GameProject, GameValidationError


def _q(value):
    return json.dumps(value, ensure_ascii=False)


def _value(raw):
    raw = raw.strip()
    if not raw:
        return ""
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw


def _quoted_pair(raw):
    decoder = json.JSONDecoder()
    raw = raw.lstrip()
    first, end = decoder.raw_decode(raw)
    rest = raw[end:].lstrip()
    second, end2 = decoder.raw_decode(rest)
    return first, second, rest[end2:].strip()


def _extras(obj, known):
    extra = {k: v for k, v in obj.items() if k not in known}
    return "  جزئیات = {}\n".format(_q(extra)) if extra else ""


def _property(key, value):
    return "  {} = {}\n".format(key, _q(value))


def dumps_monn(project):
    """Serialize a complete project as readable native MONN declarations."""
    game = project if isinstance(project, GameProject) else GameProject(project)
    d = game.data
    meta = d.get("meta", {})
    lines = [
        "# MONN Game Language · نسخه ۲",
        "# فایل متنی بومی؛ ساختار پروژه با دستورهای MONN تعریف می‌شود.",
        "بازی {}".format(_q(meta.get("title", game.title))),
        "شناسه {}".format(_q(meta.get("id", game.project_id))),
        "شروع {}".format(_q(meta.get("start_scene", game.start_scene))),
    ]
    for key, value in meta.items():
        if key not in {"id", "title", "start_scene"}:
            lines.append("{} = {}".format({
                "ending_scene": "پایان", "author": "پدیدآورنده",
                "license": "مجوز", "menu_scene": "صحنه_منو"
            }.get(key, key), _q(value)))
    lines.append("")
    player = d.get("player", {})
    lines.append("بازیکن {")
    for key, value in player.items():
        if key in ("health", "max_health"):
            lines.append("  {} = {}".format("جان" if key == "health" else "حداکثر_جان", _q(value)))
        elif key == "stats":
            for name, amount in value.items():
                lines.append("  ویژگی {} = {}".format(_q(name), _q(amount)))
        elif key == "inventory":
            for item in value:
                if isinstance(item, str):
                    lines.append("  آیتم {} = 1".format(_q(item)))
                else:
                    lines.append("  آیتم {} = {}".format(_q(item.get("name", "")), _q(item.get("count", 1))))
    lines.append(_extras(player, {"health", "max_health", "stats", "inventory"}).rstrip())
    lines.extend(["}", ""])
    for character in d.get("characters", []):
        lines.append("شخصیت {} {{".format(_q(character["id"])))
        for key, value in character.items():
            mapped = {"name":"نام","portrait":"تصویر","video":"ویدیو","voice":"صدا",
                      "model":"مدل","video_start":"شروع_کلیپ","video_end":"پایان_کلیپ"}.get(key)
            if mapped:
                lines.append("  {} = {}".format(mapped, _q(value)))
        for name, media in character.get("expressions", {}).items():
            lines.append("  حالت {} = {}".format(_q(name), _q(media)))
        ai = character.get("ai")
        if ai:
            lines.append("  هوش_مصنوعی = {}".format(_q(bool(ai.get("enabled")))))
            for key, value in ai.items():
                mapped = {"system_prompt":"دستور","model":"مدل_هوش","api_base":"نشانی_API"}.get(key)
                if mapped:
                    lines.append("  {} = {}".format(mapped, _q(value)))
            for rule in ai.get("rules", []):
                lines.append("  قانون_پاسخ {} => {}".format(_q(rule.get("trigger", "")), _q(rule.get("response", ""))))
        lines.append(_extras(character, {"id","name","portrait","video","voice","model","video_start","video_end","expressions","ai"}).rstrip())
        lines.extend(["}", ""])
    for quest in d.get("quests", []):
        lines.append("مأموریت {} {}".format(_q(quest["id"]), _q(quest.get("title", quest["id"]))))
        extra = _extras(quest, {"id","title"})
        if extra:
            lines.append(extra.rstrip())
    if d.get("quests"):
        lines.append("")
    for scene in d.get("scenes", []):
        lines.append("صحنه {} {} {{".format(_q(scene["id"]), _q(scene.get("title", scene["id"]))))
        for key, mapped in (("text","روایت"),("image","تصویر"),("video","ویدیو"),
                            ("video_start","شروع_کلیپ"),("video_end","پایان_کلیپ"),
                            ("video_loop","تکرار_کلیپ"),("music","موسیقی"),
                            ("model","مدل"),("button_sound","صدای_دکمه"),
                            ("world_enabled","جهان_فعال")):
            if key in scene:
                lines.append("  {} = {}".format(mapped, _q(scene[key])))
        for line in scene.get("dialogue", []):
            lines.append("  دیالوگ {} {}".format(_q(line.get("character") or ""), _q(line.get("text", ""))))
            for key, mapped in (("expression","حالت"),("video","ویدیو"),("voice","صدا"),
                                ("portrait","تصویر"),("video_start","شروع_کلیپ"),("video_end","پایان_کلیپ")):
                if key in line:
                    lines.append("  {} = {}".format(mapped, _q(line[key])))
        for choice in scene.get("choices", []):
            lines.append("  انتخاب {} -> {} {{".format(_q(choice.get("text", "")), _q(choice.get("target") or "")))
            lines.append("    شناسه = {}".format(_q(choice.get("id"))))
            if choice.get("sound"):
                lines.append("    صدا = {}".format(_q(choice["sound"])))
            for c in choice.get("conditions", []):
                lines.append("    شرط {} {} {} {}".format(_q(c.get("type","stat")), _q(c.get("name", c.get("id", ""))), c.get("op","=="), _q(c.get("value", True))))
            for e in choice.get("effects", []):
                if e["type"] == "journal":
                    lines.append("    اثر دفترچه {}".format(_q(e.get("text",""))))
                elif e["type"] == "quest":
                    lines.append("    اثر مأموریت {} {}".format(_q(e.get("name",e.get("id",""))), e.get("action","start")))
                elif e["type"] == "item":
                    lines.append("    اثر آیتم {} {} {}".format(_q(e.get("name","")), e.get("action","add"), _q(e.get("count",1))))
                elif e["type"] == "flag":
                    lines.append("    اثر پرچم {} = {}".format(_q(e.get("name","")), _q(e.get("value",True))))
                else:
                    lines.append("    اثر {} {} {} {}".format(_q(e["type"]), _q(e.get("name","")), e.get("op","add"), _q(e.get("value",0))))
            lines.append("  }")
        lines.append(_extras(scene, {"id","title","text","image","video","video_start","video_end","video_loop","music","model","button_sound","world_enabled","dialogue","choices"}).rstrip())
        lines.extend(["}", ""])
    if d.get("world"):
        world = d["world"]
        lines.append("جهان {")
        for key, mapped in (("enabled","فعال"),("width","عرض"),("height","ارتفاع"),("background","پس‌زمینه"),("color","رنگ")):
            if key in world:
                lines.append("  {} = {}".format(mapped, _q(world[key])))
        player2d = world.get("player", {})
        if player2d:
            lines.append("  بازیکن_جهان {")
            for key, value in player2d.items():
                lines.append("    {} = {}".format(key, _q(value)))
            lines.append("  }")
        for sprite in world.get("sprites", []):
            lines.append("  شیء {} {{".format(_q(sprite["id"])))
            for key, value in sprite.items():
                if key != "id":
                    lines.append("    {} = {}".format(key, _q(value)))
            lines.append("  }")
        lines.append(_extras(world, {"enabled","width","height","background","color","player","sprites"}).rstrip())
        lines.extend(["}", ""])
    if d.get("ui"):
        ui = d["ui"]
        lines.append("رابط {")
        mapping = {"menu_enabled":"منو_فعال","menu_title":"عنوان_منو","start_label":"برچسب_شروع",
                   "settings_label":"برچسب_تنظیمات","menu_background":"پس‌زمینه_منو",
                   "background_music":"موسیقی_منو","button_sound":"صدای_دکمه",
                   "show_health":"نمایش_جان","show_inventory":"نمایش_کوله","show_quests":"نمایش_مأموریت"}
        for key, value in ui.items():
            if key in mapping:
                lines.append("  {} = {}".format(mapping[key], _q(value)))
        for element in ui.get("elements", []):
            lines.append("  عنصر_رابط = {}".format(_q(element)))
        lines.append(_extras(ui, set(mapping) | {"elements"}).rstrip())
        lines.extend(["}", ""])
    for asset in d.get("assets", []):
        lines.append("دارایی {} {} {{".format(_q(asset.get("name","asset")), _q(asset.get("kind","file"))))
        for key in ("data","author","source","license","notes"):
            if key in asset:
                lines.append("  {} = {}".format({"author":"پدیدآورنده","source":"منبع","license":"مجوز","notes":"یادداشت"}.get(key,key), _q(asset[key])))
        lines.append(_extras(asset, {"name","kind","data","author","source","license","notes"}).rstrip())
        lines.extend(["}", ""])
    root_extra = {k:v for k,v in d.items() if k not in {"meta","player","characters","quests","scenes","world","ui","assets"}}
    if root_extra:
        lines.append("داده_ریشه = {}".format(_q(root_extra)))
    return "\n".join(line for line in lines if line is not None).rstrip() + "\n"


def loads_monn(source):
    """Parse native MONN declarations, while retaining support for legacy v1 files."""
    if not isinstance(source, str):
        raise GameValidationError("محتوای MONN باید متن باشد")
    legacy = re.search(r'^پروژه\s*=\s*"""\s*\n(.*?)\n"""\s*$', source, re.M | re.S)
    if legacy:
        try:
            return GameProject(json.loads(legacy.group(1)))
        except json.JSONDecodeError as exc:
            raise GameValidationError("ساختار داده‌های پروژه MONN خراب است: {}".format(exc)) from exc

    data = {"meta": {}, "player": {}, "characters": [], "quests": [], "scenes": []}
    stack = []
    current_scene = None

    def ctx():
        return stack[-1] if stack else ("root", data)

    def set_prop(obj, key, value):
        obj[key] = value

    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "}":
            if stack:
                stack.pop()
            continue
        if line.startswith("بازی "):
            data["meta"]["title"] = _value(line[5:]); continue
        if line.startswith("شناسه ") and ctx()[0] == "root":
            data["meta"]["id"] = _value(line[6:]); continue
        if line.startswith("شروع ") and ctx()[0] == "root":
            data["meta"]["start_scene"] = _value(line[5:]); continue
        if line.startswith("مأموریت "):
            qid, title, rest = _quoted_pair(line[len("مأموریت "):])
            quest = {"id": qid, "title": title}
            data["quests"].append(quest)
            continue
        if line.startswith("شخصیت "):
            cid = _value(line[len("شخصیت "):].split("{",1)[0].strip())
            obj = {"id": cid, "expressions": {}, "ai": {"enabled": False, "rules": []}}
            data["characters"].append(obj); stack.append(("character", obj)); continue
        if line.startswith("صحنه "):
            sid, title, rest = _quoted_pair(line[len("صحنه "):].split("{",1)[0].strip())
            obj = {"id": sid, "title": title, "text": "", "choices": [], "dialogue": []}
            data["scenes"].append(obj); current_scene = obj; stack.append(("scene", obj)); continue
        if line.startswith("انتخاب "):
            prefix = line[len("انتخاب "):].split("{",1)[0].strip()
            match = re.match(r'(.+?)\s*->\s*(.+)$', prefix)
            if not match:
                raise GameValidationError("ساختار انتخاب MONN نامعتبر است: " + line)
            text_value, target = _value(match.group(1)), _value(match.group(2))
            obj = {"id": "choice_{}".format(len(ctx()[1].get("choices",[]))+1), "text": text_value,
                   "target": target or None, "conditions": [], "effects": []}
            ctx()[1]["choices"].append(obj); stack.append(("choice", obj)); continue
        if line == "بازیکن {" :
            obj = data["player"]; stack.append(("player", obj)); continue
        if line == "جهان {":
            obj = data.setdefault("world", {"enabled": False, "width": 800, "height": 450, "sprites": []})
            stack.append(("world", obj)); continue
        if line == "رابط {":
            obj = data.setdefault("ui", {"elements": []}); stack.append(("ui", obj)); continue
        if line.startswith("بازیکن_جهان {"):
            world = data.setdefault("world", {"enabled": False, "width":800,"height":450,"sprites":[]})
            obj = world.setdefault("player", {}); stack.append(("world_player", obj)); continue
        if line.startswith("شیء "):
            sid = _value(line[len("شیء "):].split("{",1)[0].strip())
            world = data.setdefault("world", {"enabled":False,"width":800,"height":450,"sprites":[]})
            obj = {"id": sid}; world.setdefault("sprites",[]).append(obj); stack.append(("sprite",obj)); continue
        if line.startswith("عنصر_رابط"):
            ui = data.setdefault("ui", {"elements":[]})
            element = _value(line.split("=",1)[1].strip())
            ui.setdefault("elements",[]).append(element); continue
        if line.startswith("دارایی "):
            name, kind, rest = _quoted_pair(line[len("دارایی "):].split("{",1)[0].strip())
            obj = {"name":name,"kind":kind}; data.setdefault("assets",[]).append(obj); stack.append(("asset",obj)); continue
        kind, obj = ctx()
        if line.startswith("دیالوگ ") and kind == "scene":
            character, text_value, rest = _quoted_pair(line[len("دیالوگ "):])
            obj.setdefault("dialogue",[]).append({"character":character or None,"text":text_value}); continue
        if line.startswith("حالت ") and kind == "character":
            name, value, rest = _quoted_pair(line[len("حالت "):].split("=",1)[0].strip() + " " + line.split("=",1)[1].strip())
            obj.setdefault("expressions",{})[name] = value; continue
        if line.startswith("قانون_پاسخ ") and kind == "character":
            match = re.match(r'قانون_پاسخ\s+(.+?)\s*=>\s*(.+)$', line)
            trigger, response = _value(match.group(1)), _value(match.group(2))
            obj.setdefault("ai",{}).setdefault("rules",[]).append({"trigger":trigger,"response":response}); continue
        if line.startswith("شرط ") and kind == "choice":
            match = re.match(r'شرط\s+(.+?)\s+(.+?)\s+(==|!=|>=|<=|>|<|=)\s+(.+)$', line)
            if not match: raise GameValidationError("شرط MONN نامعتبر است: " + line)
            typ, name, op, value = match.groups()
            obj["conditions"].append({"type":_value(typ),"name":_value(name),"op":op,"value":_value(value)}); continue
        if line.startswith("اثر ") and kind == "choice":
            rest = line[len("اثر "):]
            if rest.startswith("دفترچه "):
                obj["effects"].append({"type":"journal","text":_value(rest[len("دفترچه "):])}); continue
            match = re.match(r'(.+?)\s+(.+?)\s+(add|set|subtract|remove|start|complete|fail|\+)\s+(.+)$', rest)
            if match:
                typ, name, op, value = match.groups(); typ=_value(typ); name=_value(name); value=_value(value)
                if typ == "item": obj["effects"].append({"type":"item","name":name,"action":{"+" :"add"}.get(op,op),"count":int(value)})
                elif typ == "quest": obj["effects"].append({"type":"quest","name":name,"action":op})
                elif typ == "flag": obj["effects"].append({"type":"flag","name":name,"value":value})
                else: obj["effects"].append({"type":typ,"name":name,"op":{"+" :"add"}.get(op,op),"value":value})
                continue
            raise GameValidationError("اثر MONN نامعتبر است: " + line)
        if line.startswith("اثر مأموریت ") and kind == "choice":
            name, action, rest = _quoted_pair(line[len("اثر مأموریت "):] + ' ""')
            obj["effects"].append({"type":"quest","name":name,"action":action}); continue
        if line.startswith("اثر آیتم ") and kind == "choice":
            match = re.match(r'اثر آیتم\s+(.+?)\s+(add|set|remove)\s+(.+)$', line)
            name, action, count = match.groups()
            obj["effects"].append({"type":"item","name":_value(name),"action":action,"count":int(_value(count))}); continue
        if line.startswith("اثر پرچم ") and kind == "choice":
            match = re.match(r'اثر پرچم\s+(.+?)\s*=\s*(.+)$', line)
            obj["effects"].append({"type":"flag","name":_value(match.group(1)),"value":_value(match.group(2))}); continue
        if "=" in line:
            key, raw = [part.strip() for part in line.split("=",1)]
            value = _value(raw)
            if key == "داده_ریشه": data.update(value); continue
            if key == "جزئیات": obj.update(value); continue
            if kind == "root":
                meta_map={"پدیدآورنده":"author","مجوز":"license","پایان":"ending_scene","صحنه_منو":"menu_scene"}
                data["meta"][meta_map.get(key,key)] = value
            elif kind == "player":
                if key == "جان": obj["health"]=value
                elif key == "حداکثر_جان": obj["max_health"]=value
                else: obj[key]=value
            elif kind == "character":
                mapping={"نام":"name","تصویر":"portrait","ویدیو":"video","صدا":"voice","مدل":"model",
                         "شروع_کلیپ":"video_start","پایان_کلیپ":"video_end","دستور":"system_prompt",
                         "مدل_هوش":"model","نشانی_API":"api_base","هوش_مصنوعی":"enabled"}
                if key in ("ویژگی","حالت"): obj.setdefault("expressions",{})[value[0]]=value[1]
                elif key in ("دستور","مدل_هوش","نشانی_API","هوش_مصنوعی"):
                    ai=obj.setdefault("ai",{"enabled":False,"rules":[]});ai[mapping[key]]=value
                else: obj[mapping.get(key,key)]=value
            elif kind == "scene":
                mapping={"روایت":"text","تصویر":"image","ویدیو":"video","شروع_کلیپ":"video_start",
                         "پایان_کلیپ":"video_end","تکرار_کلیپ":"video_loop","موسیقی":"music",
                         "مدل":"model","صدای_دکمه":"button_sound","جهان_فعال":"world_enabled"}
                obj[mapping.get(key,key)]=value
            elif kind == "choice":
                if key == "شناسه": obj["id"]=value
                elif key == "صدا": obj["sound"]=value
            elif kind in ("world","world_player","sprite"):
                mapping={"فعال":"enabled","عرض":"width","ارتفاع":"height","پس‌زمینه":"background","رنگ":"color","برخورد":"solid"}
                obj[mapping.get(key,key)]=value
            elif kind == "ui":
                mapping={"منو_فعال":"menu_enabled","عنوان_منو":"menu_title","برچسب_شروع":"start_label",
                         "برچسب_تنظیمات":"settings_label","پس‌زمینه_منو":"menu_background","موسیقی_منو":"background_music",
                         "صدای_دکمه":"button_sound","نمایش_جان":"show_health","نمایش_کوله":"show_inventory",
                         "نمایش_مأموریت":"show_quests"}
                obj[mapping.get(key,key)]=value
            elif kind == "asset":
                mapping={"پدیدآورنده":"author","منبع":"source","مجوز":"license","یادداشت":"notes"}
                obj[mapping.get(key,key)]=value
            continue
        if kind == "player" and line.startswith("ویژگی "):
            name, value, rest = _quoted_pair(line[len("ویژگی "):].split("=",1)[0].strip()+" "+line.split("=",1)[1].strip())
            obj.setdefault("stats",{})[name]=value; continue
        if kind == "player" and line.startswith("آیتم "):
            name, value, rest = _quoted_pair(line[len("آیتم "):].split("=",1)[0].strip()+" "+line.split("=",1)[1].strip())
            obj.setdefault("inventory",[]).append({"name":name,"count":int(value)}); continue
        if kind == "asset" and line.startswith("داده "):
            obj["data"]=_value(line[len("داده "):]); continue
    if not data.get("meta",{}).get("start_scene") and data.get("scenes"):
        data["meta"]["start_scene"] = data["scenes"][0]["id"]
    if not data.get("meta",{}).get("title"):
        data["meta"]["title"] = "بازی MONN"
    return GameProject(data)


def load_monn(path):
    return loads_monn(Path(path).read_text(encoding="utf-8"))
