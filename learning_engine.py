
import json
import os
import re

from pathlib import Path


# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
USERS_DIR = DATA_DIR / "users"

LEGACY_FILE = DATA_DIR / "learned_preferences.json"

MAX_PREFERENCES = 80
MAX_PREFERENCE_LENGTH = 300


# -----------------------------------------
# FILE PATH
# -----------------------------------------

def _learning_file(chat_id=None):

    # سازگاری با نسخه قدیمی
    if chat_id is None:
        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        return LEGACY_FILE

    user_dir = USERS_DIR / str(chat_id)

    user_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    return user_dir / "learned_preferences.json"


# -----------------------------------------
# LOAD PREFERENCES
# -----------------------------------------

def load_learned_preferences(chat_id=None):

    file_path = _learning_file(chat_id)

    if not file_path.exists():
        return []

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, list):
            return []

        return [
            item
            for item in data[-MAX_PREFERENCES:]
            if isinstance(item, dict)
            and isinstance(item.get("content"), str)
        ]

    except (OSError, json.JSONDecodeError) as error:

        print(
            f"[-] Learning data loading error: {error}"
        )

        return []


# -----------------------------------------
# SAVE PREFERENCES
# -----------------------------------------

def save_learned_preferences(
    preferences,
    chat_id=None
):

    if not isinstance(preferences, list):
        return False

    file_path = _learning_file(chat_id)

    temp_file = file_path.with_suffix(".tmp")

    try:

        clean_preferences = []

        for item in preferences:

            if not isinstance(item, dict):
                continue

            content = item.get("content")

            if not isinstance(content, str):
                continue

            content = content.strip()

            if not content:
                continue

            clean_preferences.append({
                "category": str(
                    item.get("category", "general")
                )[:50],

                "content": content[:MAX_PREFERENCE_LENGTH],

                "source": str(
                    item.get("source", "explicit")
                )[:30]
            })

        clean_preferences = clean_preferences[
            -MAX_PREFERENCES:
        ]

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                clean_preferences,
                file,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            temp_file,
            file_path
        )

        return True

    except (OSError, TypeError, ValueError) as error:

        print(
            f"[-] Learning data save error: {error}"
        )

        if temp_file.exists():
            temp_file.unlink()

        return False


# -----------------------------------------
# ADD PREFERENCE
# -----------------------------------------

def add_learned_preference(
    chat_id,
    category,
    content
):

    if not isinstance(content, str):
        return False

    content = content.strip()

    if not content:
        return False

    content = content[:MAX_PREFERENCE_LENGTH]

    preferences = load_learned_preferences(chat_id)

    normalized = content.casefold()

    # جلوگیری از ثبت موارد تکراری
    for item in preferences:

        old_content = item.get(
            "content",
            ""
        )

        if (
            isinstance(old_content, str)
            and old_content.casefold() == normalized
            and item.get("category") == category
        ):  
            return True

    preferences.append({
        "category": category,
        "content": content,
        "source": "explicit_feedback"
    })

    return save_learned_preferences(
        preferences,
        chat_id
    )


# -----------------------------------------
# REMOVE PREFERENCE
# -----------------------------------------

def remove_learned_preference(
    chat_id,
    index
):

    preferences = load_learned_preferences(chat_id)

    if not isinstance(index, int):
        return False

    if index < 0 or index >= len(preferences):
        return False

    preferences.pop(index)

    return save_learned_preferences(
        preferences,
        chat_id
    )


# -----------------------------------------
# CLEAR PREFERENCES
# -----------------------------------------

def clear_learned_preferences(chat_id):

    return save_learned_preferences(
        [],
        chat_id
    )


# -----------------------------------------
# LEARN FROM MESSAGE
# -----------------------------------------

def learn_from_message(
    incoming_message,
    history=None,
    chat_id=None
):

    if chat_id is None:
        print(
            "[-] Learning skipped: chat_id is required."
        )

        return False

    if not isinstance(incoming_message, str):
        return False

    message = incoming_message.strip()

    if not message or len(message) > 1000:
        return False

    rules = [

        # درخواست پاسخ کوتاه
        (
            r"(?:کوتاه(?:تر)?|مختصرتر)\s+(?:جواب بده|پاسخ بده|حرف بزن)",
            "message_length",
            "مخاطب پاسخ‌های کوتاه و مختصر را ترجیح می‌دهد."
        ),

        # درخواست پاسخ مفصل
        (
            r"(?:مفصل(?:تر)?|با جزئیات بیشتر)\s+(?:جواب بده|پاسخ بده|توضیح بده)",
            "message_length",
            "مخاطب پاسخ‌های مفصل و دارای جزئیات را ترجیح می‌دهد."
        ),

        # عدم استفاده از ایموجی
        (
            r"(?:ایموجی|شکلک)\s+(?:نذار|استفاده نکن|نفرست)",
            "emoji_usage",
            "مخاطب پاسخ بدون ایموجی را ترجیح می‌دهد."
        ),

        # استفاده از ایموجی
        (
            r"(?:ایموجی|شکلک)\s+(?:بذار|استفاده کن|بفرست)",
            "emoji_usage",
            "مخاطب استفاده از ایموجی را ترجیح می‌دهد."
        ),

        # درخواست لحن رسمی
        (
            r"(?:رسمی(?:تر)?|مودبانه‌تر)\s+(?:حرف بزن|جواب بده|پاسخ بده)",
            "tone",
            "مخاطب لحن رسمی‌تر را ترجیح می‌دهد."
        ),

        # درخواست لحن خودمانی
        (
            r"(?:خودمونی‌تر|صمیمی‌تر|راحت‌تر)\s+(?:حرف بزن|جواب بده|پاسخ بده)",
            "tone",
            "مخاطب لحن خودمانی و صمیمی را ترجیح می‌دهد."
        ),

        # درخواست عدم تکرار
        (
            r"(?:تکرار نکن|اینقدر تکرار نکن|حرف(?:‌| )تکراری نزن)",
            "conversation_style",
            "مخاطب از تکرار عبارت‌ها و پاسخ‌های قبلی خوشش نمی‌آید."
        ),

        # درخواست فارسی
        (
            r"(?:فارسی\s+جواب بده|فارسی\s+حرف بزن)",
            "language",
            "مخاطب پاسخ فارسی را ترجیح می‌دهد."
        ),

        # درخواست عدم استفاده از خطاب خاص
        (
            r"(?:منو|من را)\s+با\s+(.+?)\s+(?:صدا نکن|خطاب نکن)",
            "addressing",
            None
        ),

        # درخواست شوخی کمتر
        (
            r"(?:شوخی نکن|کمتر شوخی کن|جدی‌تر باش)",
            "humor",
            "مخاطب لحن جدی‌تر و شوخی کمتر را ترجیح می‌دهد."
        ),

        # درخواست شوخی بیشتر
        (
            r"(?:بیشتر شوخی کن|شوخ(?:‌| )طبع‌تر باش)",
            "humor",
            "مخاطب لحن شوخ‌طبعانه‌تری را ترجیح می‌دهد."
        )
    ]

    for pattern, category, content in rules:

        match = re.search(
            pattern,
            message,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        if content is None:

            requested_term = match.group(1).strip()

            content = (
                f"مخاطب نمی‌خواهد با عبارت "
                f"«{requested_term}» خطاب شود."
            )

        result = add_learned_preference(
            chat_id,
            category,
            content
        )

        if result:

            print(
                f"[+] Learned preference for chat {chat_id}: "
                f"{category}"
            )

        return result

    return False
