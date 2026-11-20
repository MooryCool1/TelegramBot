
import asyncio

from telethon import events

from config import (
    AUTO_REPLY,
    validate_config
)

from telegram_client import connect_telegram
from ai_engine import generate_reply

from reply_manager import (
    add_suggestion,
    update_status
)

from memory import (
    learn_explicit_memory,
    format_memory_context
)

from learning_engine import (
    learn_from_message,
    load_learned_preferences
)

from user_profiles import (
    record_incoming_message,
    profile_analysis_is_due,
    analyze_user_profile,
    load_user_profile
)


MAX_HISTORY = 10

# جلوگیری از پردازش هم‌زمان یک پیام در چند چت
processing_lock = asyncio.Lock()


# -----------------------------------------
# GET CHAT HISTORY
# -----------------------------------------

async def get_chat_history(client, event):

    history = []

    try:

        me = await client.get_me()

        messages = await client.get_messages(
            event.chat_id,
            limit=MAX_HISTORY + 1
        )

        messages = [
            message
            for message in messages
            if (
                message.id != event.id
                and message.message
                and message.message.strip()
            )
        ]

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

        print(
            f"[-] History loading error: {error}"
        )

        return []


# -----------------------------------------
# PROCESS MESSAGE
# -----------------------------------------

async def process_message(client, event):

    async with processing_lock:

        if not event.is_private:
            return

        message = (event.raw_text or "").strip()

        if not message:
            print("[-] Empty or non-text message. Ignored.")
            return

        chat_id = event.chat_id

        print("\n-----------------------------")
        print(f"[+] New message from chat: {chat_id}")
        print("[+] Incoming message:")
        print(message)

        # ---------------------------------
        # GET SENDER INFORMATION
        # ---------------------------------

        try:

            sender = await event.get_sender()

            display_name = (
                getattr(sender, "first_name", None)
                or getattr(sender, "title", None)
                or "Unknown"
            )

            username = getattr(
                sender,
                "username",
                None
            )

        except Exception:

            display_name = "Unknown"
            username = None

        # ---------------------------------
        # RECORD USER
        # ---------------------------------

        try:

            await asyncio.to_thread(
                record_incoming_message,
                chat_id,
                display_name,
                username
            )

        except Exception as error:

            print(
                f"[-] User profile recording error: {error}"
            )

        # ---------------------------------
        # GET CHAT HISTORY
        # ---------------------------------

        history = await get_chat_history(
            client,
            event
        )

        print(
            f"[+] Loaded {len(history)} previous messages."
        )

        # ---------------------------------
        # LOAD RECIPIENT PROFILE
        # ---------------------------------

        recipient_profile = {}

        try:

            recipient_profile = await asyncio.to_thread(
                load_user_profile,
                chat_id
            )

            if not isinstance(recipient_profile, dict):
                recipient_profile = {}

        except Exception as error:

            print(
                f"[-] Recipient profile loading error: {error}"
            )

        # ---------------------------------
        # UPDATE RECIPIENT PROFILE
        # ---------------------------------

        try:

            profile_due = await asyncio.to_thread(
                profile_analysis_is_due,
                recipient_profile
            )

            if profile_due:

                print(
                    "[+] Recipient profile analysis is due."
                )

                await asyncio.to_thread(
                    analyze_user_profile,
                    chat_id,
                    history,
                    message
                )

                recipient_profile = await asyncio.to_thread(
                    load_user_profile,
                    chat_id
                )

                if not isinstance(recipient_profile, dict):
                    recipient_profile = {}

        except Exception as error:

            print(
                f"[-] Profile analysis error: {error}"
            )

        # ---------------------------------
        # LEARN EXPLICIT MEMORY
        # ---------------------------------

        try:

            memory_saved = await asyncio.to_thread(
                learn_explicit_memory,
                chat_id,
                message
            )

            if memory_saved:
                print("[+] Explicit memory updated.")

        except Exception as error:

            print(
                f"[-] Memory learning error: {error}"
            )

        # ---------------------------------
        # LEARN BEHAVIORAL PREFERENCES
        # ---------------------------------

        try:

            await asyncio.to_thread(
                learn_from_message,
                message,
                history,
                chat_id
            )

        except Exception as error:

            print(
                f"[-] Behavioral learning error: {error}"
            )

        # ---------------------------------
        # LOAD CHAT-SPECIFIC DATA
        # ---------------------------------

        try:

            learned_preferences = await asyncio.to_thread(
                load_learned_preferences,
                chat_id
            )

        except Exception as error:

            print(
                f"[-] Preference loading error: {error}"
            )

            learned_preferences = []

        try:

            memory_context = await asyncio.to_thread(
                format_memory_context,
                chat_id
            )

        except Exception as error:

            print(
                f"[-] Memory context error: {error}"
            )

            memory_context = ""

        # ---------------------------------
        # GENERATE REPLY
        # ---------------------------------

        print("[+] Generating reply...")

        reply = await asyncio.to_thread(
            generate_reply,
            message,
            history,
            learned_preferences,
            recipient_profile,
            memory_context
        )

        if not reply:

            print("[-] No reply generated!")
            return

        print("\n[+] Suggested reply:")
        print(reply)

        # ---------------------------------
        # SAVE SUGGESTION
        # ---------------------------------

        requires_human = not AUTO_REPLY

        result = add_suggestion(
            incoming_message=message,
            reply=reply,
            message_id=event.id,
            requires_human=requires_human,
            chat_id=chat_id
        )

        if not result:

            print("[-] Suggestion was not saved.")
            print("[-] Message will not be sent.")
            return

        print("[+] Suggestion added to queue.")

        # ---------------------------------
        # AUTO REPLY CHECK
        # ---------------------------------

        if not AUTO_REPLY:

            print("[+] Auto-send is disabled.")
            print("[+] Nothing was sent to Telegram.")

            return

        # ---------------------------------
        # UPDATE STATUS
        # ---------------------------------

        status_updated = update_status(
            result["id"],
            "sending"
        )

        if not status_updated:

            print("[-] Could not update sending status.")
            return

        # ---------------------------------
        # SEND REPLY
        # ---------------------------------

        try:

            print("[+] Sending reply to Telegram...")

            input_chat = await event.get_input_chat()

            sent_message = await client.send_message(
                input_chat,
                reply,
                reply_to=event.id
            )

            update_status(
                result["id"],
                "sent"
            )

            print("[+] Reply sent successfully!")
            print(
                f"[+] Telegram message ID: {sent_message.id}"
            )

        except Exception as error:

            update_status(
                result["id"],
                "send_failed"
            )

            print(
                f"[-] Telegram send error: {error}"
            )

            print(
                "[-] Reply was not confirmed as sent."
            )


# -----------------------------------------
# MAIN
# -----------------------------------------

async def main():

    try:

        validate_config()

        print("[+] Configuration checked.")

        client = await connect_telegram()

        print("[+] Telegram connected!")
        print("[+] AI reply system is active.")

        if AUTO_REPLY:

            print("[!] AUTO-REPLY IS ENABLED!")
            print(
                "[!] Generated replies will be sent automatically."
            )

        else:

            print("[+] Auto-send is disabled.")
            print("[+] Replies will only be saved as suggestions.")

        print("[+] Monitoring all private chats...")
        print("[+] Waiting for messages...")

        @client.on(
            events.NewMessage(
                incoming=True
            )
        )
        async def message_handler(event):

            try:

                if not event.is_private:
                    return

                await process_message(
                    client,
                    event
                )

            except Exception as error:

                print(
                    f"[-] Message processing error: {error}"
                )

        await client.run_until_disconnected()

    except KeyboardInterrupt:

        print(
            "\n[+] Program stopped by user."
        )

    except Exception as error:

        print(
            f"[-] Main error: {error}"
        )


# -----------------------------------------
# ENTRY POINT
# -----------------------------------------

if __name__ == "__main__":

    asyncio.run(main())
