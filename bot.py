import logging
import os
import json
from datetime import datetime, timezone, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_TOKEN")

vietnam_tz = timezone(timedelta(hours=7))
DATA_FILE = "attendance.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

main_keyboard = [
    ["Đi ăn / 吃饭", "Hút thuốc / 抽烟"],
    ["Vệ sinh nặng / WC大", "Vệ sinh nhẹ / WC小"],
    ["Đã quay lại / 回来了"]
]
reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = f"Chọn hành động của bạn 选择\n\n{user.first_name}"
    await update.message.reply_text(welcome, reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    user_id = str(user.id)
    username = user.first_name + (f" {user.last_name}" if user.last_name else "")
    now = datetime.now(vietnam_tz)
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")

    valid_buttons = [
        "Đi ăn / 吃饭", "Hút thuốc / 抽烟",
        "Vệ sinh nặng / WC大", "Vệ sinh nhẹ / WC小",
        "Đã quay lại / 回来了"
    ]

    if text in valid_buttons:
        if user_id not in data:
            data[user_id] = {"name": username, "actions": {}}
        if text not in data[user_id]["actions"]:
            data[user_id]["actions"][text] = {"today": 0, "total": 0}
        
        if date_str not in data[user_id]["actions"][text]:
            data[user_id]["actions"][text]["today"] = 0
        
        data[user_id]["actions"][text]["today"] += 1
        data[user_id]["actions"][text]["total"] += 1
        data[user_id]["name"] = username
        save_data(data)

        response = (
            f"{username}\n"
            f"{time_str} → {text}\n\n"
            "Thành Công / 成功"
        )
        await update.message.reply_text(response, reply_markup=reply_markup)

    elif text == "/thongke":
        await thongke_command(update, context)
    else:
        await update.message.reply_text("Vui lòng chọn nút bên dưới", reply_markup=reply_markup)

async def thongke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data:
        await update.message.reply_text("Chưa có dữ liệu!")
        return

    today = datetime.now(vietnam_tz).strftime("%Y-%m-%d")
    lines = [f"Thống kê chấm công hôm nay ({today[:10]})\n"]

    total_today = 0
    for user_id, info in data.items():
        name = info["name"]
        lines.append(f"{name}")
        user_today = 0
        for action, count in info["actions"].items():
            today_count = count.get("today", 0)
            total_count = count.get("total", 0)
            lines.append(f"   {action} → {today_count} lần (tổng {total_count})")
            user_today += today_count
        lines.append(f"   → Tổng hôm nay: {user_today} lần\n")
        total_today += user_today

    lines.append(f"Tổng cộng mọi người hôm nay: {total_today} lần")
    await update.message.reply_text("\n".join(lines))

def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("thongke", thongke_command))
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
