
# TERMEZ SUPER BOTI - MVP struktura
# Mijoz / Do'konchi / Kuryer / Usta / Admin
# To'lov: Click / Payme / Naqd
# Shahar: Termez + yaqin tumanlar

import os, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "BOT_TOKENINGIZNI_SHU_YERGA_QOYING")

# ---------- ASOSIY MENYU ----------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 Ovqat buyurtma", callback_data="cat_ovqat")],
        [InlineKeyboardButton("🛒 Bozor / Do'kon", callback_data="cat_bozor")],
        [InlineKeyboardButton("💊 Dorixona", callback_data="cat_dorixona")],
        [InlineKeyboardButton("🛠 Xizmatlar / Usta", callback_data="cat_xizmat")],
        [InlineKeyboardButton("🚕 Taksi", callback_data="cat_taksi")],
        [InlineKeyboardButton("📢 E'lonlar bozori", callback_data="cat_elon")],
        [InlineKeyboardButton("📦 Buyurtmalarim", callback_data="my_orders")],
        [InlineKeyboardButton("👤 Kabinet / Ro'yxatdan o'tish", callback_data="cabinet")],
    ])

def role_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 Mijozman", callback_data="role_mijoz")],
        [InlineKeyboardButton("🏪 Do'konchi / Kafe egasiman", callback_data="role_dokon")],
        [InlineKeyboardButton("🛵 Kuryerman", callback_data="role_kuryer")],
        [InlineKeyboardButton("🔧 Ustaman", callback_data="role_usta")],
    ])

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n<b>TERMEZ SUPER BOTI</b> ga xush kelibsiz.\n\nTermezda ovqat, bozor, dorixona, taksi, usta va e'lonlar — hammasi bitta joyda.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await update.message.reply_text(
        "Avval rolingizni tanlang:",
        reply_markup=role_menu()
    )

# ---------- KATEGORIYALAR ----------
CATEGORIES = {
    "cat_ovqat": ["🍕 Fast-food", "🍜 Milliy taomlar", "🍰 Shirinlik / Qandolat", "☕ Kofe / Ichimlik"],
    "cat_bozor": ["🥩 Go'sht / Oziq-ovqat", "👕 Kiyim", "🏠 Uy-ro'zg'or", "🔨 Qurilish mollari"],
    "cat_dorixona": ["💊 Dori qidirish", "🧴 Gigiyena", "👶 Bolalar uchun"],
    "cat_xizmat": ["🔌 Elektrik", "🚿 Santexnik", "❄️ Konditsionerchi", "💇‍♂️ Sartarosh / Go'zallik", "🚗 Avtoservis / Moyka"],
    "cat_taksi": ["🚕 Shahar ichi", "🛣 Tumanlararo: Denov, Boysun, Sherobod, Qumqo'rg'on"],
    "cat_elon": ["🏠 Uy-joy ijara", "💼 Ish e'lonlari", "📱 Oldi-sotdi"],
}

async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cat = q.data
    items = CATEGORIES.get(cat, [])
    kb = [[InlineKeyboardButton(x, callback_data=f"sub_{x}")] for x in items]
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")])
    await q.edit_message_text(f"Bo'limni tanlang:", reply_markup=InlineKeyboardMarkup(kb))

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Asosiy menyu:", reply_markup=main_menu())

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Mijoz lokatsiya yuborganda - yetkazib berish narxini hisoblash uchun
    loc = update.message.location
    await update.message.reply_text(
        f"📍 Joylashuvingiz qabul qilindi: {loc.latitude}, {loc.longitude}\n\nEndi buyurtmani tanlang, yetkazib berish narxi masofaga qarab hisoblanadi:\n1-2 km - 10 000 so'm\n2-5 km - 15 000 so'm\n5 km dan ortiq - kelishilgan narx",
        reply_markup=main_menu()
    )



