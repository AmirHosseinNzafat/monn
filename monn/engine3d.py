"""Optional Monn 3D action runtime powered by Panda3D.

The module imports without Panda3D installed; the dependency is required only
when a 3D project is launched.
"""
import argparse
import base64
import hashlib
import math
import tempfile
from pathlib import Path


class Monn3DError(Exception):
    pass


def _vector(value, label, positive=False):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise Monn3DError("{} باید آرایه سه‌عددی باشد.".format(label))
    result = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            raise Monn3DError("{} شامل مقدار نامعتبر است.".format(label))
        if positive and item <= 0:
            raise Monn3DError("{} باید مقادیر مثبت داشته باشد.".format(label))
        result.append(float(item))
    return result


def validate_world3d(project):
    if not isinstance(project, dict):
        raise Monn3DError("پروژه سه‌بعدی باید یک شیء باشد.")
    world = project.get("world3d")
    if not isinstance(world, dict) or not world.get("enabled", True):
        raise Monn3DError("بخش world3d در پروژه تعریف نشده یا غیرفعال است.")
    objects = world.get("objects", [])
    if not isinstance(objects, list) or len(objects) > 1500:
        raise Monn3DError("فهرست اشیای سه‌بعدی معتبر نیست یا بیش از ۱۵۰۰ شیء دارد.")
    seen = set()
    normalized = []
    allowed_shapes = ("box", "sphere", "model")
    for item in objects:
        if not isinstance(item, dict):
            raise Monn3DError("هر شیء سه‌بعدی باید یک شیء تنظیمات باشد.")
        object_id = item.get("id")
        if not isinstance(object_id, str) or not object_id.strip() or object_id in seen:
            raise Monn3DError("شناسه اشیای سه‌بعدی باید غیرخالی و یکتا باشد.")
        seen.add(object_id)
        shape = item.get("shape", "box")
        if shape not in allowed_shapes:
            raise Monn3DError("شکل شیء فقط می‌تواند box، sphere یا model باشد.")
        entry = dict(item)
        entry["id"] = object_id
        entry["shape"] = shape
        entry["position"] = _vector(item.get("position", [0, 0, 0]), "position")
        entry["scale"] = _vector(item.get("scale", [1, 1, 1]), "scale", positive=True)
        entry["rotation"] = _vector(item.get("rotation", [0, 0, 0]), "rotation")
        entry["solid"] = bool(item.get("solid", shape != "model"))
        entry["role"] = item.get("role", "decoration")
        if entry["role"] not in ("decoration", "obstacle", "enemy", "target"):
            raise Monn3DError("نقش شیء سه‌بعدی نامعتبر است.")
        color = item.get("color", "#6b91b8")
        if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
            raise Monn3DError("رنگ باید به صورت #RRGGBB باشد.")
        try:
            int(color[1:], 16)
        except ValueError as exc:
            raise Monn3DError("کد رنگ معتبر نیست.") from exc
        entry["color"] = color
        if entry["role"] == "enemy":
            for field, default, low, high in (("health", 3, 1, 100000), ("speed", 2.2, 0.0, 20.0), ("damage", 8, 0, 10000)):
                value = item.get(field, default)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                    raise Monn3DError("مقدار {} برای دشمن معتبر نیست.".format(field))
                entry[field] = int(value) if field in ("health", "damage") else float(value)
        if shape == "model":
            model = item.get("model")
            if not isinstance(model, str) or not model.strip() or "://" in model or ".." in Path(model).parts:
                raise Monn3DError("مدل باید مسیر فایل محلی و بدون پیمایش پوشه باشد.")
            model_data = item.get("model_data")
            asset_index = item.get("model_asset")
            if model_data is None and asset_index is not None:
                assets = project.get("assets", [])
                if isinstance(asset_index, bool) or not isinstance(asset_index, int) or not isinstance(assets, list) or not 0 <= asset_index < len(assets) or not isinstance(assets[asset_index], dict) or assets[asset_index].get("kind") != "model":
                    raise Monn3DError("ارجاع دارایی مدل در پروژه معتبر نیست.")
                model_data = assets[asset_index].get("data")
            if model_data is not None:
                if not isinstance(model_data, str) or len(model_data) > 48 * 1024 * 1024 or not model_data.startswith(("data:model/gltf-binary;base64,", "data:model/gltf+json;base64,", "data:application/octet-stream;base64,", "data:application/json;base64,")):
                    raise Monn3DError("دادهٔ مدل جاسازی‌شده معتبر یا کوچک‌تر از ۳۲ مگابایت نیست.")
                try:
                    payload = base64.b64decode(model_data.split(",", 1)[1], validate=True)
                except (ValueError, base64.binascii.Error) as exc:
                    raise Monn3DError("کدگذاری مدل جاسازی‌شده معتبر نیست.") from exc
                if len(payload) > 32 * 1024 * 1024:
                    raise Monn3DError("حجم مدل جاسازی‌شده از ۳۲ مگابایت بیشتر است.")
                entry["model_data"] = model_data
        normalized.append(entry)
    player = world.get("player", {})
    if not isinstance(player, dict):
        raise Monn3DError("تنظیم بازیکن سه‌بعدی معتبر نیست.")
    camera_mode = player.get("camera_mode", "first_person")
    if camera_mode not in ("first_person", "third_person"):
        raise Monn3DError("حالت دوربین باید first_person یا third_person باشد.")
    camera_distance = player.get("camera_distance", 7.0)
    if isinstance(camera_distance, bool) or not isinstance(camera_distance, (int, float)) or not math.isfinite(camera_distance) or not 2 <= camera_distance <= 20:
        raise Monn3DError("فاصله دوربین سوم‌شخص باید بین ۲ تا ۲۰ باشد.")
    lighting = world.get("lighting", {})
    if not isinstance(lighting, dict):
        raise Monn3DError("تنظیم نورپردازی معتبر نیست.")
    ambient_intensity = lighting.get("ambient", 0.34)
    directional_intensity = lighting.get("directional", 0.66)
    if isinstance(ambient_intensity, bool) or not isinstance(ambient_intensity, (int, float)) or not math.isfinite(ambient_intensity) or not 0 <= ambient_intensity <= 2:
        raise Monn3DError("شدت نور محیطی باید بین صفر تا ۲ باشد.")
    if isinstance(directional_intensity, bool) or not isinstance(directional_intensity, (int, float)) or not math.isfinite(directional_intensity) or not 0 <= directional_intensity <= 3:
        raise Monn3DError("شدت نور جهت‌دار باید بین صفر تا ۳ باشد.")
    light_direction = _vector(lighting.get("direction", [-0.4, 0.7, 0.8]), "lighting.direction")
    if sum(value * value for value in light_direction) < 0.0001:
        raise Monn3DError("جهت نور نمی‌تواند بردار صفر باشد.")
    weapon = world.get("weapon", {})
    if not isinstance(weapon, dict):
        raise Monn3DError("تنظیم سلاح معتبر نیست.")
    weapon_config = {}
    for field, default, low, high in (("damage", 1, 1, 1000), ("fire_rate", 4.0, 0.2, 20.0), ("projectile_speed", 28.0, 2.0, 200.0), ("range", 60.0, 5.0, 500.0)):
        value = weapon.get(field, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise Monn3DError("تنظیم سلاح {} نامعتبر است.".format(field))
        weapon_config[field] = float(value) if field != "damage" else int(value)
    return {
        "title": str(world.get("title") or project.get("meta", {}).get("title") or "Monn 3D"),
        "player": {
            "position": _vector(player.get("position", [0, -8, 1.7]), "player.position"),
            "speed": max(0.5, min(float(player.get("speed", 8)), 40)),
            "sensitivity": max(0.02, min(float(player.get("sensitivity", 0.12)), 1.0)),
            "camera_mode": camera_mode,
            "camera_distance": float(camera_distance),
        },
        "weapon": weapon_config,
        "lighting": {"ambient": float(ambient_intensity), "directional": float(directional_intensity), "direction": light_direction},
        "objects": normalized,
        "gravity": max(0.0, min(float(world.get("gravity", 9.81)), 100.0)),
    }


def run_project(project, project_path=None):
    try:
        from direct.showbase.ShowBase import ShowBase
        from direct.gui.OnscreenText import OnscreenText
        from panda3d.core import (
            AmbientLight, DirectionalLight, Vec3, Vec4, WindowProperties,
            ClockObject, TransparencyAttrib,
        )
    except ImportError as exc:
        raise Monn3DError(
            'موتور سه‌بعدی نصب نیست. اجرا کن: py -m pip install -e ".[3d-runtime]"'
        ) from exc

    config = validate_world3d(project)
    root = Path(project_path).resolve().parent if project_path else Path.cwd()

    class MonnAction3D(ShowBase):
        def __init__(self):
            ShowBase.__init__(self)
            self.disableMouse()
            self.setWindowTitle(config["title"] + " — Monn 3D")
            self.setBackgroundColor(0.035, 0.055, 0.09, 1)
            self.accept("escape", self.userExit)
            self.keys = {key: False for key in ("w", "a", "s", "d", "space")}
            for key in self.keys:
                self.accept(key, self.set_key, [key, True])
                self.accept(key + "-up", self.set_key, [key, False])
            self.accept("mouse1", self.fire)
            self.heading = 0.0
            self.pitch = 0.0
            self.speed = config["player"]["speed"]
            self.sensitivity = config["player"]["sensitivity"]
            self.camera_mode = config["player"]["camera_mode"]
            self.camera_distance = config["player"]["camera_distance"]
            self.weapon = config["weapon"]
            self.lighting = config["lighting"]
            self.fire_cooldown = 0.0
            self.player_position = Vec3(*config["player"]["position"])
            self.player_visual = None
            if self.camera_mode == "third_person":
                self.player_visual = self.loader.loadModel("models/misc/sphere")
                self.player_visual.reparentTo(self.render)
                self.player_visual.setScale(0.45, 0.35, 0.85)
                self.player_visual.setColor(0.18, 0.78, 0.88, 1)
            self.gravity = config["gravity"]
            self.vertical_velocity = 0.0
            self.model_tempdir = tempfile.TemporaryDirectory(prefix="monn-3d-models-")
            self.obstacles = []
            self.enemies = []
            self.projectiles = []
            self.health = 100
            self.score = 0
            self._lighting()
            self._floor()
            self._objects()
            self.camera.setPos(*config["player"]["position"])
            self._update_camera()
            self._capture_mouse()
            self.hud = OnscreenText(
                text="WASD حرکت  |  ماوس نگاه  |  کلیک چپ شلیک  |  ESC خروج",
                pos=(-1.28, 0.92), scale=0.045, align=0,
                fg=(0.72, 0.91, 1, 1), mayChange=True,
            )
            self.stats = OnscreenText(
                text="جان: 100   امتیاز: 0", pos=(1.25, 0.92), scale=0.05,
                align=2, fg=(0.55, 1, 0.78, 1), mayChange=True,
            )
            self.crosshair = OnscreenText(
                text="+", pos=(0, -0.02), scale=0.07, fg=(1, 1, 1, 0.85),
            )
            self.taskMgr.add(self.update, "monn-3d-update")

        def set_key(self, key, value):
            self.keys[key] = value

        def _lighting(self):
            ambient = AmbientLight("monn-ambient")
            ambient_level = min(1.0, self.lighting["ambient"])
            ambient.setColor(Vec4(ambient_level * 0.95, ambient_level, min(1.0, ambient_level * 1.15), 1))
            self.render.setLight(self.render.attachNewNode(ambient))
            sun = DirectionalLight("monn-sun")
            sun_level = min(1.0, self.lighting["directional"])
            sun.setColor(Vec4(sun_level, sun_level * 0.97, sun_level * 0.86, 1))
            sun_np = self.render.attachNewNode(sun)
            sun_np.setHpr(-35, -55, 0)
            self.render.setLight(sun_np)

        def _floor(self):
            floor = self.loader.loadModel("models/box")
            floor.reparentTo(self.render)
            floor.setScale(35, 35, 0.25)
            floor.setPos(0, 0, -0.35)
            floor.setColor(0.16, 0.22, 0.29, 1)
            self.obstacles.append({"center": (0, 0, -0.35), "half": (35, 35, 0.25)})

        def _objects(self):
            for item in config["objects"]:
                if item["shape"] == "model":
                    if item.get("model_data"):
                        header, encoded = item["model_data"].split(",", 1)
                        suffix = ".gltf" if "gltf+json" in header or "application/json" in header else ".glb"
                        model_path = Path(self.model_tempdir.name) / (hashlib.sha256(item["id"].encode("utf-8")).hexdigest() + suffix)
                        model_path.write_bytes(base64.b64decode(encoded, validate=True))
                    else:
                        model_path = (root / item["model"]).resolve()
                        if root not in model_path.parents and model_path != root:
                            raise Monn3DError("مسیر مدل از پوشه پروژه خارج می‌شود.")
                        if not model_path.is_file():
                            raise Monn3DError("فایل مدل پیدا نشد: " + str(model_path))
                    node = self.loader.loadModel(str(model_path))
                    if node.isEmpty():
                        raise Monn3DError("مدل سه‌بعدی قابل بارگذاری نیست: " + item["model"])
                else:
                    model_name = "models/misc/sphere" if item["shape"] == "sphere" else "models/box"
                    node = self.loader.loadModel(model_name)
                node.reparentTo(self.render)
                node.setPos(*item["position"])
                node.setScale(*item["scale"])
                node.setHpr(*item["rotation"])
                rgb = tuple(int(item["color"][i:i + 2], 16) / 255.0 for i in (1, 3, 5))
                node.setColor(rgb[0], rgb[1], rgb[2], 1)
                node.setTag("monn-id", item["id"])
                if item["solid"]:
                    center = item["position"]
                    half = [value * 0.5 for value in item["scale"]]
                    self.obstacles.append({"center": tuple(center), "half": tuple(half)})
                if item["role"] in ("enemy", "target"):
                    self.enemies.append({"node": node, "health": int(item.get("health", 3)), "alive": True, "role": item["role"], "speed": float(item.get("speed", 2.2)), "damage": int(item.get("damage", 8)), "attack_timer": 0.0})

        def _update_camera(self):
            if self.camera_mode == "first_person":
                self.camera.setPos(self.player_position)
            else:
                heading = math.radians(self.heading)
                pitch = math.radians(self.pitch)
                horizontal = self.camera_distance * math.cos(pitch)
                offset = Vec3(math.sin(heading) * horizontal,
                              -math.cos(heading) * horizontal,
                              self.camera_distance * math.sin(pitch) + 1.5)
                self.camera.setPos(self.player_position + offset)
                self.camera.lookAt(self.player_position + Vec3(0, 0, 0.65))
                if self.player_visual:
                    self.player_visual.setPos(self.player_position - Vec3(0, 0, 0.8))
                    self.player_visual.setH(self.heading)

        def _capture_mouse(self):
            if not self.win:
                return
            props = WindowProperties()
            props.setCursorHidden(True)
            self.win.requestProperties(props)
            self.center = (self.win.getXSize() // 2, self.win.getYSize() // 2)
            self.win.movePointer(0, self.center[0], self.center[1])

        def _look(self):
            if not self.win:
                return
            pointer = self.win.getPointer(0)
            dx = pointer.getX() - self.center[0]
            dy = pointer.getY() - self.center[1]
            self.heading -= dx * self.sensitivity
            self.pitch = max(-78, min(78, self.pitch - dy * self.sensitivity))
            if self.camera_mode == "first_person":
                self.camera.setHpr(self.heading, self.pitch, 0)
            self.win.movePointer(0, self.center[0], self.center[1])

        def _blocked(self, pos):
            radius, height = 0.35, 1.7
            px, py, pz = pos
            for obstacle in self.obstacles:
                cx, cy, cz = obstacle["center"]
                hx, hy, hz = obstacle["half"]
                if abs(px - cx) < hx + radius and abs(py - cy) < hy + radius and abs((pz - height / 2) - cz) < hz + height / 2:
                    if cz + hz > 0:
                        return True
            return False

        def fire(self):
            if self.fire_cooldown > 0:
                return
            self.fire_cooldown = 1.0 / self.weapon["fire_rate"]
            direction = self.camera.getQuat(self.render).getForward()
            origin = self.camera.getPos(self.render) + direction * 0.8
            bullet = self.loader.loadModel("models/misc/sphere")
            bullet.reparentTo(self.render)
            bullet.setScale(0.12)
            bullet.setPos(origin)
            bullet.setColor(1, 0.78, 0.18, 1)
            self.projectiles.append({"node": bullet, "direction": direction, "life": self.weapon["range"] / self.weapon["projectile_speed"]})

        def update(self, task):
            dt = min(ClockObject.getGlobalClock().getDt(), 0.05)
            self._look()
            quat = self.camera.getQuat(self.render)
            if self.camera_mode == "third_person":
                heading = math.radians(self.heading)
                forward = Vec3(math.sin(heading), math.cos(heading), 0)
                right = Vec3(math.cos(heading), -math.sin(heading), 0)
            else:
                forward = quat.getForward()
                right = quat.getRight()
                forward.setZ(0)
                right.setZ(0)
            if forward.lengthSquared() > 0:
                forward.normalize()
            if right.lengthSquared() > 0:
                right.normalize()
            movement = Vec3(0, 0, 0)
            if self.keys["w"]: movement += forward
            if self.keys["s"]: movement -= forward
            if self.keys["d"]: movement += right
            if self.keys["a"]: movement -= right
            current = self.player_position
            if movement.lengthSquared() > 0:
                movement.normalize()
            candidate = current + movement * self.speed * dt
            if self.keys["space"] and current.getZ() <= 1.701:
                self.vertical_velocity = 5.5
            self.vertical_velocity -= self.gravity * dt
            candidate.setZ(max(1.7, current.getZ() + self.vertical_velocity * dt))
            if candidate.getZ() <= 1.7:
                self.vertical_velocity = 0.0
            if not self._blocked(candidate):
                self.player_position = candidate
            self._update_camera()
            self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
            player_position = self.player_position
            for enemy in self.enemies:
                if not enemy["alive"] or enemy["role"] != "enemy":
                    continue
                enemy_position = enemy["node"].getPos()
                toward_player = player_position - enemy_position
                toward_player.setZ(0)
                distance = toward_player.length()
                if distance > 1.45:
                    toward_player.normalize()
                    enemy["node"].setPos(enemy_position + toward_player * enemy["speed"] * dt)
                    enemy["node"].lookAt(player_position)
                else:
                    enemy["attack_timer"] -= dt
                    if enemy["attack_timer"] <= 0:
                        self.health = max(0, self.health - enemy["damage"])
                        enemy["attack_timer"] = 1.25
            for shot in list(self.projectiles):
                shot["life"] -= dt
                shot["node"].setPos(shot["node"].getPos() + shot["direction"] * self.weapon["projectile_speed"] * dt)
                hit = False
                pos = shot["node"].getPos()
                for enemy in self.enemies:
                    if not enemy["alive"]:
                        continue
                    if (enemy["node"].getPos() - pos).length() < max(enemy["node"].getScale()) * 0.8 + 0.2:
                        enemy["health"] -= self.weapon["damage"]
                        hit = True
                        if enemy["health"] <= 0:
                            enemy["alive"] = False
                            enemy["node"].hide()
                            self.score += 100
                        break
                if hit or shot["life"] <= 0:
                    shot["node"].removeNode()
                    self.projectiles.remove(shot)
            self.stats.setText("جان: {}   امتیاز: {}".format(self.health, self.score))
            return task.cont

    app = MonnAction3D()
    try:
        app.run()
    finally:
        app.model_tempdir.cleanup()


def main():
    parser = argparse.ArgumentParser(description="اجرای نمونه بازی سه‌بعدی و اکشن Monn")
    parser.add_argument("project", help="مسیر فایل پروژه .monn یا JSON")
    args = parser.parse_args()
    from .game import load_project
    try:
        project = load_project(args.project)
        run_project(project.data, args.project)
    except (OSError, ValueError, Monn3DError) as exc:
        parser.exit(1, "Monn 3D: {}\n".format(exc))


if __name__ == "__main__":
    main()
