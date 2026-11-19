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

    def test_camera_modes_and_weapon_settings_are_normalized(self):
        result = validate_world3d({"world3d": {
            "player": {"camera_mode": "third_person", "camera_distance": 9},
            "weapon": {"damage": 4, "fire_rate": 6, "projectile_speed": 42, "range": 120},
        }})
        self.assertEqual(result["player"]["camera_mode"], "third_person")
        self.assertEqual(result["player"]["camera_distance"], 9)
        self.assertEqual(result["weapon"]["damage"], 4)
        self.assertEqual(result["weapon"]["fire_rate"], 6)
        self.assertEqual(result["weapon"]["projectile_speed"], 42)
        self.assertEqual(result["weapon"]["range"], 120)

    def test_object_rotation_is_normalized_and_applied_to_model_config(self):
        result = validate_world3d({"world3d": {"objects": [
            {"id": "crate", "shape": "box", "rotation": [15, 30, 45]}
        ]}})
        self.assertEqual(result["objects"][0]["rotation"], [15.0, 30.0, 45.0])

    def test_model_can_reference_embedded_project_asset(self):
        data = "data:model/gltf-binary;base64,AA=="
        result = validate_world3d({
            "assets": [{"kind": "model", "data": data}],
            "world3d": {"objects": [
                {"id": "imported", "shape": "model", "model": "robot.glb", "model_asset": 0}
            ]},
        })
        self.assertEqual(result["objects"][0]["model_data"], data)

    def test_invalid_model_asset_reference_is_rejected(self):
        with self.assertRaises(Monn3DError):
            validate_world3d({"assets": [], "world3d": {"objects": [
                {"id": "imported", "shape": "model", "model": "robot.glb", "model_asset": 4}
            ]}})

    def test_invalid_object_rotation_is_rejected(self):
        with self.assertRaises(Monn3DError):
            validate_world3d({"world3d": {"objects": [
                {"id": "crate", "rotation": [0, float("nan"), 0]}
            ]}})

    def test_invalid_camera_and_weapon_settings_are_rejected(self):
        invalid = [
            ({"player": {"camera_mode": "cinematic"}}, "camera"),
            ({"player": {"camera_distance": 99}}, "distance"),
            ({"weapon": {"damage": 0}}, "damage"),
            ({"weapon": {"fire_rate": 0}}, "fire_rate"),
            ({"weapon": {"projectile_speed": 999}}, "projectile_speed"),
            ({"weapon": {"range": -1}}, "range"),
        ]
        for settings, label in invalid:
            with self.subTest(setting=label):
                with self.assertRaises(Monn3DError):
                    validate_world3d({"world3d": settings})

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