# ============================================================
# 1-BOSQICH: DO'KONCHI PANELI
# ============================================================
# Do'konchi: ro'yxatdan o'tadi -> do'konini qo'shadi -> tovar qo'shadi -> buyurtma qabul qiladi
# Ma'lumotlar hozircha xotirada (dict). Keyin admin panel + bazaga ulanadi.

DOKONCHILAR = {}  # user_id -> {dokon_nomi, kategoriya, telefon, manzil, stir, tasdiqlandi}
TOVARLAR = {}      # tovar_id -> {dokon_id, nomi, narxi, rasm, mavjud}
BUYURTMALAR = {}   # buyurtma_id -> {mijoz_id, dokon_id, tovarlar, holat}
TOVAR_ID = [0]
BUYURTMA_ID = [0]

def dokonchi_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Do'konni ro'yxatdan o'tkazish", callback_data="dokon_reg")],
        [InlineKeyboardButton("➕ Tovar qo'shish", callback_data="dokon_add")],
        [InlineKeyboardButton("📦 Mening tovarlarim", callback_data="dokon_my_products")],
        [InlineKeyboardButton("🧾 Yangi buyurtmalar", callback_data="dokon_orders_new")],
        [InlineKeyboardButton("📊 Bugungi savdo", callback_data="dokon_stats")],
        [InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="back_main")],
    ])

def dokon_kategoriya_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 Ovqat / Kafe", callback_data="dokon_cat_Ovqat")],
        [InlineKeyboardButton("🛒 Oziq-ovqat do'koni", callback_data="dokon_cat_Oziq-ovqat")],
        [InlineKeyboardButton("👕 Kiyim do'koni", callback_data="dokon_cat_Kiyim")],
        [InlineKeyboardButton("💊 Dorixona", callback_data="dokon_cat_Dorixona")],
        [InlineKeyboardButton("🏠 Uy-ro'zg'or / Qurilish", callback_data="dokon_cat_Uy-rozgor")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="role_dokon")],
    ])

async def dokon_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid in DOKONCHILAR:
        d = DOKONCHILAR[uid]
        await q.edit_message_text(
            f"🏪 <b>{d['dokon_nomi']}</b>\nKategoriya: {d['kategoriya']}\nTelefon: {d['telefon']}\nHolat: {'✅ Tasdiqlangan' if d.get('tasdiqlandi') else '⏳ Tasdiqlanmoqda'}",
            parse_mode="HTML", reply_markup=dokonchi_menu()
        )
    else:
        await q.edit_message_text(
            "🏪 <b>Do'konchi paneli</b>\n\nAvval do'koningizni ro'yxatdan o'tkazing.\n\nKerak: Do'kon nomi, Kategoriya, Telefon, Manzil, STIR / Guvohnoma",
            parse_mode="HTML", reply_markup=dokonchi_menu()
        )

async def dokon_reg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["dokon_reg_step"] = "nomi"
    await q.edit_message_text(
        "📝 <b>Ro'yxatdan o'tish</b>\n\n1-qadam: Do'kon nomini yozing.\nMasalan: <i>Termez Osh Markazi</i>",
        parse_mode="HTML"
    )

