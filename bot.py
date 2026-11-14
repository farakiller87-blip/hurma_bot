import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

def _run_server():
    port = int(os.environ.get("PORT", 10000))
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
        def log_message(self, *a): pass
    HTTPServer(("0.0.0.0", port), H).serve_forever()

threading.Thread(target=_run_server, daemon=True).start()

import asyncio
from datetime import time
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = -1002069130276

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Салом! Бот ишлаяпти ✅\nЭслатма ҳар куни 21:45 да келади.")

async def send_reminder(context):
    text = (
        "⏰ Диққат, Hurma жамоаси!\n\n"
        "Соат 21:45 бўлди.\n"
        "Илтимос, барча БЎШ АРИЗАЛАРНИ ёпиб чиқинг.\n"
        "Очиқ қолган ариза қолмасин!\n\n"
        "✅ Ёпганингиздан сўнг шу ерда ✅ белгиси билан тасдиқланг."
    )
    await context.bot.send_message(chat_id=CHAT_ID, text=text)

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.job_queue.run_daily(
        send_reminder,
        time=time(hour=17, minute=30, tzinfo=ZoneInfo("Asia/Tashkent"))
    )
    print("Bot ishga tushdi...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if "__name__" == "__main__":
    asyncio.run(main())
