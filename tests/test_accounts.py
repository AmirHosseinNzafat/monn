import tempfile
import unittest
from pathlib import Path

from monn.accounts import AccountError, LocalAccountStore


class LocalAccountTests(unittest.TestCase):
    def test_register_login_and_persian_username(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LocalAccountStore(Path(folder) / "accounts.json")
            created = store.register("امیر_123", "pass-word-8")
            self.assertEqual(created["username"], "امیر_123")
            self.assertEqual(store.authenticate(created["token"]), "امیر_123")
            logged_in = store.login("امیر_123", "pass-word-8")
            self.assertEqual(logged_in["username"], "امیر_123")

    def test_duplicate_username_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LocalAccountStore(Path(folder) / "accounts.json")
            store.register("player_01", "pass-word-8")
            with self.assertRaises(AccountError):
                store.register("PLAYER_01", "pass-word-8")

    def test_short_password_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LocalAccountStore(Path(folder) / "accounts.json")
            with self.assertRaises(AccountError):
                store.register("player_01", "short")


if __name__ == "__main__":
    unittest.main()
