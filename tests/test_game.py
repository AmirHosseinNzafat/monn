import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from monn.game import (
    GameEngine, GameError, GameProject, GameStateError,
    GameValidationError, load_project,
)
from monn.web_game import compile_game_to_html


def sample_project():
    return {
        "meta": {"id": "test-story", "title": "داستان آزمایشی", "start_scene": "start"},
        "player": {
            "health": 50, "max_health": 80,
            "stats": {"coins": 0, "level": 1},
            "inventory": [{"name": "key", "count": 1}],
        },
        "quests": [{"id": "escape", "title": "فرار"}],
        "scenes": [
            {
                "id": "start", "title": "شروع", "text": "به ماجراجویی خوش آمدی",
                "choices": [
                    {
                        "id": "locked", "text": "در مخفی را باز کن", "target": "end",
                        "conditions": [{"type": "item", "name": "key", "op": ">=", "value": 1}],
                        "effects": [
                            {"type": "item", "name": "key", "action": "remove", "count": 1},
                            {"type": "quest", "id": "escape", "action": "start"},
                            {"type": "journal", "text": "در باز شد"},
                            {"type": "stat", "name": "coins", "op": "add", "value": 5},
                        ],
                    },
                    {
                        "id": "buy", "text": "سکه پیدا کن", "target": "start",
                        "effects": [{"type": "stat", "name": "coins", "op": "add", "value": 2}],
                    },
                    {
                        "id": "finish", "text": "پایان دادن", "target": None,
                        "effects": [{"type": "health", "op": "subtract", "value": 5}],
                    },
                ],
            },
            {"id": "end", "title": "پایان", "text": "آزاد شدی", "choices": []},
        ],
    }


class GameEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine(sample_project())

    def test_starts_at_declared_scene_and_initializes_player(self):
        self.assertEqual(self.engine.state["current_scene"], "start")
        self.assertEqual(self.engine.state["health"], 50)
        self.assertEqual(self.engine.state["inventory"], {"key": 1})
        self.assertEqual(self.engine.state["visited"], ["start"])

    def test_conditions_filter_choices(self):
        choices = self.engine.available_choices()
        self.assertEqual([c["id"] for c in choices], ["locked", "buy", "finish"])

    def test_choice_applies_effects_and_moves_scene(self):
        self.engine.choose("locked")
        state = self.engine.snapshot()
        self.assertEqual(state["current_scene"], "end")
        self.assertEqual(state["inventory"], {})
        self.assertEqual(state["stats"]["coins"], 5)
        self.assertEqual(state["quests"]["escape"], "active")
        self.assertEqual(state["journal"], ["در باز شد"])
        self.assertEqual(state["visited"], ["start", "end"])

    def test_choice_by_visible_index(self):
        self.engine.choose(1)
        self.assertEqual(self.engine.state["stats"]["coins"], 2)

    def test_invalid_choice_does_not_change_state(self):
        before = self.engine.snapshot()
        with self.assertRaises(GameStateError):
            self.engine.choose("not-a-choice")
        self.assertEqual(self.engine.snapshot(), before)

    def test_failed_effect_rolls_back_entire_choice(self):
        project = sample_project()
        project["scenes"][0]["choices"][0]["effects"] = [
            {"type": "stat", "name": "coins", "op": "add", "value": 99},
            {"type": "item", "name": "missing", "action": "remove", "count": 1},
        ]
        engine = GameEngine(project)
        before = engine.snapshot()
        with self.assertRaises(GameStateError):
            engine.choose("locked")
        self.assertEqual(engine.snapshot(), before)

    def test_health_is_clamped_and_zero_ends_game(self):
        project = sample_project()
        project["scenes"][0]["choices"][0]["effects"] = [
            {"type": "health", "op": "set", "value": 0}
        ]
        engine = GameEngine(project)
        engine.choose("locked")
        self.assertEqual(engine.state["health"], 0)
        self.assertTrue(engine.state["ended"])

    def test_ended_game_rejects_more_choices(self):
        self.engine.choose("finish")
        self.assertTrue(self.engine.state["ended"])
        with self.assertRaises(GameStateError):
            self.engine.choose("buy")

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "slot-1.json")
            self.engine.choose("buy")
            self.engine.save(path)
            restored = GameEngine(sample_project())
            restored.load(path)
            self.assertEqual(restored.snapshot(), self.engine.snapshot())

    def test_save_rejects_different_project(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "slot.json")
            self.engine.save(path)
            changed = sample_project()
            changed["meta"]["title"] = "نسخه دیگر"
            with self.assertRaises(GameStateError):
                GameEngine(changed).load(path)

    def test_corrupt_save_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "broken.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('{"engine_version":1}')
            with self.assertRaises(GameStateError):
                self.engine.load(path)

    def test_invalid_scene_reference_is_rejected(self):
        project = sample_project()
        project["scenes"][0]["choices"][0]["target"] = "missing"
        with self.assertRaises(GameValidationError):
            GameProject(project)

    def test_duplicate_scene_ids_are_rejected(self):
        project = sample_project()
        project["scenes"].append(dict(project["scenes"][0]))
        with self.assertRaises(GameValidationError):
            GameProject(project)

    def test_initial_item_and_quest_validation(self):
        project = sample_project()
        project["scenes"][0]["choices"][0]["effects"][1]["id"] = "unknown"
        with self.assertRaises(GameValidationError):
            GameProject(project)

    def test_project_load_from_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "game.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(sample_project(), handle, ensure_ascii=False)
            project = load_project(path)
            self.assertEqual(project.title, "داستان آزمایشی")

    def test_browser_export_has_gameplay_and_local_save(self):
        html = compile_game_to_html(sample_project())
        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("localStorage", html)
        self.assertIn("کوله‌پشتی", html)
        self.assertIn("در مخفی را باز کن", html)
        self.assertIn("textContent", html)
        self.assertNotIn("eval(", html)
    def test_repository_example_is_valid_and_exportable(self):
        example_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "examples", "story_adventure.mongame.json"
        )
        project = load_project(example_path)
        engine = GameEngine(project)
        self.assertEqual(engine.project.title, "راز ایستگاه آخر")
        self.assertTrue(engine.available_choices())
        html = compile_game_to_html(project)
        self.assertIn("راز ایستگاه آخر", html)

    def test_cli_builds_game_html(self):
        repo_root = os.path.dirname(os.path.dirname(__file__))
        example_path = os.path.join(repo_root, "examples", "story_adventure.mongame.json")
        with tempfile.TemporaryDirectory() as folder:
            output = os.path.join(folder, "index.html")
            result = subprocess.run(
                [sys.executable, os.path.join(repo_root, "monn_cli.py"),
                 example_path, "--game", "--web", "--output", output],
                cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(output, "r", encoding="utf-8") as handle:
                self.assertIn("راز ایستگاه آخر", handle.read())


    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_generated_browser_javascript_passes_node_syntax_check(self):
        html = compile_game_to_html(sample_project())
        match = re.search(r"<script>(.*?)</script>", html, re.S)
        self.assertIsNotNone(match)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", encoding="utf-8", delete=False) as handle:
            handle.write(match.group(1))
            script_path = handle.name
        try:
            result = subprocess.run(
                ["node", "--check", script_path], text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            os.unlink(script_path)


if __name__ == "__main__":
    unittest.main()
