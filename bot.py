import logging
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")

# 5 nút đúng như ảnh bạn gửi
main_keyboard = [
    ["Đi ăn / 吃饭", "Hút thuốc / 抽烟"],
    ["Vệ sinh nặng / WC大", "Vệ sinh nhẹ / WC小"],
    ["Đã quay lại / 回来了"]
]
reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = f"Chọn hành động của bạn 选择\n\n👋 {user.first_name}"
    await update.message.reply_text(welcome, reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    now = datetime.now().strftime("%H:%M")

    # Danh sách các nút hợp lệ
    valid_buttons = [
        "Đi ăn / 吃饭", "Hút thuốc / 抽烟",
        "Vệ sinh nặng / WC大", "Vệ sinh nhẹ / WC小",
        "Đã quay lại / 回来了"
    ]

    if text in valid_buttons:
        # Hiển thị đúng như ảnh 2 của bạn
        response = (
            f"👤 {user.first_name} {user.last_name or ''}\n"
            f"🕐 {now} → {text}\n\n"
            "Đã ghi nhận thành công!"
        )
        await update.message.reply_text(response, reply_markup=reply_markup)
    else:
        # Nếu gửi tin nhắn thường thì nhắc lại menu
        await update.message.reply_text("Vui lòng chọn nút bên dưới 👇", reply_markup=reply_markup)

def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    port = int(os.environ.get("PORT", 10000))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://hary-2025-bot.onrender.com/{TOKEN}"
    )

if __name__ == "__main__":
    main()
