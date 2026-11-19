import unittest

from monn.game import GameProject
from monn.nitro_offline import build_offline_project, templates


class OfflineNitroTests(unittest.TestCase):
    def test_all_starter_templates_are_valid_projects(self):
        for name, data in templates().items():
            with self.subTest(template=name):
                project = GameProject(data)
                self.assertGreaterEqual(len(project.scenes), 2)
                self.assertTrue(project.start_scene)

    def test_workshop_contains_3d_objects_and_lighting(self):
        project = GameProject(build_offline_project(template="workshop_medium"))
        self.assertTrue(project.data["world3d"]["enabled"])
        self.assertGreaterEqual(len(project.data["world3d"]["objects"]), 3)
        self.assertGreater(project.data["world3d"]["lighting"]["directional"], 0)

    def test_battle_prompt_selects_battle_base(self):
        project = GameProject(build_offline_project("یک بتل‌بیس با دشمن و پایگاه", "starter"))
        self.assertEqual(project.project_id, "battle-base")
        self.assertTrue(any(item.get("role") == "enemy" for item in project.data["world3d"]["objects"]))

    def test_romance_prompt_selects_short_story(self):
        project = GameProject(build_offline_project("یک داستان عاشقانه زیر باران", "starter"))
        self.assertEqual(project.project_id, "rainy-letter")
        self.assertGreaterEqual(len(project.scenes), 4)

    def test_templates_are_independent_copies(self):
        first = build_offline_project(template="battle_base")
        first["world3d"]["objects"].clear()
        second = build_offline_project(template="battle_base")
        self.assertTrue(second["world3d"]["objects"])


if __name__ == "__main__":
    unittest.main()
