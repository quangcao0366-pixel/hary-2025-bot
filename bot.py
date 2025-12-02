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
    await update.message.reply_text(f"Chọn hành động của bạn 选择\n\n{user.first_name}", reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    user_id = str(user.id)
    username = user.first_name + (f" {user.last_name}" if user.last_name else "")
    now = datetime.now(vietnam_tz)
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")

    if user_id not in data:
        data[user_id] = {"name": username, "ongoing": None, "actions": {}, "overtimes": []}
    data[user_id]["name"] = username

    # Xử lý "Đã quay lại"
    if text == "Đã quay lại / 回来了":
        extra = ""
        if data[user_id]["ongoing"]:
            start_time = datetime.fromisoformat(data[user_id]["ongoing"]["time"])
            minutes_used = int((now - start_time).total_seconds() / 60)
            action = data[user_id]["ongoing"]["action"]
            limit = TIME_LIMIT.get(action, 15)

            if action not in data[user_id]["actions"]:
                data[user_id]["actions"][action] = {"today": 0, "total": 0}
            data[user_id]["actions"][action]["today"] += 1
            data[user_id]["actions"][action]["total"] += 1

            if minutes_used > limit:
                over = minutes_used - limit
                data[user_id]["overtimes"].append({"action": action, "over": over, "date": date_str})
                extra = f"\nQuá giờ {over} phút!"
            data[user_id]["ongoing"] = None
        save_data(data)

        await update.message.reply_text(
            f"{username}\n🕐 {time_str} → {text}\n\nThành Công / 成功",
            reply_markup=reply_markup
        )
        return

    # Các nút đi ra
    if text in TIME_LIMIT:
        data[user_id]["ongoing"] = {"action": text, "time": now.isoformat()}
        save_data(data)
        await update.message.reply_text(
            f"{username}\n🕐 {time_str} → {text}\n\nThành Công / 成功",
            reply_markup=reply_markup
        )
        return

    if text == "/thongke":
        await thongke_command(update, context)
    elif text == "/qua":
        await qua_command(update, context)

async def thongke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(vietnam_tz).strftime("%Y-%m-%d")
    lines = [f"Thống kê chi tiết hôm nay ({today[8:10]}/{today[5:7]}/{today[:4]})\n"]
    total_today = 0
    for user_id, info in data.items():
        name = info["name"]
        lines.append(f"{name}")
        user_today = 0
        for action, counts in info["actions"].items():
            today_c = counts.get("today", 0)
            total_c = counts.get("total", 0)
            lines.append(f"   {action} → {today_c} lần (tổng {total_c})")
            user_today += today_c
        lines.append(f"   → Tổng hôm nay: {user_today} lần\n")
        total_today += user_today
    lines.append(f"TỔNG CỘNG: {total_today} lần")
    await update.message.reply_text("\n".join(lines) if data else "Chưa có dữ liệu")

async def qua_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(vietnam_tz).strftime("%Y-%m-%d")
    lines = [f"Cảnh báo quá giờ hôm nay ({today[8:10]}/{today[5:7]})\n"]
    has = False
    for user_id, info in data.items():
        name = info["name"]
        temp = []
        if info.get("ongoing"):
            start = datetime.fromisoformat(info["ongoing"]["time"])
            mins = int((datetime.now(vietnam_tz) - start).total_seconds() / 60)
            limit = TIME_LIMIT.get(info["ongoing"]["action"], 15)
            if mins > limit:
                temp.append(f"   {info['ongoing']['action']} → quá {mins - limit} phút (đang đi)")

        over_today = [o for o in info.get("overtimes", []) if o["date"] == today]
        for o in set([o["action"] for o in over_today]):
            count = len([x for x in over_today if x["action"] == o])
            temp.append(f"   {o} → quá giờ {count} lần")

        if temp:
            has = True
            lines.append(f"{name}")
            lines.extend(temp)
            lines.append("")

    if not has:
        lines.append("Hôm nay mọi người đều đúng giờ!")
    await update.message.reply_text("\n".join(lines))

def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("thongke", thongke_command))
    app.add_handler(CommandHandler("qua", qua_command))
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