async def dokon_reg_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Oddiy bosqichma-bosqich ro'yxat: nomi -> telefon -> manzil -> STIR
    step = context.user_data.get("dokon_reg_step")
    if not step:
        return
    uid = update.message.from_user.id
    text = update.message.text.strip()
    if step == "nomi":
        context.user_data["dokon_nomi"] = text
        context.user_data["dokon_reg_step"] = "telefon"
        await update.message.reply_text("2-qadam: Telefon raqamingizni yozing.\nMasalan: +998 90 123 45 67")
    elif step == "telefon":
        context.user_data["dokon_telefon"] = text
        context.user_data["dokon_reg_step"] = "manzil"
        # Lokatsiya tugmasi
        kb = ReplyKeyboardMarkup([[KeyboardButton("📍 Joylashuvni yuborish", request_location=True)]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("3-qadam: Do'kon manzili yoki 📍 Joylashuv tugmasini bosing.", reply_markup=kb)
    elif step == "manzil":
        context.user_data["dokon_manzil"] = text
        context.user_data["dokon_reg_step"] = "stir"
        await update.message.reply_text("4-qadam: STIR / Guvohnoma raqamini yozing.\nAgar yo'q bo'lsa - 'yo'q' deb yozing.")
    elif step == "stir":
        context.user_data["dokon_stir"] = text
        # Saqlash
        DOKONCHILAR[uid] = {
            "dokon_nomi": context.user_data.get("dokon_nomi"),
            "kategoriya": context.user_data.get("dokon_kategoriya", "Ovqat"),
            "telefon": context.user_data.get("dokon_telefon"),
            "manzil": context.user_data.get("dokon_manzil"),
            "stir": text,
            "tasdiqlandi": False,
        }
        context.user_data["dokon_reg_step"] = None
        await update.message.reply_text(
            f"✅ Arizangiz qabul qilindi!\n\n🏪 {context.user_data.get('dokon_nomi')}\n📞 {context.user_data.get('dokon_telefon')}\n📍 {context.user_data.get('dokon_manzil')}\n\nAdmin tasdiqlagach tovar qo'sha olasiz. Hozircha test rejimida tovar qo'shish ochiq.",
            reply_markup=dokonchi_menu()
        )

async def dokon_cat_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cat = q.data.replace("dokon_cat_", "")
    context.user_data["dokon_kategoriya"] = cat
    await q.edit_message_text(f"Kategoriya tanlandi: <b>{cat}</b>\n\nEndi ro'yxatdan o'tishni boshlang:", parse_mode="HTML", reply_markup=dokonchi_menu())

async def dokon_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["add_step"] = "nomi"
    await q.edit_message_text(
        "➕ <b>Tovar qo'shish</b>\n\n1-qadam: Tovar nomini yozing.\nMasalan: <i>Lag'mon</i> yoki <i>Ko'ylak</i>",
        parse_mode="HTML"
    )

async def dokon_add_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("add_step")
    if not step:
        return
    uid = update.message.from_user.id
    text = (update.message.text or "").strip()
    if step == "nomi":
        context.user_data["tovar_nomi"] = text
        context.user_data["add_step"] = "narxi"
        await update.message.reply_text("2-qadam: Narxini yozing (faqat raqam). Masalan: 35000")
    elif step == "narxi":
        try:
            narx = int(text.replace(" ", "").replace(",", ""))
        except:
            await update.message.reply_text("Narxni faqat raqam bilan yozing. Masalan: 35000")
            return
        TOVAR_ID[0] += 1
        tid = TOVAR_ID[0]
        TOVARLAR[tid] = {"dokon_id": uid, "nomi": context.user_data.get("tovar_nomi"), "narxi": narx, "mavjud": True}
        context.user_data["add_step"] = None
        await update.message.reply_text(
            f"✅ Tovar qo'shildi!\n\n{context.user_data.get('tovar_nomi')} - {narx:,} so'm\nID: {tid}",
            reply_markup=dokonchi_menu()
        )

async def dokon_my_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    my = [(k, v) for k, v in TOVARLAR.items() if v["dokon_id"] == uid]
    if not my:
        await q.edit_message_text("Hozircha tovaringiz yo'q. ➕ Tovar qo'shish ni bosing.", reply_markup=dokonchi_menu())
        return
    txt = "📦 <b>Mening tovarlarim:</b>\n\n" + "\n".join([f"{k}. {v['nomi']} - {v['narxi']:,} so'm" for k, v in my])
    await q.edit_message_text(txt, parse_mode="HTML", reply_markup=dokonchi_menu())

async def dokon_orders_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    my = [(k, v) for k, v in BUYURTMALAR.items() if v["dokon_id"] == uid and v["holat"] == "yangi"]
    if not my:
        await q.edit_message_text("🧾 Yangi buyurtma yo'q.", reply_markup=dokonchi_menu())
        return
    kb = []
    txt = "🧾 <b>Yangi buyurtmalar:</b>\n\n"
    for k, v in my:
        txt += f"#{k} - {v.get('tovarlar','')} - {v.get('summa',0):,} so'm\n"
        kb.append([InlineKeyboardButton(f"✅ Qabul qilish #{k}", callback_data=f"order_accept_{k}"),
                   InlineKeyboardButton(f"❌ Rad etish #{k}", callback_data=f"order_reject_{k}")])
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="role_dokon")])
    await q.edit_message_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

