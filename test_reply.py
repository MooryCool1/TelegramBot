
from ai_engine import generate_reply

conversation = [
    {
        "sender": "partner",
        "text": "امروز خیلی دلم برات تنگ شده"
    },
    {
        "sender": "me",
        "text": "منم دلم برات تنگ شده جان"
    },
    {
        "sender": "partner",
        "text": "پس کی میای ببینمت؟"
    }
]

new_message = "پس منتظرتم"

reply = generate_reply(
    incoming_message=new_message,
    conversation_context=conversation
)

print("\n[+] Suggested Reply:")
print(reply)
