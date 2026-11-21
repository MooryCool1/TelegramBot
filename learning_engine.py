
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
BEHAVIOR_THRESHOLD = 3


# -----------------------------------------
# FILE PATH
# -----------------------------------------

def _learning_file(chat_id=None):

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


def _behavior_file(chat_id):

    user_dir = USERS_DIR / str(chat_id)

    user_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    return user_dir / "behavior_observations.json"


# -----------------------------------------
# LOAD BEHAVIOR OBSERVATIONS
# -----------------------------------------

def _load_behavior_observations(chat_id):

    file_path = _behavior_file(chat_id)

    if not file_path.exists():
        return {
            "humor_positive": 0,
            "seen": []
        }

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Invalid behavior data")

        seen = data.get("seen", [])

        if not isinstance(seen, list):
            seen = []

        return {
            "humor_positive": max(
                0,
                int(data.get("humor_positive", 0))
            ),
            "seen": seen[-100:]
        }

    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:

        print(
            f"[-] Behavior loading error: {error}"
        )

        return {
            "humor_positive": 0,
            "seen": []
        }


# -----------------------------------------
# SAVE BEHAVIOR OBSERVATIONS
# -----------------------------------------

def _save_behavior_observations(chat_id, data):

    file_path = _behavior_file(chat_id)
    temp_file = file_path.with_suffix(".tmp")

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
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
            f"[-] Behavior save error: {error}"
        )

        if temp_file.exists():
            temp_file.unlink()

        return False


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
            "[-] Learning data save error:",
            error
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
    content,
    source="explicit_feedback"
):

    if not isinstance(content, str):
        return False

    content = content.strip()

    if not content:
        return False

    content = content[:MAX_PREFERENCE_LENGTH]

    preferences = load_learned_preferences(chat_id)

    normalized = content.casefold()

    # جلوگیری از ثبت تکراری
    for item in preferences:

        old_content = item.get("content", "")

        if (
            isinstance(old_content, str)
            and old_content.casefold() == normalized
            and item.get("category") == category
        ):

            return True

    # جایگزینی ترجیح قبلی در همان دسته
    preferences = [
        item
        for item in preferences
        if item.get("category") != category
    ]

    preferences.append({
        "category": category,
        "content": content,
        "source": source
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
# BEHAVIOR LEARNING
# -----------------------------------------

def learn_from_behavior(incoming_message, history, chat_id):
    if not history:
        return False

    positive_reactions = (
        "باحال بود", "خندیدم", "عالی بود",
        "خوب بود", "😂", "🤣", "خخخ", "ههه"
    )

    message = incoming_message.lower()

    if not any(word in message for word in positive_reactions):
        return False

    # پیدا کردن آخرین پیام واقعی ارسال‌شده توسط خودمان
    my_message_index = None

    for index in range(len(history) - 1, -1, -1):
        if history[index].get("sender") == "me":
            my_message_index = index
            break

    if my_message_index is None:
        return False

    # بررسی اینکه قبل از پیام ما درخواست شوخی وجود داشته یا نه
    previous_messages = history[:my_message_index]

    requested_humor = any(
        any(word in item.get("text", "").lower()
            for word in ("جوک", "شوخی", "بخندیم"))
        for item in previous_messages
        if item.get("sender") == "partner"
    )

    if not requested_humor:
        return False

    observations = _load_behavior_observations(chat_id)

    seen_id = history[my_message_index].get("message_id")

    if seen_id in observations["seen"]:
        return False

    observations["seen"].append(seen_id)
    observations["humor_positive"] += 1

    _save_behavior_observations(chat_id, observations)

    print(
        f"[+] Behavioral observation: "
        f"positive humor ({observations['humor_positive']}/3)"
    )

    if observations["humor_positive"] >= 3:
        add_learned_preference(
            chat_id,
            "humor",
            "مخاطب به شوخی و جوک واکنش مثبت نشان می‌دهد.",
            source="behavior_observation"
        )

        observations["humor_positive"] = 0
        _save_behavior_observations(chat_id, observations)

        print("[+] Learned new behavioral preference!")

    return True

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

    message = re.sub(
        r"\s+",
        " ",
        message
    )

    rules = [

        # ---------------------------------
        # MESSAGE LENGTH
        # ---------------------------------

        (
            r"(?:کوتاه(?:تر)?|مختصرتر)\s+(?:جواب بده|پاسخ بده|حرف بزن)",
            "message_length",
            "مخاطب پاسخ‌های کوتاه و مختصر را ترجیح می‌دهد."
        ),

        (
            r"(?:مفصل(?:تر)?|با جزئیات بیشتر)\s+(?:جواب بده|پاسخ بده|توضیح بده)",
            "message_length",
            "مخاطب پاسخ‌های مفصل و دارای جزئیات را ترجیح می‌دهد."
        ),

        # ---------------------------------
        # EMOJI
        # ---------------------------------

        (
            r"(?:ایموجی|شکلک)\s+(?:نذار|استفاده نکن|نفرست)",
            "emoji_usage",
            "مخاطب پاسخ بدون ایموجی را ترجیح می‌دهد."
        ),

        (
            r"(?:ایموجی|شکلک)\s+(?:بذار|استفاده کن|بفرست)",
            "emoji_usage",
            "مخاطب استفاده از ایموجی را ترجیح می‌دهد."
        ),

        # ---------------------------------
        # TONE
        # ---------------------------------

        (
            r"(?:رسمی(?:تر)?|مودبانه‌تر)\s+(?:حرف بزن|جواب بده|پاسخ بده)",
            "tone",
            "مخاطب لحن رسمی‌تر را ترجیح می‌دهد."
        ),

        (
            r"(?:خودمونی‌تر|صمیمی‌تر|راحت‌تر)\s+(?:حرف بزن|جواب بده|پاسخ بده)",
            "tone",
            "مخاطب لحن خودمانی و صمیمی را ترجیح می‌دهد."
        ),

        # ---------------------------------
        # REPETITION
        # ---------------------------------

        (
            r"(?:تکرار نکن|اینقدر تکرار نکن|حرف(?:‌| )تکراری نزن)",
            "conversation_style",
            "مخاطب از تکرار عبارت‌ها و پاسخ‌های قبلی خوشش نمی‌آید."
        ),

        # ---------------------------------
        # LANGUAGE
        # ---------------------------------

        (
            r"(?:فارسی\s+(?:جواب بده|حرف بزن)|به فارسی صحبت کن)",
            "language",
            "مخاطب پاسخ فارسی را ترجیح می‌دهد."
        ),

        # ---------------------------------
        # ADDRESSING
        # ---------------------------------

        (
            r"(?:منو|من را)\s+با\s+(.+?)\s+(?:صدا نکن|خطاب نکن)",
            "addressing",
            None
        ),

        # ---------------------------------
        # HUMOR
        # ---------------------------------

        (
            r"(?:وقتی\s+.+?،?\s*)?(?:شوخی نکن|کمتر شوخی کن|جدی‌تر باش)",
            "humor",
            "مخاطب هنگام ناراحتی یا در مکالمه جدی، شوخی کمتر و لحن جدی را ترجیح می‌دهد."
        ),

        (
            r"(?:بیشتر شوخی کن|شوخ(?:‌| )طبع‌تر باش)",
            "humor",
            "مخاطب لحن شوخ‌طبعانه‌تری را ترجیح می‌دهد."
        )

    ]

    # ابتدا بررسی بازخورد مستقیم
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

    # سپس بررسی رفتار مخاطب
    return learn_from_behavior(
        message,
        history,
        chat_id
    )
