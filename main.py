
import asyncio

from telethon import events

from config import (
    TARGET_CHAT_ID,
    AUTO_REPLY,
    validate_config
)

from telegram_client import connect_telegram
from ai_engine import generate_reply
from reply_manager import (
    add_suggestion,
    update_status
)


MAX_HISTORY = 10

# جلوگیری از پردازش هم‌زمان چند پیام
processing_lock = asyncio.Lock()


async def get_chat_history(client, event):
    history = []

    try:
        me = await client.get_me()

        messages = await client.get_messages(
            event.chat_id,
            limit=MAX_HISTORY + 1
        )

        messages = [
            message for message in messages
            if message.id != event.id
            and message.message
            and message.message.strip()
        ]

        # ترتیب از قدیمی به جدید
        messages.reverse()

        for message in messages:
            sender = (
                "me"
                if message.sender_id == me.id
                else "partner"
            )

            history.append({
                "sender": sender,
                "text": message.message,
                "message_id": message.id
            })

        return history

    except Exception as error:
        print(f"[-] History loading error: {error}")
        return []


async def process_message(client, event):
    async with processing_lock:

        message = event.raw_text.strip()

        if not message:
            print("[-] Empty or non-text message. Ignored.")
            return

        print("\n-----------------------------")
        print("[+] New incoming message:")
        print(message)

        # دریافت تاریخچه مکالمه
        history = await get_chat_history(client, event)

        print(f"[+] Loaded {len(history)} previous messages.")
        print("[+] Generating reply...")

        # تولید پاسخ با Groq
        reply = await asyncio.to_thread(
            generate_reply,
            message,
            history
        )

        if not reply:
            print("[-] No reply generated!")
            return

        print("\n[+] Suggested reply:")
        print(reply)

        # اگر ارسال خودکار خاموش باشد، فقط پیشنهاد ذخیره می‌شود
        requires_human = not AUTO_REPLY

        result = add_suggestion(
            incoming_message=message,
            reply=reply,
            message_id=event.id,
            requires_human=requires_human
        )

        if not result:
            print("[-] Suggestion was not saved.")
            print("[-] Message will not be sent.")
            return

        print("[+] Suggestion added to queue.")

        # حالت فقط پیشنهاد
        if not AUTO_REPLY:
            print("[+] Auto-send is disabled.")
            print("[+] Nothing was sent to Telegram.")
            return

        # قبل از ارسال، وضعیت را ثبت می‌کنیم
        status_updated = update_status(
            result["id"],
            "sending"
        )

        if not status_updated:
            print("[-] Could not update sending status.")
            return

        try:
            print("[+] Sending reply to Telegram...")

            sent_message = await client.send_message(
                event.chat_id,
                reply,
                reply_to=event.id
            )

            update_status(
                result["id"],
                "sent"
            )

            print("[+] Reply sent successfully!")
            print(f"[+] Telegram message ID: {sent_message.id}")

        except Exception as error:
            update_status(
                result["id"],
                "send_failed"
            )

            print(f"[-] Telegram send error: {error}")
            print("[-] Reply was not confirmed as sent.")


async def main():
    try:
        validate_config()

        print("[+] Configuration checked.")

        client = await connect_telegram()

        chat_id = int(TARGET_CHAT_ID)

        entity = await client.get_entity(chat_id)

        print(
            "[+] Target chat:",
            getattr(entity, "first_name", "Selected chat")
        )

        print("[+] AI reply system is active.")

        if AUTO_REPLY:
            print("[!] AUTO-REPLY IS ENABLED!")
            print("[!] Generated replies will be sent automatically.")
        else:
            print("[+] Auto-send is disabled.")

        print("[+] Waiting for messages...")

        @client.on(
            events.NewMessage(
                chats=chat_id,
                incoming=True
            )
        )
        async def message_handler(event):
            try:
                await process_message(client, event)

            except Exception as error:
                print(f"[-] Message processing error: {error}")

        await client.run_until_disconnected()

    except KeyboardInterrupt:
        print("\n[+] Program stopped by user.")

    except Exception as error:
        print(f"[-] Main error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
