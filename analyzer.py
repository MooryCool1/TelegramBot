
import os
import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "openai/gpt-oss-120b"

def analyze_personality():

    if not API_KEY:
        print("[-] GROQ_API_KEY is missing in .env")
        return

    if not os.path.exists("data/chat_history.json"):
        print("[-] Chat history not found!")
        return

    with open("data/chat_history.json", "r", encoding="utf-8") as file:
        messages = json.load(file)

    my_messages = [
        message["text"]
        for message in messages
        if message.get("sender") == "me" and message.get("text")
    ]

    if len(my_messages) < 20:
        print("[-] Not enough messages for analysis!")
        return

    my_messages = my_messages[-500:]

    chat_text = "\n".join(my_messages)
    chat_text = chat_text[-15000:]

    print(f"[+] Analyzing {len(my_messages)} of your messages...")
    print("[+] Sending only your messages to Groq...")

    client = Groq(api_key=API_KEY)

    prompt = f"""
You are a writing style analyzer.

Analyze ONLY the following messages written by one person.

Do not guess personality, mental health, identity, or private characteristics.
Focus only on observable writing habits.

Return a valid JSON object with these keys:

{{
    "language": "",
    "tone": "",
    "message_length": "",
    "emoji_usage": "",
    "humor_style": "",
    "affection_style": "",
    "writing_style": "",
    "common_expressions": [],
    "common_patterns": [],
    "reply_habits": "",
    "things_to_avoid": []
}}

Write the values in Persian.

Messages:

{chat_text}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        result = response.choices[0].message.content

        profile = json.loads(result)

        os.makedirs("data", exist_ok=True)

        with open(
            "data/personality_profile.json",
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                profile,
                file,
                ensure_ascii=False,
                indent=4
            )

        print("\n[+] Analysis completed successfully!")
        print("[+] Profile saved to data/personality_profile.json")

    except Exception as error:
        print("\n[-] Analysis failed:")
        print(error)


if __name__ == "__main__":
    analyze_personality()
