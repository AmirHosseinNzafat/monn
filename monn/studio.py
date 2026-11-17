"""Local web-based Monn Studio authoring environment."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .game import GameProject
from .game_dsl import dumps_monn, loads_monn
from .web_game import compile_game_to_html
from .accounts import AccountError, LocalAccountStore
from .nitro import NitroAgent, NitroError

STUDIO_DIR = Path(__file__).with_name("studio")
ACCOUNTS = LocalAccountStore()
NITRO_PROPOSALS = {}


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "MonnStudio/1.4.3"

    def _token(self):
        header = self.headers.get("Authorization", "")
        return header[7:].strip() if header.startswith("Bearer ") else ""

    def _user(self):
        return ACCOUNTS.authenticate(self._token())

    def _require_user(self):
        user = self._user()
        if not user:
            self._json(401, {"ok": False, "error": "برای استفاده از این قابلیت ابتدا وارد حساب محلی شو."})
        return user

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = (STUDIO_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/health":
            self._json(200, {"ok": True, "studio": "Monn Studio"})
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/build", "/api/source", "/api/parse", "/api/auth/register", "/api/auth/login", "/api/auth/logout", "/api/nitro/propose", "/api/nitro/approve"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 48 * 1024 * 1024:
                raise ValueError("حجم پروژه باید کمتر از ۴۸ مگابایت باشد.")
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if path in ("/api/auth/register", "/api/auth/login"):
                if path.endswith("register"):
                    result = ACCOUNTS.register(payload.get("username"), payload.get("password"))
                else:
                    result = ACCOUNTS.login(payload.get("username"), payload.get("password"))
                self._json(200, {"ok": True, **result})
                return
            if path == "/api/auth/logout":
                ACCOUNTS.logout(self._token())
                self._json(200, {"ok": True})
                return
            if path == "/api/nitro/propose":
                if not self._require_user():
                    return
                proposal = NitroAgent(payload.get("endpoint"), payload.get("model")).propose(
                    payload.get("project"), payload.get("prompt"))
                NITRO_PROPOSALS[proposal["id"]] = {"user": self._user(), "proposal": proposal}
                self._json(200, {"ok": True, "id": proposal["id"], "summary": proposal["summary"],
                                 "operations": proposal["operations"], "project": proposal["project"],
                                 "before": proposal["before"], "after": proposal["after"]})
                return
            if path == "/api/nitro/approve":
                if not self._require_user():
                    return
                item = NITRO_PROPOSALS.pop(payload.get("id"), None)
                if not item or item["user"] != self._user():
                    raise NitroError("پیشنهاد پیدا نشد یا منقضی شده است؛ دوباره از نیترو درخواست کن.")
                from .nitro import NitroAgent
                updated = NitroAgent.approve(item["proposal"], payload.get("project"))
                self._json(200, {"ok": True, "project": updated})
                return
            if path == "/api/parse":
                project = loads_monn(payload.get("source", ""))
                self._json(200, project.data)
                return
            validated = GameProject(payload)
            if path == "/api/source":
                body = dumps_monn(validated).encode("utf-8")
                filename = self._filename(validated.title).replace(".html", ".monn")
                content_type = "text/plain; charset=utf-8"
            else:
                body = compile_game_to_html(validated).encode("utf-8")
                filename = self._filename(validated.title)
                content_type = "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", 'attachment; filename="{}"'.format(filename))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
        except (AccountError, NitroError) as exc:\n            self._json(400, {"ok": False, "error": str(exc)})\n        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(422, {"ok": False, "error": str(exc)})

    @staticmethod
    def _filename(title):
        safe = "".join(ch for ch in title if ch.isascii() and (ch.isalnum() or ch in "-_ ")).strip().replace(" ", "-")
        return (safe[:60] or "monn-game") + ".html"

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[Monn Studio] " + fmt % args)


def main():
    parser = argparse.ArgumentParser(description="اجرای محیط گرافیکی Monn Studio")
    parser.add_argument("--host", default="127.0.0.1", help="آدرس اتصال؛ پیش‌فرض فقط همین رایانه")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not (1 <= args.port <= 65535):
        parser.error("شماره پورت باید بین 1 تا 65535 باشد.")
    server = ThreadingHTTPServer((args.host, args.port), StudioHandler)
    url = "http://{}:{}/".format(args.host, args.port)
    print("Monn Studio آماده است: " + url)
    print("برای توقف، Ctrl+C را بزن.")
    if not args.no_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMonn Studio متوقف شد.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