async def dokon_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    parts = q.data.split("_")  # order_accept_1
    action = parts[1]
    oid = int(parts[2])
    if oid in BUYURTMALAR:
        BUYURTMALAR[oid]["holat"] = "qabul_qilindi" if action == "accept" else "rad_etildi"
        await q.edit_message_text(f"Buyurtma #{oid} - {'✅ Qabul qilindi, kuryerga yuborildi' if action=='accept' else '❌ Rad etildi'}", reply_markup=dokonchi_menu())

async def dokon_stats_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    my_orders = [v for v in BUYURTMALAR.values() if v["dokon_id"] == uid]
    total = sum([v.get("summa", 0) for v in my_orders if v["holat"] == "qabul_qilindi"])
    await q.edit_message_text(f"📊 <b>Bugungi savdo</b>\n\nBuyurtmalar: {len(my_orders)} ta\nJami: {total:,} so'm", parse_mode="HTML", reply_markup=dokonchi_menu())



# ---------- RENDER BEPUL WEB SERVICE UCHUN - WEBHOOK ----------
# Background Worker pullik, Web Service bepul.
# Web Service da polling ishlamaydi, webhook ishlaydi.
# Render Environment ga 2 ta narsa qo'yiladi:
#   BOT_TOKEN = bot tokeni
#   WEBHOOK_URL = https://hurma-bot.onrender.com  <- Render dagi sizning URL ingiz, oxirida / yo'q

TOKEN = os.environ.get("BOT_TOKEN", TOKEN)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", os.environ.get("RENDER_EXTERNAL_URL", "")).rstrip("/")

def build_app():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_category, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(dokon_entry, pattern="^role_dokon$"))
    app.add_handler(CallbackQueryHandler(dokon_reg_start, pattern="^dokon_reg$"))
    app.add_handler(CallbackQueryHandler(dokon_cat_select, pattern="^dokon_cat_"))
    app.add_handler(CallbackQueryHandler(dokon_add_start, pattern="^dokon_add$"))
    app.add_handler(CallbackQueryHandler(dokon_my_products, pattern="^dokon_my_products$"))
    app.add_handler(CallbackQueryHandler(dokon_orders_new, pattern="^dokon_orders_new$"))
    app.add_handler(CallbackQueryHandler(dokon_order_action, pattern="^order_(accept|reject)_"))
    app.add_handler(CallbackQueryHandler(dokon_stats_show, pattern="^dokon_stats$"))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data.get("dokon_reg_step"):
            await dokon_reg_message(update, context)
        elif context.user_data.get("add_step"):
            await dokon_add_message(update, context)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    return app

def main():
    # Python 3.14 da get_event_loop() ishlamaydi, loop ni o'zimiz yaratamiz
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    app = build_app()
    port = int(os.environ.get("PORT", 10000))
    if WEBHOOK_URL:
        # Bepul Web Service - to'g'ri yo'l
        print(f"Webhook rejim: {WEBHOOK_URL}/{TOKEN}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
            drop_pending_updates=True,
        )
    else:
        # Kompyuterda test qilish uchun - WEBHOOK_URL bo'lmasa polling
        print("WEBHOOK_URL yo'q, kompyuterda polling bilan ishlayapti...")
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
