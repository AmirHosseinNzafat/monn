"""Explicitly opt-in discovery for third-party Monn extensions.

Discovery reads package metadata only. Extension code is imported only after the
caller explicitly approves loading it.
"""
import importlib.metadata


ENTRY_POINT_GROUP = "monn.extensions"


class ExtensionError(Exception):
    pass


class ExtensionRegistry:
    def __init__(self):
        self.tools = {}

    def register_tool(self, name, callback, description=""):
        if not isinstance(name, str) or not name.strip() or name in self.tools:
            raise ExtensionError("نام ابزار افزونه خالی یا تکراری است.")
        if not callable(callback):
            raise ExtensionError("ابزار افزونه باید تابع قابل اجرا باشد.")
        self.tools[name] = {"callback": callback, "description": str(description)[:500]}


def _entry_points():
    entries = importlib.metadata.entry_points()
    if hasattr(entries, "select"):
        return list(entries.select(group=ENTRY_POINT_GROUP))
    return list(entries.get(ENTRY_POINT_GROUP, []))


def discover_extensions():
    """Return installed extension metadata without importing extension code."""
    result = []
    for entry in _entry_points():
        result.append({
            "name": entry.name,
            "target": entry.value,
            "distribution": getattr(getattr(entry, "dist", None), "name", None),
            "description": getattr(entry, "value", ""),
            "loaded": False,
        })
    return sorted(result, key=lambda item: item["name"].lower())


def load_extension(name, registry=None, approved=False):
    """Load one extension only after an explicit user approval."""
    if not approved:
        raise ExtensionError("بارگذاری افزونه نیازمند تأیید صریح کاربر است.")
    entry = next((item for item in _entry_points() if item.name == name), None)
    if entry is None:
        raise ExtensionError("افزونه نصب‌شده پیدا نشد: " + str(name))
    try:
        register = entry.load()
        if not callable(register):
            raise ExtensionError("نقطه ورود افزونه باید تابع register باشد.")
        target = registry or ExtensionRegistry()
        register(target)
        return target
    except ExtensionError:
        raise
    except Exception as exc:
        raise ExtensionError("بارگذاری افزونه ناموفق بود: " + str(exc)) from exc
