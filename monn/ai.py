"""OpenAI-compatible API client. Secrets are read from environment variables."""
import json
import os
import urllib.error
import urllib.request


class AIClient:
    def __init__(self, base_url=None, api_key=None, model=None, timeout=90):
        self.base_url = (base_url or os.getenv("MONN_API_BASE", "https://openrouter.ai/api/v1")).rstrip("/")
        self.image_base_url = os.getenv("MONN_IMAGE_API_BASE", self.base_url).rstrip("/")
        self.api_key = api_key or os.getenv("MONN_API_KEY")
        self.model = model or os.getenv("MONN_MODEL", "openrouter/free")
        self.timeout = timeout

    def _post(self, endpoint, payload, base_url=None):
        if not self.api_key:
            raise RuntimeError("کلید API تنظیم نشده است. متغیر MONN_API_KEY را تنظیم کنید.")
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            (base_url or self.base_url) + endpoint, data=body, method="POST",
            headers={"Authorization": "Bearer " + self.api_key,
                     "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/AmirHosseinNzafat/monn",
                     "X-Title": "MonnLang"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:1000]
            raise RuntimeError("AI API HTTP %s: %s" % (exc.code, detail)) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("اتصال به API ناموفق بود: %s" % exc.reason) from exc

    def chat(self, messages, temperature=0.7):
        data = self._post("/chat/completions", {
            "model": self.model, "messages": messages,
            "temperature": temperature
        })
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("پاسخ API ساختار مورد انتظار را ندارد: " + str(data)[:500]) from exc

    def generate_image(self, prompt, size="1024x1024"):
        data = self._post("/images/generations", {
            "model": os.getenv("MONN_IMAGE_MODEL", self.model),
            "prompt": prompt, "size": size, "response_format": "b64_json"
        }, base_url=self.image_base_url)
        if not data.get("data"):
            raise RuntimeError("سرویس تصویر خروجی قابل استفاده برنگرداند.")
        return data["data"][0]
