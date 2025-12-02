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

TIME_LIMIT = {
    "Đi ăn / 吃饭": 30,
    "Hút thuốc / 抽烟": 15,
    "Vệ sinh nặng / WC大": 15,
    "Vệ sinh nhẹ / WC小": 5,
}

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
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
    await update.message.reply_text(f"Chọn hành động của bạn 选择\n\n{user.first_name}", reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    user_id = str(user.id)
    username = f"{user.first_name}{' ' + user.last_name if user.last_name else ''}"
    now = datetime.now(vietnam_tz)
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")

    if user_id not in data:
        data[user_id] = {"name": username, "ongoing": None, "actions": {}, "overtimes": []}
    data[user_id]["name"] = username

    # Đã quay lại
    if text == "Đã quay lại / 回来了":
        if data[user_id]["ongoing"]:
            start = datetime.fromisoformat(data[user_id]["ongoing"]["time"])
            mins = int((now - start).total_seconds() / 60)
            action = data[user_id]["ongoing"]["action"]
            limit = TIME_LIMIT.get(action, 15)

            if action not in data[user_id]["actions"]:
                data[user_id]["actions"][action] = {"today": 0, "total": 0}
            data[user_id]["actions"][action]["today"] += 1
            data[user_id]["actions"][action]["total"] += 1

            if mins > limit:
                over = mins - limit
                data[user_id]["overtimes"].append({"action": action, "over": over, "date": date_str})

            data[user_id]["ongoing"] = None
        save_data(data)

        await update.message.reply_text(
            f"👤 {username}\n🕐 {time_str} → {text}",
            reply_markup=reply_markup
        )
        return

    # Các nút đi ra
    if text in TIME_LIMIT:
        data[user_id]["ongoing"] = {"action": text, "time": now.isoformat()}
        save_data(data)
        await update.message.reply_text(
            f"👤 {username}\n🕐 {time_str} → {text}",
            reply_markup=reply_markup
        )
        return

    if text == "/thongke":
        await thongke(update, context)
    elif text == "/qua":
        await qua(update, context)

async def thongke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(vietnam_tz).strftime("%d/%m")
    lines = [f"Thống kê hôm nay {today}\n"]
    total = 0
    for info in data.values():
        name = info["name"]
        lines.append(f"👤 {name}")
        day_count = 0
        for action, c in info.get("actions", {}).items():
            cnt = c.get("today", 0)
            lines.append(f"   {action} → {cnt} lần")
            day_count += cnt
        lines.append(f"   → Tổng: {day_count} lần\n")
        total += day_count
    lines.append(f"TỔNG CỘNG: {total} lần")
    await update.message.reply_text("\n".join(lines) if total > 0 else "Chưa có dữ liệu")

async def qua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["Cảnh báo quá giờ hôm nay\n"]
    has = False
    for info in data.values():
        if info.get("ongoing"):
            start = datetime.fromisoformat(info["ongoing"]["time"])
            mins = int((datetime.now(vietnam_tz) - start).total_seconds() / 60)
            limit = TIME_LIMIT.get(info["ongoing"]["action"], 15)
            if mins > limit:
                has = True
                lines.append(f"👤 {info['name']}")
                lines.append(f"   {info['ongoing']['action']} → quá {mins-limit} phút")
    await update.message.reply_text("\n".join(lines) if has else "Mọi người đều đúng giờ!")

def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("thongke", thongke))
    app.add_handler(CommandHandler("qua", qua))
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
