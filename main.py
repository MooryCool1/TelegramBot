import asyncio

from telethon import events

from config import (
    TARGET_CHAT_ID,
    AUTO_REPLY,
    validate_config
)

from telegram_client import connect_telegram
from ai_engine import generate_reply
from user_profiles import (
    record_incoming_message,
    profile_analysis_is_due,
    analyze_user_profile,
    load_user_profile
)
from learning_engine import (
    learn_from_message,
    load_learned_preferences
)
from reply_manager import (
    add_suggestion,
    update_status
)


MAX_HISTORY = 10

# یک قفل مشترک برای جلوگیری از تداخل در نوشتن فایل صف پاسخ‌ها
processing_lock = asyncio.Lock()


def is_legacy_target(chat_id):
    """بررسی می‌کند آیا این چت همان چت قدیمی دارای حافظه مشترک است."""
    if not TARGET_CHAT_ID:
        return False

    try:
        return int(chat_id) == int(TARGET_CHAT_ID)
    except (TypeError, ValueError):
        return False


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
    # فعلاً فقط چت خصوصی افراد؛ پیام گروه‌ها در این مرحله پردازش نمی‌شود.
    if not event.is_private:
        return

    async with processing_lock:
        message = (event.raw_text or "").strip()

        if not message:
            print("[-] Empty or non-text message. Ignored.")
            return

        chat_id = event.chat_id
        is_old_target = is_legacy_target(chat_id)

        print("\n-----------------------------")
        print("[+] New incoming private message.")
        print(f"[+] Chat ID: {chat_id}")
        print(message)

        history = await get_chat_history(client, event)
        print(f"[+] Loaded {len(history)} previous messages.")

        # پروفایل ارتباطی مستقل برای هر چت
        display_name = ""
        username = ""
        try:
            sender = await event.get_sender()
            if sender:
                display_name = " ".join(
                    part for part in [
                        getattr(sender, "first_name", None),
                        getattr(sender, "last_name", None)
                    ] if part
                ).strip()
                username = getattr(sender, "username", None) or ""
        except Exception as error:
            print(f"[-] Could not read Telegram user details: {error}")

        user_profile_data = await asyncio.to_thread(
            record_incoming_message,
            chat_id,
            display_name,
            username
        )

        if profile_analysis_is_due(user_profile_data):
            print("[+] Updating this chat's personal profile...")
            await asyncio.to_thread(
                analyze_user_profile,
                chat_id,
                history,
                message
            )

        user_profile_data = await asyncio.to_thread(
            load_user_profile,
            chat_id
        ) or user_profile_data

        recipient_profile = {
            "telegram_display_name": user_profile_data.get("telegram", {}).get("display_name", ""),
            "telegram_username": user_profile_data.get("telegram", {}).get("username", ""),
            **user_profile_data.get("profile", {})
        }
        print(
            "[+] Personal profile loaded:",
            recipient_profile.get("communication_style", "unknown"),
            "| relationship:",
            recipient_profile.get("relationship_type", "unknown")
        )

        # حافظه و یادگیری قدیمی فقط برای TARGET_CHAT_ID اعمال می‌شود.
        # تا قبل از مرحله سوم، از اشتراک ترجیحات بین افراد جلوگیری می‌کنیم.
        if is_old_target:
            print("[+] Using the existing target chat learning.")
            print("[+] Checking for a behavioral preference to learn...")

            await asyncio.to_thread(
                learn_from_message,
                message,
                history
            )

            learned_preferences = await asyncio.to_thread(
                load_learned_preferences
            )
        else:
            print("[+] This is a new chat. Shared learned preferences are disabled.")
            learned_preferences = []

        print("[+] Generating reply...")

        reply = await asyncio.to_thread(
            generate_reply,
            message,
            history,
            learned_preferences,
            recipient_profile
        )

        if not reply:
            print("[-] No reply generated!")
            return

        print("\n[+] Suggested reply:")
        print(reply)

        result = add_suggestion(
            incoming_message=message,
            reply=reply,
            message_id=event.id,
            chat_id=chat_id,
            requires_human=not AUTO_REPLY
        )

        if not result:
            print("[-] Suggestion was not saved.")
            print("[-] Message will not be sent.")
            return

        print("[+] Reply suggestion saved.")

        # اگر ارسال خودکار خاموش باشد، فقط پیشنهاد ذخیره می‌شود.
        if not AUTO_REPLY:
            print("[+] Auto-send is disabled.")
            print("[+] Nothing was sent to Telegram.")
            return

        # این بخش برای مراحل بعد حفظ شده، اما در این مرحله قابل فعال‌سازی نیست.
        status_updated = update_status(result["id"], "sending")
        if not status_updated:
            print("[-] Could not update sending status.")
            return

        try:
            sent_message = await client.send_message(
                event.chat_id,
                reply,
                reply_to=event.id
            )

            update_status(result["id"], "sent")
            print("[+] Reply sent successfully!")
            print(f"[+] Telegram message ID: {sent_message.id}")

        except Exception as error:
            update_status(result["id"], "send_failed")
            print(f"[-] Telegram send error: {error}")


async def main():
    try:
        validate_config()
        print("[+] Configuration checked.")

        client = await connect_telegram()

        print("[+] Mooryane (موریانه) is connected.")
        print("[+] Listening to all incoming private chats.")
        print("[+] Group messages are ignored in Stage 1.")
        print("[+] Legacy shared learning remains limited to TARGET_CHAT_ID.")

        if AUTO_REPLY:
            print("[!] AUTO-REPLY IS ENABLED FOR ALL PRIVATE CHATS!")
            print("[!] AI-generated replies will be sent without manual review.")
        else:
            print("[+] Auto-send is disabled. Replies are suggestions only.")

        @client.on(events.NewMessage(incoming=True))
        async def message_handler(event):
            try:
                await process_message(client, event)
            except Exception as error:
                print(f"[-] Message processing error: {error}")

        print("[+] Waiting for messages...")
        await client.run_until_disconnected()

    except KeyboardInterrupt:
        print("\n[+] Program stopped by user.")

    except Exception as error:
        print(f"[-] Main error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
