import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from monn.game import GameProject, load_project
from monn.game_dsl import dumps_monn, loads_monn
from monn.web_game import compile_game_to_html
from monn.studio import StudioHandler


def sample():
    return {
        "meta": {"id": "studio-test", "title": "آزمایش استودیو", "start_scene": "start"},
        "player": {"health": 100, "max_health": 100, "stats": {"سکه": 0}, "inventory": []},
        "characters": [{"id": "guide", "name": "راهنما"}],
        "scenes": [
            {"id": "start", "title": "آغاز", "text": "سلام", "choices": [
                {"id": "go", "text": "ادامه", "target": "end", "conditions": [], "effects": []}
            ]},
            {"id": "end", "title": "پایان", "text": "تمام", "choices": []},
        ],
    }


class MonnStudioTests(unittest.TestCase):
    def test_native_monn_round_trip(self):
        original = GameProject(sample())
        source = dumps_monn(original)
        self.assertIn('بازی "آزمایش استودیو"', source)
        self.assertIn('صحنه "start"', source)
        self.assertNotIn("پروژه =", source)
        restored = loads_monn(source)
        self.assertEqual(restored.data, original.data)

    def test_load_project_reads_native_monn_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.monn"
            path.write_text(dumps_monn(sample()), encoding="utf-8")
            loaded = load_project(path)
            self.assertEqual(loaded.title, "آزمایش استودیو")

    def test_native_monn_example_parses_and_compiles(self):
        path = Path(__file__).parent.parent / "examples" / "studio_demo.monn"
        project = load_project(path)
        self.assertEqual(project.title, "ماجرای دروازه")
        html = compile_game_to_html(project)
        self.assertIn("world-canvas", html)
        self.assertIn("menu-screen", html)

    def test_studio_builds_standalone_html_from_valid_project(self):
        html = compile_game_to_html(GameProject(sample()))
        self.assertIn("آزمایش استودیو", html)
        self.assertIn("const GAME", html)

    def test_download_filename_is_safe_ascii(self):
        name = StudioHandler._filename("بازی ما")
        self.assertEqual(name, "monn-game.html")
        self.assertTrue(name.isascii())

    def test_embedded_image_asset_is_accepted(self):
        project = sample()
        project["scenes"][0]["image"] = "data:image/png;base64,aGVsbG8="
        GameProject(project)

    def test_studio_choice_logic_uses_visual_editor(self):
        html_path = Path(__file__).parent.parent / "monn" / "studio" / "index.html"
        html = html_path.read_text(encoding="utf-8")
        match = re.search(r"function editLogic\(i\)\{([^}]+)\}", html)
        self.assertIsNotNone(match)
        self.assertIn("renderLogicEditor()", match.group(1))
        self.assertNotIn("prompt(", match.group(1))
        self.assertIn("function syncLogicEditorDraft()", html)
        self.assertIn("function addExpressionFromAsset()", html)
        self.assertIn("charExpressionAsset", html)
        self.assertIn("$('eo'+i)?.value", html)

    def test_compiled_runtime_contains_interactive_media_ai_and_2d_features(self):
        project = sample()
        project["characters"][0]["ai"] = {
            "enabled": True, "system_prompt": "در نقش نگهبان پاسخ بده.",
            "rules": [{"trigger": "سلام", "response": "درود"}],
        }
        project["characters"][0]["video"] = "assets/guard.mp4"
        project["characters"][0]["expressions"] = {"happy": "assets/happy.mp4"}
        project["characters"][0]["model"] = "assets/guard.glb"
        project["scenes"][0]["video"] = "assets/scene.mp4"
        project["scenes"][0]["dialogue"] = [
            {"character": "guide", "text": "سلام", "expression": "happy",
             "voice": "assets/voice.ogg"}
        ]
        project["world"] = {
            "enabled": True, "width": 800, "height": 450,
            "player": {"x": 10, "y": 10, "width": 28, "height": 40, "frames": 4, "fps": 8},
            "sprites": [{"id": "wall", "x": 100, "y": 80, "width": 40, "height": 80, "solid": True}],
        }
        project["ui"] = {
            "menu_enabled": True,
            "elements": [{"type": "name_input", "text": "نام بازیکن"},
                         {"type": "location", "text": "مکان فعلی"}],
        }
        html = compile_game_to_html(GameProject(project))
        for feature in ("renderAICharacters", "chat/completions", "drawWorldFrame",
                        "function overlaps", "name_input", "scene-video", "model-viewer",
                        "credits-list"):
            self.assertIn(feature, html)

    def test_video_ai_2d_and_3d_project_schema(self):
        project = sample()
        project["characters"][0].update({
            "video": "data:video/mp4;base64,aGVsbG8=",
            "expressions": {"happy": "data:video/mp4;base64,aGVsbG8="},
            "model": "data:model/gltf-binary;base64,aGVsbG8=",
            "ai": {"enabled": True, "rules": [{"trigger": "سلام", "response": "درود"}]},
        })
        project["scenes"][0]["video"] = "data:video/mp4;base64,aGVsbG8="
        project["scenes"][0]["model"] = "data:model/gltf-binary;base64,aGVsbG8="
        project["world"] = {
            "enabled": True, "width": 800, "height": 450,
            "sprites": [{"id": "wall", "x": 20, "y": 30, "width": 80, "height": 80,
                         "solid": True, "model": "data:model/gltf-binary;base64,aGVsbG8="}],
            "player": {"x": 10, "y": 10, "image": "data:image/png;base64,aGVsbG8="},
        }
        project["ui"] = {"menu_enabled": True, "elements": [{"type": "name_input", "text": "نام"}]}
        GameProject(project)

    def test_native_monn_round_trip_preserves_advanced_game_features(self):
        project = sample()
        project["meta"].update({"author": "سازنده", "license": "CC BY 4.0", "ending_scene": "end"})
        project["characters"][0].update({
            "video": "data:video/mp4;base64,aGVsbG8=",
            "expressions": {"happy": "data:video/mp4;base64,aGVsbG8="},
            "ai": {"enabled": True, "model": "example-model", "system_prompt": "نقش نگهبان",
                   "api_base": "https://example.test/v1",
                   "rules": [{"trigger": "سلام", "response": "درود"}]},
        })
        project["scenes"][0]["dialogue"] = [
            {"character": "guide", "text": "سلام", "expression": "happy",
             "video": "data:video/mp4;base64,aGVsbG8=", "voice": "data:audio/ogg;base64,aGVsbG8="}
        ]
        project["scenes"][0]["choices"][0]["conditions"] = [
            {"type": "stat", "name": "سکه", "op": ">=", "value": 2}
        ]
        project["scenes"][0]["choices"][0]["effects"] = [
            {"type": "stat", "name": "سکه", "op": "add", "value": 2},
            {"type": "journal", "text": "کلید را پیدا کردم."}
        ]
        project["scenes"][0]["timeline"] = {
            "duration": 9, "fps": 30,
            "tracks": [{"id": "voice", "name": "صدا", "type": "audio",
                        "clips": [{"id": "clip1", "src": "assets/voice.ogg",
                                   "start": 1, "duration": 3, "in": 0.5, "out": 3.5}]}],
        }
        project["world"] = {
            "enabled": True, "width": 800, "height": 450,
            "player": {"x": 10, "y": 20, "width": 28, "height": 40, "frames": 4},
            "sprites": [{"id": "wall", "x": 20, "y": 30, "width": 80, "height": 80,
                         "solid": True, "image": "data:image/png;base64,aGVsbG8="}],
        }
        project["ui"] = {"menu_enabled": True, "start_label": "بزن بریم",
                         "elements": [{"type": "button", "text": "دروازه", "target": "end"},
                                     {"type": "location", "text": "مکان فعلی", "x": 5, "y": 5}]}
        project["assets"] = [{"name": "wall.png", "kind": "image", "data": "data:image/png;base64,aGVsbG8=",
                              "author": "هنرمند", "source": "https://example.test/wall", "license": "CC BY 4.0"}]
        original = GameProject(project)
        restored = loads_monn(dumps_monn(original))
        self.assertEqual(restored.data, original.data)


    def test_studio_has_visual_timeline_and_drag_ui_designer(self):
        html_path = Path(__file__).parent.parent / "monn" / "studio" / "index.html"
        html = html_path.read_text(encoding="utf-8")
        for feature in ("openTimelineEditor", "addTimelineClip", "selectTimelineClip",
                        "saveTimelineEditor", "openUIDesigner", "addDesignerElement",
                        "wireDesignerItems", "wireDesignerPalette", "dataTransfer.setData",
                        "applyDesignerInspector", "designer-canvas", "function preview()",
                        "tabWorld3D", "renderWorld3DEditor", "add3DObject", "render3DInspector",
                        "world3DCanvas", "drawWorld3DViewport", "world3DPointerMove",
                        "camera_mode", "update3DWeapon", "view3DZoom",
                        "getContext('webgl'", "load3DGLB", "set3DGizmo",
                        "gizmoRotate", "m4Perspective", "uLight", "uAmbient",
                        "GLTF", "rotation", "frame3DSelection",
                        "update3DLighting", "update3DLightDirection",
                        "model_asset", "m4NodeTRS", "world3DProjectPoint"):
            self.assertIn(feature, html)

    def test_compiled_runtime_runs_timeline_and_renders_designer_images(self):
        project = sample()
        project["scenes"][0]["timeline"] = {
            "duration": 12, "fps": 30,
            "tracks": [
                {"id": "audio", "name": "صدا", "type": "audio",
                 "clips": [{"id": "a1", "src": "assets/music.ogg", "start": 1,
                            "duration": 4, "in": 0, "out": 4}]},
                {"id": "animation", "name": "حرکت", "type": "animation",
                 "clips": [{"id": "m1", "target": "title", "property": "opacity",
                            "start": 0, "duration": 2, "from": 0, "to": 1}]},
            ],
        }
        project["ui"] = {"elements": [
            {"id": "title", "type": "text", "text": "عنوان", "x": 5, "y": 5,
             "width": 30, "height": 10},
            {"id": "logo", "type": "image", "src": "assets/logo.png", "x": 2, "y": 2,
             "width": 10, "height": 10},
        ]}
        html = compile_game_to_html(GameProject(project))
        for feature in ("startSceneTimeline", "timelineAudio", "data-ui-id",
                        'el.type==="image"', "scene?.timeline"):
            self.assertIn(feature, html)

    def test_compiled_browser_runtime_javascript_syntax_when_node_is_available(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed")
        html = compile_game_to_html(GameProject(sample()))
        scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
        self.assertTrue(scripts)
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "runtime.js"
            script.write_text(scripts[-1], encoding="utf-8")
            result = subprocess.run([node, "--check", str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_studio_javascript_syntax_when_node_is_available(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed")
        html_path = Path(__file__).parent.parent / "monn" / "studio" / "index.html"
        html = html_path.read_text(encoding="utf-8")
        match = re.search(r"<script>(.*?)</script>", html, re.S)
        self.assertIsNotNone(match)
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "studio.js"
            script.write_text(match.group(1), encoding="utf-8")
            result = subprocess.run([node, "--check", str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
