import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "qwen/qwen3.8-27b"
)

# در مرحله اول دیگر به یک چت خاص محدود نیستیم.
# این مقدار فقط برای سازگاری با حافظه و یادگیری قدیمی نگه داشته شده است.
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID", "").strip()

# ارسال خودکار برای تمام چت‌های خصوصی، طبق تنظیم فایل .env
AUTO_REPLY = os.getenv(
    "AUTO_REPLY",
    "false"
).strip().lower() == "true"


def validate_config():
    required = {
        "TELEGRAM_API_ID": TELEGRAM_API_ID,
        "TELEGRAM_API_HASH": TELEGRAM_API_HASH,
        "TELEGRAM_PHONE": TELEGRAM_PHONE,
        "GROQ_API_KEY": GROQ_API_KEY,
    }

    missing = [
        name for name, value in required.items()
        if not value
    ]

    if missing:
        raise ValueError(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    try:
        int(TELEGRAM_API_ID)
    except (TypeError, ValueError):
        raise ValueError("TELEGRAM_API_ID must be a number.")

    if TARGET_CHAT_ID:
        try:
            int(TARGET_CHAT_ID)
        except ValueError:
            raise ValueError("TARGET_CHAT_ID must be a number when provided.")
