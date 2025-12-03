import logging, os, json
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

# ---------- LOAD / SAVE AN TOÀN ----------
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

data = load_data()

# ---------- KEYBOARD ----------
kb = ReplyKeyboardMarkup([
    ["Đi ăn / 吃饭", "Hút thuốc / 抽烟"],
    ["Vệ sinh nặng / WC大", "Vệ sinh nhẹ / WC小"],
    ["Đã quay lại / 回来了"]
], resize_keyboard=True)

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chọn hành động của bạn", reply_markup=kb)

# ---------- XỬ LÝ CHÍNH (chỉ lưu 1 lần duy nhất) ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    uid = str(user.id)
    name = f"{user.first_name}{' ' + user.last_name if user.last_name else ''}".strip()
    now = datetime.now(vietnam_tz)
    time_str = now.strftime("%H:%M")

    # Khởi tạo user
    if uid not in data:
        data[uid] = {"name": name, "ongoing": None, "actions": {}, "overtimes": []}
    data[uid]["name"] = name

    changed = False

    # QUAY LẠI
    if text == "Đã quay lại / 回来了" and data[uid].get("ongoing"):
        start_time = datetime.fromisoformat(data[uid]["ongoing"]["time"])
        mins = int((now - start_time).total_seconds() / 60)
        action = data[uid]["ongoing"]["action"]
        limit = TIME_LIMIT.get(action, 15)

        if action not in data[uid]["actions"]:
            data[uid]["actions"][action] = {"today": 0, "total": 0}
        data[uid]["actions"][action]["today"] += 1
        data[uid]["actions"][action]["total"] += 1

        if mins > limit:
            data[uid]["overtimes"].append({
                "action": action,
                "over": mins - limit,
                "date": now.strftime("%Y-%m-%d")
            })

        data[uid]["ongoing"] = None
        changed = True

    # ĐI RA
    elif text in TIME_LIMIT:
        data[uid]["ongoing"] = {"action": text, "time": now.isoformat()}
        changed = True

    # LƯU DUY NHẤT 1 LẦN Ở CUỐI → KHÔNG BAO GIỜ MẤT DỮ LIỆU
    if changed:
        save_data(data)

    # FORMAT ĐẸP ĐÚNG YÊU CẦU CUỐI CÙNG CỦA BẠN
    await update.message.reply_text(
        f"👤 {name}\n🕐 {time_str} → {text}\n\n🤖Thành Công / 成功 ✅",
        reply_markup=kb
    )

# ---------- THỐNG KÊ ----------
async def thongke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(vietnam_tz).strftime("%d/%m")
    lines = [f"Thống kê hôm nay {today}\n"]
    total = 0
    for v in data.values():
        name = v["name"]
        cnt = sum(c.get("today", 0) for c in v.get("actions", {}).values())
        if cnt > 0:
            lines.append(f"👤 {name} → {cnt} lần\n")
            total += cnt
    if total > 0:
        lines.append(f"TỔNG CỘNG: {total} lần")
    await update.message.reply_text("\n".join(lines) if total else "Chưa có dữ liệu hôm nay")

# ---------- QUÁ GIỜ ----------
async def qua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["Cảnh báo quá giờ hiện tại\n"]
    has = False
    now = datetime.now(vietnam_tz)
    for v in data.values():
        if v.get("ongoing"):
            mins = int((now - datetime.fromisoformat(v["ongoing"]["time"])).total_seconds() / 60)
            limit = TIME_LIMIT.get(v["ongoing"]["action"], 15)
            if mins > limit:
                has = True
                lines.append(f"👤 {v['name']}\n   {v['ongoing']['action']} → quá {mins-limit} phút\n")
    await update.message.reply_text("\n".join(lines) if has else "Mọi người đều đúng giờ!")

# ---------- MAIN ----------
def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("thongke", thongke))
    app.add_handler(CommandHandler("qua", qua))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    
    port = int(os.environ.get("PORT", 10000))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://hary-2025-bot.onrender.com/{TOKEN}"
    )

if __name__ == "__main__":
    main()
