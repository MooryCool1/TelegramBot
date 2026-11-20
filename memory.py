# Conversation memory module
# Store and retrieve approved conversation context here.

import json
import os
import re
import tempfile
from datetime import datetime


DATA_DIR = "data"
USERS_DIR = os.path.join(DATA_DIR, "users")

MAX_MEMORIES = 80
MAX_CONTENT_LENGTH = 400

ALLOWED_CATEGORIES = {
    "preference",
    "interest",
    "important_event",
    "preferred_name"
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _memory_path(chat_id):
    user_dir = os.path.join(
        USERS_DIR,
        str(int(chat_id))
    )

    os.makedirs(user_dir, exist_ok=True)

    return os.path.join(user_dir, "memory.json")


def load_memory(chat_id):
    path = _memory_path(chat_id)

    if not os.path.exists(path):
        return {"memories": []}

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {"memories": []}

        if not isinstance(data.get("memories"), list):
            return {"memories": []}

        return data

    except (OSError, json.JSONDecodeError):
        return {"memories": []}


def save_memory(chat_id, data):
    path = _memory_path(chat_id)
    directory = os.path.dirname(path)

    fd, temp_path = tempfile.mkstemp(
        prefix="memory_",
        suffix=".tmp",
        dir=directory
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )

        os.replace(temp_path, path)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def add_memory(chat_id, category, content):
    if category not in ALLOWED_CATEGORIES:
        return False

    content = str(content).strip()

    if not content:
        return False

    content = content[:MAX_CONTENT_LENGTH]

    data = load_memory(chat_id)

    normalized = re.sub(
        r"\s+",
        " ",
        content
    ).casefold()

    for item in data["memories"]:

        old_content = re.sub(
            r"\s+",
            " ",
            str(item.get("content", ""))
        ).casefold()

        if (
            item.get("category") == category
            and old_content == normalized
        ):
            item["updated_at"] = _now()
            save_memory(chat_id, data)
            return True

    data["memories"].append({
        "id": f"{int(datetime.now().timestamp() * 1000)}",
        "category": category,
        "content": content,
        "created_at": _now(),
        "updated_at": _now()
    })

    data["memories"] = data["memories"][-MAX_MEMORIES:]

    save_memory(chat_id, data)

    return True


def learn_explicit_memory(chat_id, message):
    """
    ذخیره اطلاعاتی که کاربر به شکل واضح بیان کرده است.
    این تابع از API استفاده نمی‌کند.
    """

    text = str(message or "").strip()

    if not text:
        return 0

    saved = 0

    preference_phrases = (
        "یادت باشه",
        "یادت باشد",
        "از این به بعد",
        "ترجیح می‌دم",
        "ترجیح میدم",
        "ترجیح می دهم",
        "دوست دارم جواب"
    )

    if any(phrase in text for phrase in preference_phrases):

        if add_memory(
            chat_id,
            "preference",
            text
        ):
            saved += 1

    interest_match = re.search(
        r"(?:من\s+)?به\s+(.{2,120}?)\s+علاقه دارم[.!؟]?$",
        text
    )

    if interest_match:

        interest = interest_match.group(1).strip()

        if add_memory(
            chat_id,
            "interest",
            interest
        ):
            saved += 1

    name_match = re.search(
        r"(?:منو|من را)\s+(.{1,60}?)\s+(?:صدا کن|خطاب کن)",
        text
    )

    if name_match:

        preferred_name = name_match.group(1).strip()

        if add_memory(
            chat_id,
            "preferred_name",
            preferred_name
        ):
            saved += 1

    return saved


def remove_memory(chat_id, item_id):
    data = load_memory(chat_id)

    old_count = len(data["memories"])

    data["memories"] = [
        item
        for item in data["memories"]
        if item.get("id") != item_id
    ]

    if len(data["memories"]) != old_count:
        save_memory(chat_id, data)
        return True

    return False


def clear_memory(chat_id):
    save_memory(
        chat_id,
        {"memories": []}
    )


def format_memory_context(chat_id, max_chars=1800):
    data = load_memory(chat_id)

    if not data["memories"]:
        return ""

    labels = {
        "preference": "ترجیح",
        "interest": "علاقه",
        "important_event": "رویداد مهم",
        "preferred_name": "نام ترجیحی"
    }

    lines = []

    for item in data["memories"]:

        category = labels.get(
            item.get("category"),
            "یادداشت"
        )

        content = str(
            item.get("content", "")
        ).replace("\n", " ").strip()

        if content:
            lines.append(
                f"- {category}: {content}"
            )

    return "\n".join(lines)[:max_chars]
