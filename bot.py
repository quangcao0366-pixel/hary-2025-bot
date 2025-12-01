import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot đang chạy 24/7 trên Render rồi nè!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Lỗi rồi:", exc_info=context.error)

def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.add_error_handler(error_handler)

    port = int(os.environ.get("PORT", 10000))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://hary-2025-bot.onrender.com/{TOKEN}"
    )

if __name__ == "__main__":
    main()
