import os

from telethon import TelegramClient

from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE
)


SESSION_DIR = "sessions"
SESSION_PATH = os.path.join(
    SESSION_DIR,
    "moory_session"
)


async def connect_telegram():
    os.makedirs(SESSION_DIR, exist_ok=True)

    client = TelegramClient(
        SESSION_PATH,
        int(TELEGRAM_API_ID),
        TELEGRAM_API_HASH
    )

    print("[+] Connecting to Telegram...")

    await client.start(
        phone=TELEGRAM_PHONE
    )

    if not await client.is_user_authorized():
        raise RuntimeError(
            "Telegram authorization failed."
        )

    me = await client.get_me()

    print("[+] Telegram connected!")
    print(f"[+] Logged in as: {me.first_name}")

    return client