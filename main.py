
import asyncio

from telethon import events

from config import (
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

from memory import (
    learn_explicit_memory,
    format_memory_context
)

from reply_manager import (
    add_suggestion,
    update_status
)


MAX_HISTORY = 10

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


async def process_message(client, event):

    if not event.is_private:
        return

    async with processing_lock:

        message = (
            event.raw_text or ""
        ).strip()

        if not message:

            print(
                "[-] Empty or non-text message. Ignored."
            )

            return

        chat_id = event.chat_id

        print("\n-----------------------------")
        print("[+] New incoming private message.")
        print(f"[+] Chat ID: {chat_id}")
        print(message)

        history = await get_chat_history(
            client,
            event
        )

        print(
            f"[+] Loaded {len(history)} previous messages."
        )

        # -------------------------------------
        # TELEGRAM USER INFORMATION
        # -------------------------------------

        display_name = ""
        username = ""

        try:

            sender = await event.get_sender()

            if sender:

                display_name = " ".join(
                    part
                    for part in [
                        getattr(sender, "first_name", None),
                        getattr(sender, "last_name", None)
                    ]
                    if part
                ).strip()

                username = (
                    getattr(sender, "username", None) or ""
                )

        except Exception as error:

            print(
                f"[-] Could not read Telegram user details: {error}"
            )

        # -------------------------------------
        # PERSONAL PROFILE
        # -------------------------------------

        user_profile_data = await asyncio.to_thread(
            record_incoming_message,
            chat_id,
            display_name,
            username
        )

        if profile_analysis_is_due(user_profile_data):

            print(
                "[+] Updating this chat's personal profile..."
            )

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
            "telegram_display_name": (
                user_profile_data.get("telegram", {}).get(
                    "display_name",
                    ""
                )
            ),

            "telegram_username": (
                user_profile_data.get("telegram", {}).get(
                    "username",
                    ""
                )
            ),

            **user_profile_data.get("profile", {})
        }

        print(
            "[+] Personal profile loaded:",
            recipient_profile.get(
                "communication_style",
                "unknown"
            ),
            "| relationship:",
            recipient_profile.get(
                "relationship_type",
                "unknown"
            )
        )

        # -------------------------------------
        # STAGE 3: EXPLICIT MEMORY
        # -------------------------------------

        print(
            "[+] Checking explicit personal memories..."
        )

        saved_memories = await asyncio.to_thread(
            learn_explicit_memory,
            chat_id,
            message
        )

        if saved_memories:
            print(
                f"[+] Explicit memories saved: {saved_memories}"
            )

        memory_context = await asyncio.to_thread(
            format_memory_context,
            chat_id
        )

        if memory_context:
            print(
                "[+] Personal memory loaded for this chat."
            )
        else:
            print(
                "[+] No personal memory found for this chat."
            )

        # -------------------------------------
        # STAGE 3: BEHAVIORAL LEARNING
        # -------------------------------------

        print(
            "[+] Checking for a behavioral preference to learn..."
        )

        await asyncio.to_thread(
            learn_from_message,
            message,
            history,
            chat_id
        )

        learned_preferences = await asyncio.to_thread(
            load_learned_preferences,
            chat_id
        )

        print(
            "[+] Personal learned preferences:",
            len(learned_preferences)
        )

        # -------------------------------------
        # GENERATE AI REPLY
        # -------------------------------------

        print(
            "[+] Generating reply..."
        )

        reply = await asyncio.to_thread(
            generate_reply,
            message,
            history,
            learned_preferences,
            recipient_profile,
            memory_context
        )

        if not reply:

            print(
                "[-] No reply generated!"
            )

            return

        print("\n[+] Suggested reply:")
        print(reply)

        # -------------------------------------
        # SAVE SUGGESTION
        # -------------------------------------

        result = add_suggestion(
            incoming_message=message,
            reply=reply,
            message_id=event.id,
            chat_id=chat_id,
            requires_human=not AUTO_REPLY
        )

        if not result:

            print(
                "[-] Suggestion was not saved."
            )

            print(
                "[-] Message will not be sent."
            )

            return

        print(
            "[+] Reply suggestion saved."
        )

        # -------------------------------------
        # AUTO REPLY
        # -------------------------------------

        if not AUTO_REPLY:

            print(
                "[+] Auto-send is disabled."
            )

            print(
                "[+] Nothing was sent to Telegram."
            )

            return

        status_updated = update_status(
            result["id"],
            "sending"
        )

        if not status_updated:

            print(
                "[-] Could not update sending status."
            )

            return

        try:

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

            print(
                "[+] Reply sent successfully!"
            )

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


async def main():

    try:

        validate_config()

        print(
            "[+] Configuration checked."
        )

        client = await connect_telegram()

        print(
            "[+] Mooryane (موریانه) is connected."
        )

        print(
            "[+] Listening to all incoming private chats."
        )

        print(
            "[+] Group messages are ignored."
        )

        print(
            "[+] Per-chat personal profiles are enabled."
        )

        print(
            "[+] Per-chat memory is enabled."
        )

        print(
            "[+] Per-chat behavioral learning is enabled."
        )

        if AUTO_REPLY:

            print(
                "[!] AUTO-REPLY IS ENABLED FOR ALL PRIVATE CHATS!"
            )

            print(
                "[!] AI-generated replies will be sent without manual review."
            )

        else:

            print(
                "[+] Auto-send is disabled. Replies are suggestions only."
            )

        @client.on(events.NewMessage(incoming=True))
        async def message_handler(event):

            try:

                await process_message(
                    client,
                    event
                )

            except Exception as error:

                print(
                    f"[-] Message processing error: {error}"
                )

        print(
            "[+] Waiting for messages..."
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


if __name__ == "__main__":

    asyncio.run(main())
