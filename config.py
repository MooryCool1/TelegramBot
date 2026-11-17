import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")

AUTO_REPLY = os.getenv(
    "AUTO_REPLY",
    "false"
).lower() == "true"


def validate_config():
    required = {
        "TELEGRAM_API_ID": TELEGRAM_API_ID,
        "TELEGRAM_API_HASH": TELEGRAM_API_HASH,
        "TELEGRAM_PHONE": TELEGRAM_PHONE,
        "GROQ_API_KEY": GROQ_API_KEY,
        "TARGET_CHAT_ID": TARGET_CHAT_ID,
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
        int(TARGET_CHAT_ID)
    except ValueError:
        raise ValueError(
            "TELEGRAM_API_ID and TARGET_CHAT_ID must be numbers."
        )