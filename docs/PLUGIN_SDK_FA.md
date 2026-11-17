# راهنمای توسعه افزونه‌های Monn

Monn یک مسیر افزونه‌پذیری اولیه دارد تا توسعه‌دهندگان بتوانند ابزارهای اختصاصی بسازند. کشف افزونه‌ها فقط فرادادهٔ بسته‌ها را می‌خواند و کد افزونه را اجرا نمی‌کند. بارگذاری هر افزونه نیازمند تأیید صریح کاربر است؛ افزونهٔ پایتون پس از بارگذاری می‌تواند کد دلخواه اجرا کند، پس فقط افزونه‌های مورد اعتماد را فعال کن.

## ساختار افزونه

یک بستهٔ پایتون بساز و در `pyproject.toml` آن نقطهٔ ورود را معرفی کن:

```toml
[project.entry-points."monn.extensions"]
my-tools = "my_monn_tools:register"
```

در ماژول `my_monn_tools.py`:

```python
def register(registry):
    def say_hello(project):
        return "سلام از افزونه Monn"

    registry.register_tool(
        "hello",
        say_hello,
        description="یک ابزار نمونه برای آزمایش افزونه",
    )
```

## کشف و بارگذاری

```python
from monn.extensions import discover_extensions, load_extension

# فقط نام و اطلاعات بسته را نشان می‌دهد؛ کد اجرا نمی‌شود.
print(discover_extensions())

# فقط پس از تأیید کاربر:
registry = load_extension("my-tools", approved=True)
print(registry.tools.keys())
```

## اصول انتشار

- نام افزونه، نسخه، نویسنده، مجوز و منبع را روشن اعلام کن.
- وابستگی‌ها و دسترسی‌های شبکه/فایل را مستند کن.
- مجوز کد و دارایی‌های همراه را مشخص کن.
- هیچ افزونه‌ای را بی‌اجازه یا بی‌اطلاع کاربر بارگذاری نکن.
- این API نسخهٔ اولیه است و هنوز فروشگاه افزونه، امضای دیجیتال یا sandbox اجرای کد ندارد.
