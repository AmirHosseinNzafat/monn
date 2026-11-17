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
