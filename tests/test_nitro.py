import tempfile
import unittest
from pathlib import Path

from monn.accounts import AccountError, LocalAccountStore
from monn.nitro import NitroAgent, NitroError, project_fingerprint
from monn.game import GameProject


def sample():
    return {
        "meta": {"id": "nitro-test", "title": "بازی آزمایشی", "start_scene": "start"},
        "player": {"health": 100, "max_health": 100, "stats": {}, "inventory": []},
        "characters": [],
        "scenes": [{"id": "start", "title": "آغاز", "text": "متن اولیه", "choices": []}],
    }


class LocalAccountTests(unittest.TestCase):
    def test_register_login_logout_and_password_hashing(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LocalAccountStore(Path(folder) / "accounts.json")
            session = store.register("player_01", "a-strong-password")
            self.assertEqual(store.authenticate(session["token"]), "player_01")
            saved = (Path(folder) / "accounts.json").read_text(encoding="utf-8")
            self.assertNotIn("a-strong-password", saved)
            store.logout(session["token"])
            self.assertIsNone(store.authenticate(session["token"]))
            self.assertEqual(store.login("PLAYER_01", "a-strong-password")["username"], "player_01")

    def test_weak_password_and_duplicate_user_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LocalAccountStore(Path(folder) / "accounts.json")
            with self.assertRaises(AccountError):
                store.register("player", "short")
            store.register("player", "a-strong-password")
            with self.assertRaises(AccountError):
                store.register("player", "another-strong-password")


class NitroSafetyTests(unittest.TestCase):
    def test_allowlisted_edits_are_validated_and_approved(self):
        original = GameProject(sample()).data
        plan = [
            {"type": "set_scene_text", "scene_id": "start", "value": "متن تازه"},
            {"type": "add_scene", "id": "forest", "title": "جنگل", "text": "درختان بلند"},
            {"type": "add_choice", "scene_id": "start", "id": "go_forest",
             "text": "رفتن به جنگل", "target": "forest"},
            {"type": "add_character", "id": "guide", "name": "راهنما", "role": "راهنمای سفر"},
        ]
        changed = NitroAgent.apply_operations(original, plan)
        proposal = {"before": project_fingerprint(original), "after": project_fingerprint(changed),
                    "project": changed}
        approved = NitroAgent.approve(proposal, original)
        self.assertEqual(approved, changed)
        self.assertEqual(approved["scenes"][0]["choices"][0]["target"], "forest")

    def test_unsafe_operation_is_rejected(self):
        with self.assertRaises(NitroError):
            NitroAgent.apply_operations(sample(), [{"type": "execute_python", "code": "import os"}])

    def test_stale_proposal_is_rejected(self):
        original = sample()
        changed = NitroAgent.apply_operations(original, [
            {"type": "set_title", "value": "عنوان جدید"}
        ])
        proposal = {"before": project_fingerprint(original),
                    "after": project_fingerprint(changed), "project": changed}
        changed_by_user = NitroAgent.apply_operations(original, [
            {"type": "set_title", "value": "ویرایش دستی"}
        ])
        with self.assertRaises(NitroError):
            NitroAgent.approve(proposal, changed_by_user)

    def test_invalid_scene_reference_is_rejected(self):
        with self.assertRaises(NitroError):
            NitroAgent.apply_operations(sample(), [
                {"type": "add_choice", "scene_id": "start", "id": "bad",
                 "text": "انتخاب نامعتبر", "target": "missing"}
            ])


if __name__ == "__main__":
    unittest.main()
