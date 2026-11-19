
import os
import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

HISTORY_FILE = "data/chat_history.json"
PROFILE_FILE = "data/personality_profile.json"
TEMP_FILE = "data/personality_profile.tmp"


def load_my_messages():

    if not os.path.exists(HISTORY_FILE):
        print("[-] Chat history not found!")
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            messages = json.load(file)

    except (json.JSONDecodeError, OSError) as error:
        print("[-] Could not read chat history:", error)
        return []

    if not isinstance(messages, list):
        print("[-] Invalid chat history format!")
        return []

    my_messages = []

    for message in messages:

        if not isinstance(message, dict):
            continue

        if message.get("sender") != "me":
            continue

        message_text = message.get("text")

        if isinstance(message_text, str) and message_text.strip():
            my_messages.append(message_text.strip())

    return my_messages


def create_prompt(chat_text, analysis_type):

    if analysis_type == "writing":

        return f"""
تو یک تحلیلگر حرفه‌ای سبک نوشتاری هستی.

پیام‌های زیر همگی توسط یک نفر نوشته شده‌اند.
فقط عادت‌های قابل مشاهده در نوشتار او را تحلیل کن.

هدف:
شناخت دقیق نحوه نوشتن این شخص برای تولید پاسخ‌هایی شبیه سبک واقعی او.

قوانین:
- هیچ ویژگی‌ای را بدون شواهد اختراع نکن.
- فقط از پیام‌های داده‌شده نتیجه بگیر.
- عبارت‌های پرتکرار واقعی را شناسایی کن.
- از حدس زدن شخصیت و ویژگی‌های خصوصی خودداری کن.
- مقادیر را کوتاه و فارسی بنویس.
- آرایه‌ها حداکثر ۵ مورد داشته باشند.
- JSON باید کامل و معتبر باشد.

ساختار خروجی:

{{
    "language": "",
    "tone": "",
    "message_length": "",
    "emoji_usage": "",
    "writing_style": "",
    "sentence_structure": "",
    "punctuation_style": "",
    "line_break_style": "",
    "common_expressions": [],
    "slang_patterns": [],
    "sentence_openings": [],
    "sentence_endings": [],
    "things_to_avoid": []
}}

پیام‌ها:

{chat_text}
"""

    return f"""
تو یک تحلیلگر رفتار مکالمه و سبک پاسخ‌گویی هستی.

پیام‌های زیر همگی توسط یک نفر نوشته شده‌اند.
فقط الگوهای قابل مشاهده در نحوه پاسخ دادن او را بررسی کن.

هدف:
شناخت اینکه این شخص در موقعیت‌های مختلف چگونه جواب می‌دهد.

قوانین:
- فقط از شواهد موجود در پیام‌ها استفاده کن.
- اگر الگویی مشخص نیست، آن را اختراع نکن.
- شوخی و محبت را از پاسخ‌های عادی جدا کن.
- عبارت‌های پرتکرار را به اجبار وارد پاسخ‌های آینده نکن.
- مقادیر کوتاه و فارسی باشند.
- آرایه‌ها حداکثر ۵ مورد داشته باشند.
- JSON باید کامل و معتبر باشد.

ساختار خروجی:

{{
    "humor_style": "",
    "affection_style": "",
    "affection_patterns": [],
    "humor_patterns": [],
    "normal_reply_patterns": [],
    "question_reply_patterns": [],
    "reply_habits": "",
    "conversation_rhythm": "",
    "variation_guidelines": []
}}

پیام‌ها:

{chat_text}
"""


def run_analysis(client, chat_text, analysis_type):

    prompt = create_prompt(chat_text, analysis_type)

    print(f"\n[+] Running {analysis_type} analysis...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_completion_tokens=700
    )

    choice = response.choices[0]

    if choice.finish_reason == "length":
        raise ValueError(
            f"{analysis_type} analysis reached token limit."
        )

    result = choice.message.content

    if not result:
        raise ValueError(
            f"{analysis_type} analysis returned an empty response."
        )

    profile = json.loads(result)

    if not isinstance(profile, dict):
        raise ValueError("AI returned an invalid JSON object.")

    print(f"[+] {analysis_type.capitalize()} analysis completed!")

    return profile


def validate_profile(profile):

    if not isinstance(profile, dict):
        return False

    required_fields = [
        "language",
        "tone",
        "message_length",
        "emoji_usage",
        "writing_style",
        "humor_style",
        "affection_style",
        "common_expressions",
        "reply_habits"
    ]

    for field in required_fields:

        if field not in profile:
            print(f"[-] Missing profile field: {field}")
            return False

    return True


def save_profile(profile):

    os.makedirs("data", exist_ok=True)

    try:

        with open(TEMP_FILE, "w", encoding="utf-8") as file:
            json.dump(
                profile,
                file,
                ensure_ascii=False,
                indent=4
            )

        # فقط بعد از ذخیره موفق، فایل قبلی جایگزین می‌شود
        os.replace(TEMP_FILE, PROFILE_FILE)

        return True

    except OSError as error:

        print("[-] Could not save profile:", error)

        if os.path.exists(TEMP_FILE):
            os.remove(TEMP_FILE)

        return False


def analyze_personality():

    if not API_KEY:
        print("[-] GROQ_API_KEY is missing in .env")
        return

    my_messages = load_my_messages()

    if len(my_messages) < 20:
        print("[-] Not enough messages for analysis!")
        print(f"[-] Found only {len(my_messages)} messages.")
        return

    # استفاده از حداکثر 500 پیام آخر خود شخص
    my_messages = my_messages[-500:]

    chat_text = "\n".join(my_messages)

    # محدود کردن حجم متن ارسالی
    chat_text = chat_text[-15000:]

    print(f"[+] Analyzing {len(my_messages)} of your messages...")
    print("[+] Only your messages will be analyzed.")
    print(f"[+] Using model: {MODEL}")

    client = Groq(api_key=API_KEY)

    try:

        # مرحله اول: تحلیل سبک نوشتار
        writing_profile = run_analysis(
            client,
            chat_text,
            "writing"
        )

        # مرحله دوم: تحلیل رفتار مکالمه
        conversation_profile = run_analysis(
            client,
            chat_text,
            "conversation"
        )

        # ترکیب نتایج دو تحلیل
        profile = {}

        profile.update(writing_profile)
        profile.update(conversation_profile)

        # بررسی کامل بودن پروفایل
        if not validate_profile(profile):
            print("[-] Profile validation failed!")
            return

        # ذخیره نهایی
        if not save_profile(profile):
            return

        print("\n[+] Analysis completed successfully!")
        print(f"[+] Profile saved to {PROFILE_FILE}")

        print("\n------------------------------")
        print("[+] Writing style:")
        print(profile.get("writing_style", "Not detected"))

        print("\n[+] Tone:")
        print(profile.get("tone", "Not detected"))

        print("\n[+] Common expressions:")

        expressions = profile.get("common_expressions", [])

        if expressions:
            for expression in expressions:
                print("-", expression)
        else:
            print("No expressions detected.")

        print("\n[+] Affection style:")
        print(profile.get("affection_style", "Not detected"))

        print("\n[+] Humor style:")
        print(profile.get("humor_style", "Not detected"))

        print("\n------------------------------")

    except json.JSONDecodeError:
        print("\n[-] AI returned invalid JSON!")

    except Exception as error:
        print("\n[-] Analysis failed:")
        print(error)


if __name__ == "__main__":
    analyze_personality()
