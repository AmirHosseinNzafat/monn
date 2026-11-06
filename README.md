# MonnLang

MonnLang یک زبان نقطه‌ای برای ساخت برنامه‌های دسکتاپ با Python و Tkinter است. فایل‌های آن پسوند .monn دارند و می‌توانند پنجره، ویجت، استایل، ابزارهای رسانه‌ای و رابط چت هوش مصنوعی بسازند.

## نصب

Python 3.8 یا جدیدتر لازم است.

\`\`\`powershell
git clone https://github.com/AmirHosseinNzafat/monn.git
cd monn
py -m pip install .
\`\`\`

قابلیت‌های اختیاری عکس و سه‌بعدی:

\`\`\`powershell
py -m pip install ".[all]"
\`\`\`

یا فقط مورد موردنیاز:

\`\`\`powershell
py -m pip install ".[images]"
py -m pip install ".[3d]"
\`\`\`

## اجرا

\`\`\`powershell
monn examples/hello.monn
\`\`\`

یا:

\`\`\`powershell
py -m monn_cli examples/hello.monn
\`\`\`

در ویندوز می‌توانی فایل monn.bat را نیز اجرا کنی.

## نمونه رابط کاربری

\`\`\`text
...
##title:برنامه من
##size:700x500
...theme:dark
##bg:#172033
##fg:#f8fafc
##font:13
##padding:8
..... 'به برنامه من خوش آمدید'
.... 'شروع'
..tabs
..combo
..slider
..progress
\`\`\`

## ده قابلیت استایل

| فرمان | کاربرد |
|---|---|
| ##bg:#172033 | تعیین رنگ پس‌زمینه |
| ##fg:#ffffff | تعیین رنگ نوشته |
| ##font:13 | تعیین اندازه فونت |
| ##color | بازکردن انتخاب‌گر رنگ گرافیکی |
| ##padding:8 | فاصله ویجت‌ها |
| ##relief:groove | سبک قاب |
| ##cursor:hand2 | شکل نشانگر ماوس |
| ##alpha:0.95 | شفافیت پنجره از 0.2 تا 1 |
| ##resizable:1 | اجازه تغییر اندازه پنجره؛ 0 برای غیرفعال |
| ...theme:dark / ...theme:light | پوسته تیره یا روشن |

فرمان ##color پنجره انتخاب رنگ سیستم را باز می‌کند. رنگ‌های CSS مانند #12a4ef نیز پذیرفته می‌شوند.

## قابلیت‌های رابط و عملکرد

| فرمان | کاربرد |
|---|---|
| ..tabs | ساخت تب‌ها |
| ..list | فهرست انتخاب |
| ..combo | فهرست کشویی |
| ..slider | نوار لغزنده |
| ..progress | نوار پیشرفت |
| ..menu | منوی فایل و خروج |
| ..chat | پنجره چت هوش مصنوعی |
| ..ask:نام شما چیست؟ | پرسیدن ورودی از کاربر |
| ..openimage | انتخاب و نمایش تصویر |
| ..model3d | انتخاب و نمایش فایل سه‌بعدی |
| ..image:prompt | درخواست تولید تصویر از API سازگار |
| ..create3d:cube | ساخت مدل OBJ مکعب |
| ..create3d:pyramid | ساخت مدل OBJ هرم |
| ..create3d:diamond | ساخت مدل OBJ الماس |

فرمان‌های پایه نیز شامل ساخت دکمه، برچسب، ورودی، کادر متن، چک‌باکس، ماشین‌حساب، متغیر و پنجره هستند.

## اتصال هوش مصنوعی از طریق API

Monn از APIهای سازگار با قالب OpenAI Chat Completions استفاده می‌کند. کلید را داخل سورس یا GitHub قرار نده؛ آن را در متغیر محیطی سیستم تنظیم کن.

نمونه PowerShell:

\`\`\`powershell
$env:MONN_API_KEY="کلید-خصوصی-تو"
$env:MONN_API_BASE="https://openrouter.ai/api/v1"
$env:MONN_MODEL="openrouter/free"
py -m monn_cli examples/ai_chat.monn
\`\`\`

در Linux/macOS:

\`\`\`bash
export MONN_API_KEY="your-secret-key"
export MONN_API_BASE="https://openrouter.ai/api/v1"
export MONN_MODEL="openrouter/free"
python -m monn_cli examples/ai_chat.monn
\`\`\`

متغیرها:
- MONN_API_KEY: کلید API
- MONN_API_BASE: آدرس پایه ارائه‌دهنده
- MONN_MODEL: نام مدل چت
- MONN_IMAGE_API_BASE: آدرس پایه سرویس تصویر؛ در صورت تنظیم‌نشدن از MONN_API_BASE استفاده می‌شود
- MONN_IMAGE_MODEL: نام مدل تولید تصویر؛ در صورت تنظیم‌نشدن از MONN_MODEL استفاده می‌شود

چت به endpoint استاندارد /chat/completions نیاز دارد. تولید تصویر به endpoint سازگار /images/generations نیاز دارد؛ بنابراین ممکن است با بعضی مدل‌ها یا سرویس‌های رایگان کار نکند. فعال‌بودن چت به معنی فعال‌بودن تولید تصویر نیست.

## تصاویر و مدل سه‌بعدی

برای نمایش تصویر، Pillow نصب کن:

\`\`\`powershell
py -m pip install Pillow
\`\`\`

برای نمایش مدل‌های OBJ/STL/PLY/GLB:

\`\`\`powershell
py -m pip install trimesh matplotlib
\`\`\`

Monn می‌تواند با فرمان‌های create3d مدل OBJ ساده بسازد. نمایش فایل‌های پیچیده به پشتیبانی کتابخانه‌های اختیاری وابسته است. این نسخه هنوز سرویس عمومی و مستقل برای تولید مدل سه‌بعدی با هوش مصنوعی ارائه نمی‌کند؛ برای آن باید API اختصاصی یک ارائه‌دهنده مدل سه‌بعدی اضافه شود.

## تست و بررسی

\`\`\`powershell
py -m compileall monn monn_cli.py
py -m unittest discover -s tests -v
\`\`\`

## امنیت

- Monn از eval برای اجرای ورودی یا محاسبات استفاده نمی‌کند.
- کلید API را در فایل .monn، سورس، commit یا مخزن عمومی ننویس.
- فایل‌های .monn ناشناس را فقط پس از بررسی اجرا کن.
- درخواست‌های شبکه‌ای API به اینترنت و کلید معتبر نیاز دارند.
- ابزارهای تصویری و سه‌بعدی به نصب وابستگی‌های اختیاری نیاز دارند.

## محدودیت‌های فعلی

شرط‌های ???? هنوز زبان شرطی کامل ندارند و حلقه ......[ در حال حاضر یک بار اجرا می‌شود. چیدمان‌های ..<, ..>, ..^, ..v و ..= در فهرست رزروشده‌اند و هنوز رفتار اختصاصی ندارند.
