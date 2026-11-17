
from reply_manager import (
    add_suggestion,
    show_pending,
    update_status
)

incoming = "امروز خیلی دلم برات تنگ شده"

reply = "منم دلم برات تنگ شده جان"

# ذخیره پاسخ پیشنهادی
result = add_suggestion(
    incoming_message=incoming,
    reply=reply
)

# نمایش پاسخ‌های منتظر بررسی
show_pending()

# تأیید پاسخ
if result:
    update_status(
        result["id"],
        "approved"
    )

# نمایش مجدد
print("\nFinal Queue:")
show_pending()
    