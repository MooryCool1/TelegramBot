
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "user",
            "content": "سلام! خودت رو به فارسی معرفی کن و بگو چه کارهایی می‌تونی انجام بدی."
        }
    ]
)

print(response.choices[0].message.content)
