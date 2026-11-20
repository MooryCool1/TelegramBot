
import os
import json
import uuid

from datetime import datetime


DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "reply_queue.json")


def load_replies():

    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        return []

    try:

        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        print("[-] Invalid reply queue format!")
        return []

    except (json.JSONDecodeError, OSError) as error:

        print(f"[-] Could not load reply queue: {error}")
        return []


def save_replies(replies):

    os.makedirs(DATA_DIR, exist_ok=True)

    temp_file = DATA_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:

        json.dump(
            replies,
            file,
            ensure_ascii=False,
            indent=4
        )

    os.replace(temp_file, DATA_FILE)


def add_suggestion(
    incoming_message,
    reply,
    message_id=None,
    requires_human=True,
    chat_id=None
):

    if not reply or not reply.strip():
        print("[-] Empty reply!")
        return None

    replies = load_replies()

    # بررسی پیام تکراری با درنظرگرفتن مخاطب
    if message_id is not None:

        for item in replies:

            same_message = (
                str(item.get("message_id")) == str(message_id)
            )

            same_chat = (
                str(item.get("chat_id")) == str(chat_id)
            )

            if same_message and same_chat:
                print("[-] This Telegram message was already processed.")
                return None

    suggestion = {

        "id": str(uuid.uuid4())[:8],

        "chat_id": chat_id,
        "message_id": message_id,

        "incoming_message": incoming_message,
        "suggested_reply": reply,

        "requires_human": requires_human,

        "status": (
            "needs_review"
            if requires_human
            else "pending"
        ),

        "created_at": datetime.now().isoformat()
    }

    replies.append(suggestion)

    save_replies(replies)

    print("[+] Reply suggestion saved!")
    print(f"[+] Suggestion ID: {suggestion['id']}")

    return suggestion


def update_status(reply_id, new_status):

    allowed_statuses = (
        "approved",
        "rejected",
        "sending",
        "sent",
        "send_failed"
    )

    if new_status not in allowed_statuses:
        print("[-] Invalid status!")
        return False

    replies = load_replies()

    for item in replies:

        if item.get("id") == reply_id:

            item["status"] = new_status
            item["updated_at"] = datetime.now().isoformat()

            save_replies(replies)

            print(f"[+] Status updated: {new_status}")
            return True

    print("[-] Reply not found!")
    return False


def show_pending():

    replies = load_replies()

    pending = [
        item
        for item in replies
        if item.get("status") in (
            "pending",
            "needs_review"
        )
    ]

    if not pending:
        print("No pending replies.")
        return

    for item in pending:

        print("\n------------------------------")

        print("ID:", item.get("id"))
        print("Chat ID:", item.get("chat_id"))
        print("Incoming:", item.get("incoming_message"))
        print("Suggested:", item.get("suggested_reply"))
        print("Status:", item.get("status"))
