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
        restored = loads_monn(source)
        self.assertEqual(restored.data, original.data)

    def test_load_project_reads_native_monn_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.monn"
            path.write_text(dumps_monn(sample()), encoding="utf-8")
            loaded = load_project(path)
            self.assertEqual(loaded.title, "آزمایش استودیو")

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
