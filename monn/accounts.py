"""Local Monn Studio profiles with salted password hashing."""
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
from pathlib import Path


class AccountError(Exception):
    pass


class LocalAccountStore:
    ITERATIONS = 310000

    def __init__(self, path=None):
        self.path = Path(path or Path.home() / ".monn" / "accounts.json")
        self._lock = threading.RLock()
        self._sessions = {}

    def _read(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            raise AccountError("فایل حساب‌های محلی قابل خواندن نیست.")

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            os.chmod(temp, 0o600)
        except OSError:
            pass
        temp.replace(self.path)

    @staticmethod
    def _username(value):
        if not isinstance(value, str):
            raise AccountError("نام کاربری معتبر نیست.")
        value = value.strip()
        if not re.fullmatch(r"[\w.-]{3,32}", value):
            raise AccountError("نام کاربری باید ۳ تا ۳۲ نویسه باشد و می‌تواند شامل حروف فارسی یا انگلیسی، عدد، نقطه، خط تیره و زیرخط باشد.")
        return value.lower()

    def register(self, username, password):
        username = self._username(username)
        if not isinstance(password, str) or len(password) < 8 or len(password) > 256:
            raise AccountError("گذرواژه باید حداقل ۸ نویسه داشته باشد.")
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.ITERATIONS)
        with self._lock:
            data = self._read()
            if username in data:
                raise AccountError("این نام کاربری قبلاً ثبت شده است.")
            data[username] = {
                "salt": salt.hex(), "hash": digest.hex(),
                "iterations": self.ITERATIONS, "created": __import__("time").time(),
            }
            self._write(data)
        return self.login(username, password)

    def login(self, username, password):
        username = self._username(username)
        if not isinstance(password, str):
            raise AccountError("گذرواژه معتبر نیست.")
        with self._lock:
            record = self._read().get(username)
            if not record:
                raise AccountError("نام کاربری یا گذرواژه اشتباه است.")
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(record["salt"]),
                int(record.get("iterations", self.ITERATIONS)),
            ).hex()
            if not hmac.compare_digest(digest, record["hash"]):
                raise AccountError("نام کاربری یا گذرواژه اشتباه است.")
            token = secrets.token_urlsafe(32)
            self._sessions[token] = username
            return {"token": token, "username": username}

    def authenticate(self, token):
        if not isinstance(token, str):
            return None
        with self._lock:
            return self._sessions.get(token)

    def logout(self, token):
        with self._lock:
            self._sessions.pop(token, None)
