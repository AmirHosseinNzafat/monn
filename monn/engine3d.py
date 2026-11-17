"""Optional Monn 3D action runtime powered by Panda3D.

The module imports without Panda3D installed; the dependency is required only
when a 3D project is launched.
"""
import argparse
import math
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
        if shape == "model":
            model = item.get("model")
            if not isinstance(model, str) or not model.strip() or "://" in model or ".." in Path(model).parts:
                raise Monn3DError("مدل باید مسیر فایل محلی و بدون پیمایش پوشه باشد.")
        normalized.append(entry)
    player = world.get("player", {})
    if not isinstance(player, dict):
        raise Monn3DError("تنظیم بازیکن سه‌بعدی معتبر نیست.")
    return {
        "title": str(world.get("title") or project.get("meta", {}).get("title") or "Monn 3D"),
        "player": {
            "position": _vector(player.get("position", [0, -8, 1.7]), "player.position"),
            "speed": max(0.5, min(float(player.get("speed", 8)), 40)),
            "sensitivity": max(0.02, min(float(player.get("sensitivity", 0.12)), 1.0)),
        },
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
            "موتور سه‌بعدی نصب نیست. اجرا کن: py -m pip install -e ".[3d-runtime]""
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
            self.obstacles = []
            self.enemies = []
            self.projectiles = []
            self.health = 100
            self.score = 0
            self._lighting()
            self._floor()
            self._objects()
            self.camera.setPos(*config["player"]["position"])
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
            self.taskMgr.add(self.update, "monn-3d-update")

        def set_key(self, key, value):
            self.keys[key] = value

        def _lighting(self):
            ambient = AmbientLight("monn-ambient")
            ambient.setColor(Vec4(0.38, 0.42, 0.52, 1))
            self.render.setLight(self.render.attachNewNode(ambient))
            sun = DirectionalLight("monn-sun")
            sun.setColor(Vec4(0.95, 0.92, 0.82, 1))
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
                rgb = tuple(int(item["color"][i:i + 2], 16) / 255.0 for i in (1, 3, 5))
                node.setColor(rgb[0], rgb[1], rgb[2], 1)
                node.setTag("monn-id", item["id"])
                if item["solid"]:
                    center = item["position"]
                    half = [value * 0.5 for value in item["scale"]]
                    self.obstacles.append({"center": tuple(center), "half": tuple(half)})
                if item["role"] in ("enemy", "target"):
                    self.enemies.append({"node": node, "health": int(item.get("health", 3)), "alive": True})

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
            direction = self.camera.getQuat(self.render).getForward()
            origin = self.camera.getPos(self.render) + direction * 0.8
            bullet = self.loader.loadModel("models/misc/sphere")
            bullet.reparentTo(self.render)
            bullet.setScale(0.12)
            bullet.setPos(origin)
            bullet.setColor(1, 0.78, 0.18, 1)
            self.projectiles.append({"node": bullet, "direction": direction, "life": 2.2})

        def update(self, task):
            dt = min(ClockObject.getGlobalClock().getDt(), 0.05)
            self._look()
            quat = self.camera.getQuat(self.render)
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
            if movement.lengthSquared() > 0:
                movement.normalize()
                current = self.camera.getPos()
                candidate = current + movement * self.speed * dt
                if not self._blocked(candidate):
                    self.camera.setPos(candidate)
            for shot in list(self.projectiles):
                shot["life"] -= dt
                shot["node"].setPos(shot["node"].getPos() + shot["direction"] * 28 * dt)
                hit = False
                pos = shot["node"].getPos()
                for enemy in self.enemies:
                    if not enemy["alive"]:
                        continue
                    if (enemy["node"].getPos() - pos).length() < max(enemy["node"].getScale()) * 0.8 + 0.2:
                        enemy["health"] -= 1
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
    app.run()


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
