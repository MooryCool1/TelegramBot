
import json
import os
import re
import uuid

from pathlib import Path


# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

BASE_DIR = Path(__file__).resolve().parent
USERS_DIR = BASE_DIR / "data" / "users"

MAX_MEMORIES = 80
MAX_CONTENT_LENGTH = 400


# -----------------------------------------
# FILE PATH
# -----------------------------------------

def get_memory_file(chat_id):

    user_dir = USERS_DIR / str(chat_id)

    user_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    return user_dir / "memory.json"


# -----------------------------------------
# LOAD MEMORY
# -----------------------------------------

def load_memory(chat_id):

    memory_file = get_memory_file(chat_id)

    if not memory_file.exists():
        return {
            "chat_id": str(chat_id),
            "memories": []
        }

    try:

        with open(
            memory_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Invalid memory format")

        memories = data.get("memories", [])

        if not isinstance(memories, list):
            memories = []

        return {
            "chat_id": str(chat_id),
            "memories": memories
        }

    except (
        OSError,
        json.JSONDecodeError,
        ValueError
    ):

        print(
            f"[-] Could not load memory for chat {chat_id}"
        )

        return {
            "chat_id": str(chat_id),
            "memories": []
        }


# -----------------------------------------
# SAVE MEMORY
# -----------------------------------------

def save_memory(chat_id, data):

    memory_file = get_memory_file(chat_id)

    temp_file = memory_file.with_suffix(".tmp")

    try:

        if not isinstance(data, dict):
            return False

        memories = data.get("memories", [])

        if not isinstance(memories, list):
            return False

        memories = memories[-MAX_MEMORIES:]

        save_data = {
            "chat_id": str(chat_id),
            "memories": memories
        }

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                save_data,
                file,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            temp_file,
            memory_file
        )

        return True

    except (OSError, TypeError, ValueError) as error:

        print("[-] Memory save error:", error)

        if temp_file.exists():
            temp_file.unlink()

        return False


# -----------------------------------------
# ADD MEMORY
# -----------------------------------------

def add_memory(
    chat_id,
    category,
    content,
    source="explicit"
):

    allowed_categories = {
        "preference",
        "interest",
        "important_event",
        "preferred_name"
    }

    if category not in allowed_categories:
        return False

    if not isinstance(content, str):
        return False

    content = content.strip()

    if not content:
        return False

    content = content[:MAX_CONTENT_LENGTH]

    data = load_memory(chat_id)

    memories = data["memories"]

    normalized_content = content.casefold()

    # جلوگیری از ذخیره اطلاعات تکراری
    for item in memories:

        if not isinstance(item, dict):
            continue

        old_content = str(
            item.get("content", "")
        ).strip().casefold()

        if (
            old_content == normalized_content
            and item.get("category") == category
        ):

            return True

    new_memory = {
        "id": uuid.uuid4().hex[:12],
        "category": category,
        "content": content,
        "source": source
    }

    memories.append(new_memory)

    data["memories"] = memories[-MAX_MEMORIES:]

    return save_memory(chat_id, data)


# -----------------------------------------
# EXPLICIT MEMORY LEARNING
# -----------------------------------------

def learn_explicit_memory(chat_id, message):

    if not isinstance(message, str):
        return False

    message = message.strip()

    if not message:
        return False

    if len(message) > 1000:
        return False

    patterns = [

        (
            r"^(?:یادت باشه|یادت بمونه|این رو به خاطر بسپار)\s*[:،]?\s*(.+)$",
            "preference"
        ),

        (
            r"^(?:از این به بعد)\s+(.+)$",
            "preference"
        ),

        (
            r"^(?:ترجیح میدم|ترجیح می‌دم|من ترجیح میدم|من ترجیح می‌دم)\s+(.+)$",
            "preference"
        ),

        (
            r"^(?:من به)\s+(.+?)\s+(?:علاقه دارم|علاقه‌مندم)$",
            "interest"
        ),

        (
            r"^(?:منو|من را)\s+(.+?)\s+(?:صدا کن|صدا بزن)$",
            "preferred_name"
        ),

        (
            r"^(?:اسمم رو|اسم من رو|نامم رو)\s+(.+?)\s+(?:صدا کن|صدا بزن)$",
            "preferred_name"
        ),

        (
            r"^(?:این موضوع رو یادت باشه)\s*[:،]?\s*(.+)$",
            "important_event"
        )

    ]

    for pattern, category in patterns:

        match = re.search(
            pattern,
            message,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        content = match.group(1).strip()

        if not content:
            return False

        result = add_memory(
            chat_id=chat_id,
            category=category,
            content=content,
            source="explicit"
        )

        if result:
            print(
                f"[+] Memory saved for chat {chat_id}"
            )

        return result

    return False


# -----------------------------------------
# REMOVE MEMORY
# -----------------------------------------

def remove_memory(chat_id, item_id):

    data = load_memory(chat_id)

    old_memories = data["memories"]

    new_memories = [
        item
        for item in old_memories
        if (
            isinstance(item, dict)
            and item.get("id") != item_id
        )
    ]

    if len(new_memories) == len(old_memories):
        return False

    data["memories"] = new_memories

    return save_memory(chat_id, data)


# -----------------------------------------
# CLEAR MEMORY
# -----------------------------------------

def clear_memory(chat_id):

    return save_memory(
        chat_id,
        {
            "chat_id": str(chat_id),
            "memories": []
        }
    )


# -----------------------------------------
# FORMAT MEMORY FOR AI
# -----------------------------------------

def format_memory_context(
    chat_id,
    max_chars=1800
):

    data = load_memory(chat_id)

    memories = data["memories"]

    if not memories:
        return ""

    category_names = {
        "preference": "ترجیحات",
        "interest": "علایق",
        "important_event": "موارد مهم",
        "preferred_name": "نحوه خطاب"
    }

    lines = []

    for item in memories:

        if not isinstance(item, dict):
            continue

        category = item.get("category")
        content = item.get("content")

        if not isinstance(content, str):
            continue

        category_name = category_names.get(
            category,
            "اطلاعات"
        )

        line = f"- {category_name}: {content}"

        lines.append(line)

    result = "\n".join(lines)

    return result[-max_chars:]
