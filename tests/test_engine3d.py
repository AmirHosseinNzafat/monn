import unittest

from monn.engine3d import Monn3DError, validate_world3d


class Monn3DValidationTests(unittest.TestCase):
    def test_valid_3d_action_world(self):
        result = validate_world3d({
            "meta": {"title": "آزمایش سه‌بعدی"},
            "world3d": {
                "enabled": True,
                "player": {"position": [0, -8, 1.7], "speed": 8},
                "objects": [
                    {"id": "enemy", "shape": "box", "position": [0, 5, 1],
                     "scale": [1, 1, 2], "role": "enemy", "solid": True,
                     "color": "#ff3344"}
                ],
            },
        })
        self.assertEqual(result["objects"][0]["role"], "enemy")
        self.assertEqual(result["player"]["speed"], 8)

    def test_enemy_ai_parameters_are_normalized_and_bounded(self):
        result = validate_world3d({
            "world3d": {"objects": [
                {"id": "guard", "role": "enemy", "health": 15,
                 "speed": 3.5, "damage": 12}
            ]}
        })
        enemy = result["objects"][0]
        self.assertEqual(enemy["health"], 15)
        self.assertEqual(enemy["speed"], 3.5)
        self.assertEqual(enemy["damage"], 12)

    def test_invalid_enemy_ai_parameters_are_rejected(self):
        for field, value in (("speed", 500), ("damage", -1), ("health", 0)):
            with self.subTest(field=field):
                with self.assertRaises(Monn3DError):
                    validate_world3d({"world3d": {"objects": [
                        {"id": "guard", "role": "enemy", field: value}
                    ]}})

    def test_repository_action_sample_loads_and_validates(self):
        from pathlib import Path
        from monn.game import load_project
        path = Path(__file__).parent.parent / "examples" / "action_3d_demo.mongame.json"
        project = load_project(path)
        result = validate_world3d(project.data)
        self.assertEqual(result["title"], "میدان تمرین")
        self.assertEqual(len(result["objects"]), 5)

    def test_duplicate_3d_ids_are_rejected(self):
        project = {"world3d": {"objects": [{"id": "x"}, {"id": "x"}]}}
        with self.assertRaises(Monn3DError):
            validate_world3d(project)

    def test_model_path_traversal_is_rejected(self):
        project = {"world3d": {"objects": [
            {"id": "model", "shape": "model", "model": "../secret.glb"}
        ]}}
        with self.assertRaises(Monn3DError):
            validate_world3d(project)

    def test_non_finite_coordinates_are_rejected(self):
        project = {"world3d": {"objects": [
            {"id": "box", "position": [0, float("nan"), 0]}
        ]}}
        with self.assertRaises(Monn3DError):
            validate_world3d(project)


if __name__ == "__main__":
    unittest.main()
