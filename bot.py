import asyncio
from datetime import time
from telegram.ext import Application

TOKEN = "9229454847:AAEhknEgYb_fhfrN15y_4uoZaRq8RfVBfQA"
CHAT_ID = -1002069130276

async def send_reminder(context):
    text = (
        "⏰ Диққат, Hurma жамоаси!\n\n"
        "Соат 17:30 бўлди.\n"
        "Илтимос, барча БЎШ АРИЗАЛАРНИ ёпиб чиқинг.\n"
        "Очиқ қолган ариза қолмасин!\n\n"
        "✅ Ёпганингиздан сўнг шу ерда ✅ белгиси билан тасдиқланг."
    )
    await context.bot.send_message(chat_id=CHAT_ID, text=text)

async def main():
    app = Application.builder().token(TOKEN).build()
    app.job_queue.run_daily(send_reminder, time=time(hour=17, minute=30))
    print("Bot ishga tushdi...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())