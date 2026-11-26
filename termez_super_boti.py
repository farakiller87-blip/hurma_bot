
# TERMEZ SUPER BOTI - MVP struktura
# Mijoz / Do'konchi / Kuryer / Usta / Admin
# To'lov: Click / Payme / Naqd
# Shahar: Termez + yaqin tumanlar

import os, asyncio, threading, sqlite3, json, time
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ---------- BAZA: Postgres (asosiy) + SQLite (zaxira) ----------
# Render'da DATABASE_URL bo'lsa -> Postgres ishlaydi (deploy'da ham o'chmaydi)
# Kompyuterda DATABASE_URL yo'q bo'lsa -> termez.db (SQLite) ishlaydi
# Ma'lumotlar har 30 soniyada avtomatik saqlanadi.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "termez.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

def _db_data():
    return {
        "dokonchilar": {str(k): v for k, v in DOKONCHILAR.items()},
        "tovarlar": {str(k): v for k, v in TOVARLAR.items()},
        "buyurtmalar": {str(k): v for k, v in BUYURTMALAR.items()},
        "kuryerlar": {str(k): v for k, v in KURYERLAR.items()},
        "tovar_id": TOVAR_ID[0],
        "buyurtma_id": BUYURTMA_ID[0],
    }

def _db_apply(rows):
    if "dokonchilar" in rows:
        DOKONCHILAR.clear(); DOKONCHILAR.update({int(k): v for k, v in json.loads(rows["dokonchilar"]).items()})
    if "tovarlar" in rows:
        TOVARLAR.clear(); TOVARLAR.update({int(k): v for k, v in json.loads(rows["tovarlar"]).items()})
    if "buyurtmalar" in rows:
        BUYURTMALAR.clear(); BUYURTMALAR.update({int(k): v for k, v in json.loads(rows["buyurtmalar"]).items()})
    if "kuryerlar" in rows:
        KURYERLAR.clear(); KURYERLAR.update({int(k): v for k, v in json.loads(rows["kuryerlar"]).items()})
    if "tovar_id" in rows:
        TOVAR_ID[0] = int(json.loads(rows["tovar_id"]))
    if "buyurtma_id" in rows:
        BUYURTMA_ID[0] = int(json.loads(rows["buyurtma_id"]))
    print(f"DB: yuklandi - dokon {len(DOKONCHILAR)}, kuryer {len(KURYERLAR)}, buyurtma {len(BUYURTMALAR)}")

def db_save():
    try:
        data = _db_data()
        if DATABASE_URL:
            import psycopg2
            con = psycopg2.connect(DATABASE_URL)
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
            for k, v in data.items():
                cur.execute("INSERT INTO kv (k, v) VALUES (%s, %s) ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v", (k, json.dumps(v, ensure_ascii=False, default=str)))
            con.commit(); con.close()
        else:
            con = sqlite3.connect(DB_PATH)
            con.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
            for k, v in data.items():
                con.execute("INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)", (k, json.dumps(v, ensure_ascii=False, default=str)))
            con.commit(); con.close()
    except Exception as e:
        print("DB save xato:", e)

def db_load():
    try:
        if DATABASE_URL:
            import psycopg2
            con = psycopg2.connect(DATABASE_URL)
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
            cur.execute("SELECT k, v FROM kv")
            rows = dict(cur.fetchall())
            con.close()
            if not rows:
                print("DB: Postgres yangi, eski ma'lumot yoq")
                return
            _db_apply(rows)
        else:
            if not os.path.exists(DB_PATH):
                print("DB: SQLite yangi, eski ma'lumot yoq")
                return
            con = sqlite3.connect(DB_PATH)
            rows = dict(con.execute("SELECT k, v FROM kv").fetchall())
            con.close()
            _db_apply(rows)
    except Exception as e:
        print("DB load xato:", e)

def db_autosave_loop():
    while True:
        time.sleep(30)
        db_save()


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
        [InlineKeyboardButton("🛒 Tovarlar ro'yxati", callback_data="mijoz_tovarlar")],
        [InlineKeyboardButton("🧺 Savatim", callback_data="mijoz_savat")],
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
    # Agar mijoz buyurtma berayotgan bo'lsa - lokatsiyani manzil qilib olish
    if context.user_data.get("checkout_step") == "manzil":
        loc = update.message.location
        await mijoz_create_order(update, context, f"📍 Lokatsiya: {loc.latitude}, {loc.longitude}")
        return
    loc = update.message.location
    await update.message.reply_text(
        f"📍 Joylashuvingiz qabul qilindi: {loc.latitude}, {loc.longitude}\n\nEndi buyurtmani tanlang, yetkazib berish narxi masofaga qarab hisoblanadi:\n1-2 km - 10 000 so'm\n2-5 km - 15 000 so'm\n5 km dan ortiq - kelishilgan narx",
        reply_markup=main_menu()
    )



# ============================================================
# MIJOZ BUYURTMA BERISH - Savat + Lokatsiya + Buyurtma
# ============================================================
# Mijoz: Tovarlar -> Savatga qo'shish -> Savat -> Buyurtma berish
# -> Lokatsiya / Manzil yozish -> Buyurtma do'konchiga tushadi (holat=yangi)

def mijoz_get_savat(context):
    if "savat" not in context.user_data or not isinstance(context.user_data.get("savat"), dict):
        context.user_data["savat"] = {}
    return context.user_data["savat"]

async def mijoz_tovarlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not TOVARLAR:
        await q.edit_message_text("Hozircha tovar yo'q. Do'konchi avval tovar qo'shishi kerak.\n\nTest uchun: do'konchi bo'lib tovar qo'shing, keyin bu yerga qayting.", reply_markup=main_menu())
        return
    txt = "🛒 <b>Tovarlar:</b>\n\nTanlang - savatga qo'shiladi:\n"
    kb = []
    for tid, v in TOVARLAR.items():
        if not v.get("mavjud", True):
            continue
        txt += f"{tid}. {v['nomi']} - {v['narxi']:,} so'm\n"
        kb.append([InlineKeyboardButton(f"➕ {v['nomi']} - {v['narxi']:,} so'm", callback_data=f"mijoz_add_{tid}")])
    kb.append([InlineKeyboardButton("🧺 Savatim", callback_data="mijoz_savat")])
    kb.append([InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="back_main")])
    await q.edit_message_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

async def mijoz_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tid = int(q.data.replace("mijoz_add_", ""))
    if tid not in TOVARLAR:
        await q.edit_message_text("Tovar topilmadi.", reply_markup=main_menu())
        return
    savat = mijoz_get_savat(context)
    savat[tid] = savat.get(tid, 0) + 1
    v = TOVARLAR[tid]
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Yana qo'shish", callback_data=f"mijoz_add_{tid}")],
        [InlineKeyboardButton("🧺 Savatni ko'rish", callback_data="mijoz_savat")],
        [InlineKeyboardButton("🛒 Tovarlar", callback_data="mijoz_tovarlar")],
    ])
    await q.edit_message_text(f"✅ Savatga qo'shildi!\n\n{v['nomi']} - {v['narxi']:,} so'm\nSavatda bu tovardan: {savat[tid]} ta", reply_markup=kb)

async def mijoz_savat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    savat = mijoz_get_savat(context)
    if not savat:
        await q.edit_message_text("🧺 Savatingiz bo'sh.\n\n🛒 Tovarlar ro'yxatidan tanlang.", reply_markup=main_menu())
        return
    txt = "🧺 <b>Savatingiz:</b>\n\n"
    total = 0
    for tid, qty in savat.items():
        if tid not in TOVARLAR:
            continue
        v = TOVARLAR[tid]
        txt += f"{v['nomi']} x {qty} = {v['narxi'] * qty:,} so'm\n"
        total += v['narxi'] * qty
    txt += f"\n<b>Jami: {total:,} so'm</b>\nYetkazib berish: 10 000 - 15 000 so'm (alohida)"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Buyurtma berish", callback_data="mijoz_checkout")],
        [InlineKeyboardButton("🗑 Savatni tozalash", callback_data="mijoz_clear")],
        [InlineKeyboardButton("🛒 Tovarlar", callback_data="mijoz_tovarlar")],
        [InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="back_main")],
    ])
    await q.edit_message_text(txt, parse_mode="HTML", reply_markup=kb)

async def mijoz_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["savat"] = {}
    await q.edit_message_text("🗑 Savat tozalandi.", reply_markup=main_menu())

async def mijoz_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    savat = mijoz_get_savat(context)
    if not savat:
        await q.edit_message_text("Savat bo'sh.", reply_markup=main_menu())
        return
    context.user_data["checkout_step"] = "manzil"
    # Lokatsiya tugmasi - mijoz bosib joyini yuboradi
    loc_kb = ReplyKeyboardMarkup([[KeyboardButton("📍 Lokatsiyani yuborish", request_location=True)]], resize_keyboard=True, one_time_keyboard=True)
    await q.message.reply_text("📍 <b>Manzilingizni yuboring:</b>\n\n1-usul: Pastdagi 📍 Lokatsiyani yuborish tugmasini bosing\n2-usul: Manzilni yozing. Masalan: <i>Termez, Alisher Navoiy 12</i>", parse_mode="HTML", reply_markup=loc_kb)

async def mijoz_create_order(update, context, manzil):
    savat = mijoz_get_savat(context)
    if not savat:
        await update.message.reply_text("Savat bo'sh.", reply_markup=main_menu())
        return
    # Har bir do'kon uchun alohida buyurtma (bitta savatda 2 do'kon bo'lsa)
    by_dokon = {}
    for tid, qty in savat.items():
        if tid not in TOVARLAR:
            continue
        v = TOVARLAR[tid]
        by_dokon.setdefault(v["dokon_id"], []).append((v, qty))
    created = []
    for dokon_id, items in by_dokon.items():
        BUYURTMA_ID[0] += 1
        oid = BUYURTMA_ID[0]
        tovar_txt = ", ".join([f"{v['nomi']} x {qty}" for v, qty in items])
        total = sum([v['narxi'] * qty for v, qty in items])
        BUYURTMALAR[oid] = {"mijoz_id": update.message.from_user.id, "dokon_id": dokon_id, "tovarlar": tovar_txt, "summa": total, "holat": "yangi", "kuryer_id": None, "manzil": manzil}
        created.append(oid)
    context.user_data["savat"] = {}
    context.user_data["checkout_step"] = None
    try:
        db_save()
    except Exception:
        pass
    await update.message.reply_text(
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\nBuyurtma №: {', '.join(['#' + str(x) for x in created])}\nManzil: {manzil}\nDo'kon tasdiqlagach, kuryer yetkazib beradi.\nHolatni 📦 Buyurtmalarim dan kuzating.",
        parse_mode="HTML", reply_markup=main_menu()
    )

async def mijoz_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    my = [(k, v) for k, v in BUYURTMALAR.items() if v.get("mijoz_id") == uid]
    if not my:
        await q.edit_message_text("📦 Hozircha buyurtmangiz yo'q.", reply_markup=main_menu())
        return
    holat_map = {"yangi": "🆕 Do'kon ko'ryapti", "qabul_qilindi": "✅ Do'kon qabul qildi, kuryer kutilmoqda", "kuryerda": "🛵 Kuryer oldi", "oldim": "🏪 Kuryer do'kondan oldi", "yoldaman": "🚀 Kuryer yolda", "yetkazildi": "✅ Yetkazildi", "rad_etildi": "❌ Rad etildi"}
    txt = "📦 <b>Buyurtmalarim:</b>\n\n"
    for k, v in sorted(my, reverse=True)[:10]:
        txt += f"#{k} - {v.get('tovarlar','')} - {v.get('summa',0):,} so'm\nHolat: {holat_map.get(v.get('holat'), v.get('holat'))}\n\n"
    await q.edit_message_text(txt, parse_mode="HTML", reply_markup=main_menu())


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


# ============================================================
# 2-BOSQICH: KURYER PANELI
# ============================================================
# Kuryer: ro'yxatdan o'tadi -> transport tanlaydi -> buyurtma oladi
# -> do'kondan oldim -> yoldaman -> yetkazdim -> pulini ko'radi
# Do'konchi qabul qilgan buyurtma (holat=qabul_qilindi) kuryerga chiqadi.

KURYERLAR = {}  # user_id -> {ism, telefon, transport, online, tasdiqlandi, rasm_bor, yetkazgan, daromad}

def kuryer_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Kuryer bo'lib ro'yxatdan o'tish", callback_data="kuryer_reg")],
        [InlineKeyboardButton("🟢 Ishga chiqish / 🔴 To'xtatish", callback_data="kuryer_toggle")],
        [InlineKeyboardButton("📦 Bo'sh buyurtmalar", callback_data="kuryer_free")],
        [InlineKeyboardButton("🚀 Mening faol buyurtmam", callback_data="kuryer_active")],
        [InlineKeyboardButton("💰 Mening daromadim", callback_data="kuryer_money")],
        [InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="back_main")],
    ])

def kuryer_transport_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚶 Piyoda - rasm shart emas", callback_data="kuryer_tr_Piyoda")],
        [InlineKeyboardButton("🚲 Velosiped", callback_data="kuryer_tr_Velosiped")],
        [InlineKeyboardButton("🛵 Moped / Skuter", callback_data="kuryer_tr_Moped")],
        [InlineKeyboardButton("🚗 Avtomobil", callback_data="kuryer_tr_Avtomobil")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="role_kuryer")],
    ])

def delivery_fee_for(transport):
    # Transportga qarab yetkazib berish narxi (1-5 km uchun o'rtacha)
    return {"Piyoda": 10000, "Velosiped": 12000, "Moped": 13000, "Avtomobil": 15000}.get(transport, 10000)

async def kuryer_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid in KURYERLAR:
        k = KURYERLAR[uid]
        await q.edit_message_text(
            f"🛵 <b>{k['ism']}</b>\nTransport: {k['transport']}\nTelefon: {k['telefon']}\nHolat: {'🟢 Ishda' if k.get('online') else '🔴 Damda'}\nTasdiq: {'✅ Tasdiqlangan' if k.get('tasdiqlandi') else '⏳ Tasdiqlanmoqda'}\nYetkazgan: {k.get('yetkazgan',0)} ta\nDaromad: {k.get('daromad',0):,} so'm",
            parse_mode="HTML", reply_markup=kuryer_menu()
        )
    else:
        await q.edit_message_text(
            "🛵 <b>Kuryer paneli</b>\n\nAvval ro'yxatdan o'ting.\n\nKerak: Ism, Telefon, Transport turi\nPiyodadan boshqalar uchun transport rasmi + admin tasdiqi kerak.",
            parse_mode="HTML", reply_markup=kuryer_menu()
        )

async def kuryer_reg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["kuryer_step"] = "ism"
    await q.edit_message_text("📝 <b>Kuryer ro'yxati</b>\n\n1-qadam: Ismingizni yozing.\nMasalan: <i>Farrux</i>", parse_mode="HTML")

async def kuryer_transport_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tr = q.data.replace("kuryer_tr_", "")
    context.user_data["kuryer_transport"] = tr
    if tr == "Piyoda":
        # Piyoda - rasm shart emas, darhol saqlash
        uid = q.from_user.id
        KURYERLAR[uid] = {"ism": context.user_data.get("kuryer_ism"), "telefon": context.user_data.get("kuryer_telefon"), "transport": tr, "online": False, "tasdiqlandi": True, "rasm_bor": False, "yetkazgan": 0, "daromad": 0}
        context.user_data["kuryer_step"] = None
        await q.edit_message_text(f"✅ Ro'yxatdan o'tdingiz!\n\n🛵 {context.user_data.get('kuryer_ism')} - {tr}\nEndi 🟢 Ishga chiqish ni bosing.", reply_markup=kuryer_menu())
    else:
        context.user_data["kuryer_step"] = "rasm"
        await q.edit_message_text(f"Transport: <b>{tr}</b>\n\nEndi transport rasmini yuboring 📸\n(Moped / Velosiped / Avtomobil uchun rasm shart, admin tasdiqlaydi)", parse_mode="HTML")

async def kuryer_reg_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("kuryer_step")
    if not step:
        return
    text = (update.message.text or "").strip()
    if step == "ism":
        context.user_data["kuryer_ism"] = text
        context.user_data["kuryer_step"] = "telefon"
        await update.message.reply_text("2-qadam: Telefon raqamingizni yozing.\nMasalan: +998 90 123 45 67")
    elif step == "telefon":
        context.user_data["kuryer_telefon"] = text
        context.user_data["kuryer_step"] = "transport"
        await update.message.reply_text("3-qadam: Transport turini tanlang:", reply_markup=kuryer_transport_menu())

async def kuryer_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Transport rasmi kelsa
    if context.user_data.get("kuryer_step") != "rasm":
        return
    uid = update.message.from_user.id
    tr = context.user_data.get("kuryer_transport", "Moped")
    KURYERLAR[uid] = {"ism": context.user_data.get("kuryer_ism"), "telefon": context.user_data.get("kuryer_telefon"), "transport": tr, "online": False, "tasdiqlandi": False, "rasm_bor": True, "yetkazgan": 0, "daromad": 0}
    context.user_data["kuryer_step"] = None
    await update.message.reply_text(f"✅ Rasm qabul qilindi!\n\n🛵 {context.user_data.get('kuryer_ism')} - {tr}\nAriza adminga tushdi. Admin tasdiqlagach ishga chiqasiz. Hozircha test rejimida ishlash ochiq.", reply_markup=kuryer_menu())

async def kuryer_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in KURYERLAR:
        await q.edit_message_text("Avval ro'yxatdan o'ting.", reply_markup=kuryer_menu())
        return
    KURYERLAR[uid]["online"] = not KURYERLAR[uid].get("online", False)
    hol = "🟢 Ishga chiqdingiz - endi buyurtmalar ko'rinadi" if KURYERLAR[uid]["online"] else "🔴 Ishdan to'xtadingiz"
    await q.edit_message_text(hol, reply_markup=kuryer_menu())

async def kuryer_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in KURYERLAR or not KURYERLAR[uid].get("online"):
        await q.edit_message_text("Avval ro'yxatdan o'tib, 🟢 Ishga chiqish ni bosing.", reply_markup=kuryer_menu())
        return
    free = [(k, v) for k, v in BUYURTMALAR.items() if v.get("holat") == "qabul_qilindi" and not v.get("kuryer_id")]
    if not free:
        await q.edit_message_text("📦 Hozircha bo'sh buyurtma yo'q. Birozdan keyin yana tekshiring.", reply_markup=kuryer_menu())
        return
    txt = "📦 <b>Bo'sh buyurtmalar (do'kon qabul qilgan):</b>\n\n"
    kb = []
    fee = delivery_fee_for(KURYERLAR[uid]["transport"])
    for k, v in free:
        txt += f"#{k} - {v.get('tovarlar','')} - {v.get('summa',0):,} so'm\nYetkazib berish: {fee:,} so'm\n\n"
        kb.append([InlineKeyboardButton(f"✅ Olish #{k}", callback_data=f"kuryer_take_{k}")])
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="role_kuryer")])
    await q.edit_message_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

async def kuryer_take(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    oid = int(q.data.replace("kuryer_take_", ""))
    if oid not in BUYURTMALAR:
        await q.edit_message_text("Buyurtma topilmadi.", reply_markup=kuryer_menu())
        return
    if BUYURTMALAR[oid].get("kuryer_id"):
        await q.edit_message_text("Bu buyurtmani boshqa kuryer olib bo'libdi.", reply_markup=kuryer_menu())
        return
    BUYURTMALAR[oid]["kuryer_id"] = uid
    BUYURTMALAR[oid]["holat"] = "kuryerda"
    fee = delivery_fee_for(KURYERLAR[uid]["transport"])
    BUYURTMALAR[oid]["yetkazish_narxi"] = fee
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 Do'kondan oldim", callback_data=f"kuryer_status_oldim_{oid}")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="role_kuryer")],
    ])
    await q.edit_message_text(f"✅ Buyurtma #{oid} sizda!\n\n1. Do'konga boring\n2. Mahsulotni oling\n3. 'Do'kondan oldim' ni bosing\n\nYetkazib berish: {fee:,} so'm", reply_markup=kb)

async def kuryer_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    active = [(k, v) for k, v in BUYURTMALAR.items() if v.get("kuryer_id") == uid and v.get("holat") in ("kuryerda", "oldim", "yoldaman")]
    if not active:
        await q.edit_message_text("Faol buyurtmangiz yo'q.", reply_markup=kuryer_menu())
        return
    k, v = active[0]
    holat = v.get("holat")
    if holat == "kuryerda":
        btn = [InlineKeyboardButton("🏪 Do'kondan oldim", callback_data=f"kuryer_status_oldim_{k}")]
    elif holat == "oldim":
        btn = [InlineKeyboardButton("🚀 Yoldaman - mijozga ketyapman", callback_data=f"kuryer_status_yoldaman_{k}")]
    else:
        btn = [InlineKeyboardButton("✅ Yetkazdim", callback_data=f"kuryer_status_yetkazdim_{k}")]
    await q.edit_message_text(f"🚀 <b>Faol buyurtma #{k}</b>\n\n{v.get('tovarlar','')} - {v.get('summa',0):,} so'm\nHolat: {holat}\nYetkazib berish: {v.get('yetkazish_narxi',0):,} so'm", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([btn, [InlineKeyboardButton("⬅️ Orqaga", callback_data="role_kuryer")]]))

async def kuryer_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # kuryer_status_oldim_1 / yoldaman_1 / yetkazdim_1
    parts = q.data.split("_")  # ['kuryer','status','oldim','1']
    action = parts[2]
    oid = int(parts[3])
    uid = q.from_user.id
    if oid not in BUYURTMALAR:
        await q.edit_message_text("Buyurtma topilmadi.", reply_markup=kuryer_menu())
        return
    if action == "oldim":
        BUYURTMALAR[oid]["holat"] = "oldim"
        await q.edit_message_text(f"🏪 Buyurtma #{oid} do'kondan olindi.\nEndi mijozga boring.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Yoldaman", callback_data=f"kuryer_status_yoldaman_{oid}")]]))
    elif action == "yoldaman":
        BUYURTMALAR[oid]["holat"] = "yoldaman"
        await q.edit_message_text(f"🚀 Buyurtma #{oid} - yoldasiz.\nYetkazgach 'Yetkazdim' ni bosing.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Yetkazdim", callback_data=f"kuryer_status_yetkazdim_{oid}")]]))
    elif action == "yetkazdim":
        BUYURTMALAR[oid]["holat"] = "yetkazildi"
        fee = BUYURTMALAR[oid].get("yetkazish_narxi", 10000)
        if uid in KURYERLAR:
            KURYERLAR[uid]["yetkazgan"] = KURYERLAR[uid].get("yetkazgan", 0) + 1
            KURYERLAR[uid]["daromad"] = KURYERLAR[uid].get("daromad", 0) + fee
        await q.edit_message_text(f"✅ Buyurtma #{oid} yetkazildi!\n\n💰 Sizga: {fee:,} so'm qo'shildi.", reply_markup=kuryer_menu())

async def kuryer_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in KURYERLAR:
        await q.edit_message_text("Avval ro'yxatdan o'ting.", reply_markup=kuryer_menu())
        return
    k = KURYERLAR[uid]
    await q.edit_message_text(f"💰 <b>Daromad</b>\n\nYetkazgan buyurtma: {k.get('yetkazgan',0)} ta\nJami daromad: {k.get('daromad',0):,} so'm\nTransport: {k['transport']}", parse_mode="HTML", reply_markup=kuryer_menu())


async def test_order_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Faqat test uchun: /testbuyurtma yozsa, kuryer ko'rishi uchun 1 ta test buyurtma yaratadi
    BUYURTMA_ID[0] += 1
    oid = BUYURTMA_ID[0]
    BUYURTMALAR[oid] = {"mijoz_id": update.message.from_user.id, "dokon_id": 0, "tovarlar": "Test - Lag'mon 1 ta", "summa": 35000, "holat": "qabul_qilindi", "kuryer_id": None}
    await update.message.reply_text(f"🧪 Test buyurtma yaratildi: #{oid}\n\nEndi Kuryer paneli -> 📦 Bo'sh buyurtmalar ni bosing, shu buyurtma chiqishi kerak.")



# ---------- RENDER BEPUL WEB SERVICE UCHUN - WEBHOOK ----------
# Background Worker pullik, Web Service bepul.
# Web Service da polling ishlamaydi, webhook ishlaydi.
# Render Environment ga 2 ta narsa qo'yiladi:
#   BOT_TOKEN = bot tokeni
#   WEBHOOK_URL = https://hurma-bot.onrender.com  <- Render dagi sizning URL ingiz, oxirida / yo'q

# ---------- BAZA: SQLite - ma'lumotlar o'chmaydi ----------
# Oldin ma'lumotlar faqat xotirada (dict) edi - Render uxlab qolsa tozalanardi.
# Endi har 30 soniyada termez.db fayliga yoziladi, ishga tushganda qayta o'qiladi.
# Render bepulda fayl deploy qilinguncha saqlanadi (uxlashda o'chmaydi).
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "termez.db")

def db_save():
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
        data = {
            "dokonchilar": {str(k): v for k, v in DOKONCHILAR.items()},
            "tovarlar": {str(k): v for k, v in TOVARLAR.items()},
            "buyurtmalar": {str(k): v for k, v in BUYURTMALAR.items()},
            "kuryerlar": {str(k): v for k, v in KURYERLAR.items()},
            "tovar_id": TOVAR_ID[0],
            "buyurtma_id": BUYURTMA_ID[0],
        }
        for k, v in data.items():
            con.execute("INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)", (k, json.dumps(v, ensure_ascii=False, default=str)))
        con.commit()
        con.close()
    except Exception as e:
        print("DB save xato:", e)

def db_load():
    try:
        if not os.path.exists(DB_PATH):
            print("DB: yangi baza, eski ma'lumot yoq")
            return
        con = sqlite3.connect(DB_PATH)
        con.execute("CREATE TABLE IF NOT EXISTS kv (k, v TEXT)")
        rows = dict(con.execute("SELECT k, v FROM kv").fetchall())
        con.close()
        if "dokonchilar" in rows:
            DOKONCHILAR.clear(); DOKONCHILAR.update({int(k): v for k, v in json.loads(rows["dokonchilar"]).items()})
        if "tovarlar" in rows:
            TOVARLAR.clear(); TOVARLAR.update({int(k): v for k, v in json.loads(rows["tovarlar"]).items()})
        if "buyurtmalar" in rows:
            BUYURTMALAR.clear(); BUYURTMALAR.update({int(k): v for k, v in json.loads(rows["buyurtmalar"]).items()})
        if "kuryerlar" in rows:
            KURYERLAR.clear(); KURYERLAR.update({int(k): v for k, v in json.loads(rows["kuryerlar"]).items()})
        if "tovar_id" in rows:
            TOVAR_ID[0] = int(json.loads(rows["tovar_id"]))
        if "buyurtma_id" in rows:
            BUYURTMA_ID[0] = int(json.loads(rows["buyurtma_id"]))
        print(f"DB: yuklandi - dokon {len(DOKONCHILAR)}, kuryer {len(KURYERLAR)}, buyurtma {len(BUYURTMALAR)}")
    except Exception as e:
        print("DB load xato:", e)

def db_autosave_loop():
    while True:
        time.sleep(30)
        db_save()


TOKEN = os.environ.get("BOT_TOKEN", TOKEN)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", os.environ.get("RENDER_EXTERNAL_URL", "")).rstrip("/")

def build_app():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("testbuyurtma", test_order_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(show_category, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    # Mijoz buyurtma
    app.add_handler(CallbackQueryHandler(mijoz_tovarlar, pattern="^mijoz_tovarlar$"))
    app.add_handler(CallbackQueryHandler(mijoz_add, pattern="^mijoz_add_"))
    app.add_handler(CallbackQueryHandler(mijoz_savat, pattern="^mijoz_savat$"))
    app.add_handler(CallbackQueryHandler(mijoz_clear, pattern="^mijoz_clear$"))
    app.add_handler(CallbackQueryHandler(mijoz_checkout, pattern="^mijoz_checkout$"))
    app.add_handler(CallbackQueryHandler(mijoz_my_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(mijoz_tovarlar, pattern="^sub_"))
    app.add_handler(CallbackQueryHandler(dokon_entry, pattern="^role_dokon$"))
    app.add_handler(CallbackQueryHandler(dokon_reg_start, pattern="^dokon_reg$"))
    app.add_handler(CallbackQueryHandler(dokon_cat_select, pattern="^dokon_cat_"))
    app.add_handler(CallbackQueryHandler(dokon_add_start, pattern="^dokon_add$"))
    app.add_handler(CallbackQueryHandler(dokon_my_products, pattern="^dokon_my_products$"))
    app.add_handler(CallbackQueryHandler(dokon_orders_new, pattern="^dokon_orders_new$"))
    app.add_handler(CallbackQueryHandler(dokon_order_action, pattern="^order_(accept|reject)_"))
    app.add_handler(CallbackQueryHandler(dokon_stats_show, pattern="^dokon_stats$"))
    # Kuryer - 2-bosqich
    app.add_handler(CallbackQueryHandler(kuryer_entry, pattern="^role_kuryer$"))
    app.add_handler(CallbackQueryHandler(kuryer_reg_start, pattern="^kuryer_reg$"))
    app.add_handler(CallbackQueryHandler(kuryer_transport_select, pattern="^kuryer_tr_"))
    app.add_handler(CallbackQueryHandler(kuryer_toggle, pattern="^kuryer_toggle$"))
    app.add_handler(CallbackQueryHandler(kuryer_free, pattern="^kuryer_free$"))
    app.add_handler(CallbackQueryHandler(kuryer_active, pattern="^kuryer_active$"))
    app.add_handler(CallbackQueryHandler(kuryer_money, pattern="^kuryer_money$"))
    app.add_handler(CallbackQueryHandler(kuryer_take, pattern="^kuryer_take_"))
    app.add_handler(CallbackQueryHandler(kuryer_status, pattern="^kuryer_status_"))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.PHOTO, kuryer_photo_message))
    async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data.get("dokon_reg_step"):
            await dokon_reg_message(update, context)
        elif context.user_data.get("add_step"):
            await dokon_add_message(update, context)
        elif context.user_data.get("checkout_step") == "manzil":
            await mijoz_create_order(update, context, update.message.text)
        elif context.user_data.get("kuryer_step"):
            await kuryer_reg_message(update, context)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    return app

# ============================================================
# 2-BOSQICH: KURYER PANELI
# ============================================================
# Kuryer: ro'yxatdan o'tadi -> transport tanlaydi -> buyurtma oladi
# -> do'kondan oldim -> yoldaman -> yetkazdim -> pulini ko'radi
# Do'konchi qabul qilgan buyurtma (holat=qabul_qilindi) kuryerga chiqadi.

KURYERLAR = {}  # user_id -> {ism, telefon, transport, online, tasdiqlandi, rasm_bor, yetkazgan, daromad}

def kuryer_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Kuryer bo'lib ro'yxatdan o'tish", callback_data="kuryer_reg")],
        [InlineKeyboardButton("🟢 Ishga chiqish / 🔴 To'xtatish", callback_data="kuryer_toggle")],
        [InlineKeyboardButton("📦 Bo'sh buyurtmalar", callback_data="kuryer_free")],
        [InlineKeyboardButton("🚀 Mening faol buyurtmam", callback_data="kuryer_active")],
        [InlineKeyboardButton("💰 Mening daromadim", callback_data="kuryer_money")],
        [InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="back_main")],
    ])

def kuryer_transport_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚶 Piyoda - rasm shart emas", callback_data="kuryer_tr_Piyoda")],
        [InlineKeyboardButton("🚲 Velosiped", callback_data="kuryer_tr_Velosiped")],
        [InlineKeyboardButton("🛵 Moped / Skuter", callback_data="kuryer_tr_Moped")],
        [InlineKeyboardButton("🚗 Avtomobil", callback_data="kuryer_tr_Avtomobil")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="role_kuryer")],
    ])

def delivery_fee_for(transport):
    # Transportga qarab yetkazib berish narxi (1-5 km uchun o'rtacha)
    return {"Piyoda": 10000, "Velosiped": 12000, "Moped": 13000, "Avtomobil": 15000}.get(transport, 10000)

async def kuryer_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid in KURYERLAR:
        k = KURYERLAR[uid]
        await q.edit_message_text(
            f"🛵 <b>{k['ism']}</b>\nTransport: {k['transport']}\nTelefon: {k['telefon']}\nHolat: {'🟢 Ishda' if k.get('online') else '🔴 Damda'}\nTasdiq: {'✅ Tasdiqlangan' if k.get('tasdiqlandi') else '⏳ Tasdiqlanmoqda'}\nYetkazgan: {k.get('yetkazgan',0)} ta\nDaromad: {k.get('daromad',0):,} so'm",
            parse_mode="HTML", reply_markup=kuryer_menu()
        )
    else:
        await q.edit_message_text(
            "🛵 <b>Kuryer paneli</b>\n\nAvval ro'yxatdan o'ting.\n\nKerak: Ism, Telefon, Transport turi\nPiyodadan boshqalar uchun transport rasmi + admin tasdiqi kerak.",
            parse_mode="HTML", reply_markup=kuryer_menu()
        )

async def kuryer_reg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["kuryer_step"] = "ism"
    await q.edit_message_text("📝 <b>Kuryer ro'yxati</b>\n\n1-qadam: Ismingizni yozing.\nMasalan: <i>Farrux</i>", parse_mode="HTML")

async def kuryer_transport_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tr = q.data.replace("kuryer_tr_", "")
    context.user_data["kuryer_transport"] = tr
    if tr == "Piyoda":
        # Piyoda - rasm shart emas, darhol saqlash
        uid = q.from_user.id
        KURYERLAR[uid] = {"ism": context.user_data.get("kuryer_ism"), "telefon": context.user_data.get("kuryer_telefon"), "transport": tr, "online": False, "tasdiqlandi": True, "rasm_bor": False, "yetkazgan": 0, "daromad": 0}
        context.user_data["kuryer_step"] = None
        await q.edit_message_text(f"✅ Ro'yxatdan o'tdingiz!\n\n🛵 {context.user_data.get('kuryer_ism')} - {tr}\nEndi 🟢 Ishga chiqish ni bosing.", reply_markup=kuryer_menu())
    else:
        context.user_data["kuryer_step"] = "rasm"
        await q.edit_message_text(f"Transport: <b>{tr}</b>\n\nEndi transport rasmini yuboring 📸\n(Moped / Velosiped / Avtomobil uchun rasm shart, admin tasdiqlaydi)", parse_mode="HTML")

async def kuryer_reg_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("kuryer_step")
    if not step:
        return
    text = (update.message.text or "").strip()
    if step == "ism":
        context.user_data["kuryer_ism"] = text
        context.user_data["kuryer_step"] = "telefon"
        await update.message.reply_text("2-qadam: Telefon raqamingizni yozing.\nMasalan: +998 90 123 45 67")
    elif step == "telefon":
        context.user_data["kuryer_telefon"] = text
        context.user_data["kuryer_step"] = "transport"
        await update.message.reply_text("3-qadam: Transport turini tanlang:", reply_markup=kuryer_transport_menu())

async def kuryer_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Transport rasmi kelsa
    if context.user_data.get("kuryer_step") != "rasm":
        return
    uid = update.message.from_user.id
    tr = context.user_data.get("kuryer_transport", "Moped")
    KURYERLAR[uid] = {"ism": context.user_data.get("kuryer_ism"), "telefon": context.user_data.get("kuryer_telefon"), "transport": tr, "online": False, "tasdiqlandi": False, "rasm_bor": True, "yetkazgan": 0, "daromad": 0}
    context.user_data["kuryer_step"] = None
    await update.message.reply_text(f"✅ Rasm qabul qilindi!\n\n🛵 {context.user_data.get('kuryer_ism')} - {tr}\nAriza adminga tushdi. Admin tasdiqlagach ishga chiqasiz. Hozircha test rejimida ishlash ochiq.", reply_markup=kuryer_menu())

async def kuryer_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in KURYERLAR:
        await q.edit_message_text("Avval ro'yxatdan o'ting.", reply_markup=kuryer_menu())
        return
    KURYERLAR[uid]["online"] = not KURYERLAR[uid].get("online", False)
    hol = "🟢 Ishga chiqdingiz - endi buyurtmalar ko'rinadi" if KURYERLAR[uid]["online"] else "🔴 Ishdan to'xtadingiz"
    await q.edit_message_text(hol, reply_markup=kuryer_menu())

async def kuryer_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in KURYERLAR or not KURYERLAR[uid].get("online"):
        await q.edit_message_text("Avval ro'yxatdan o'tib, 🟢 Ishga chiqish ni bosing.", reply_markup=kuryer_menu())
        return
    free = [(k, v) for k, v in BUYURTMALAR.items() if v.get("holat") == "qabul_qilindi" and not v.get("kuryer_id")]
    if not free:
        await q.edit_message_text("📦 Hozircha bo'sh buyurtma yo'q. Birozdan keyin yana tekshiring.", reply_markup=kuryer_menu())
        return
    txt = "📦 <b>Bo'sh buyurtmalar (do'kon qabul qilgan):</b>\n\n"
    kb = []
    fee = delivery_fee_for(KURYERLAR[uid]["transport"])
    for k, v in free:
        txt += f"#{k} - {v.get('tovarlar','')} - {v.get('summa',0):,} so'm\nYetkazib berish: {fee:,} so'm\n\n"
        kb.append([InlineKeyboardButton(f"✅ Olish #{k}", callback_data=f"kuryer_take_{k}")])
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="role_kuryer")])
    await q.edit_message_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

async def kuryer_take(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    oid = int(q.data.replace("kuryer_take_", ""))
    if oid not in BUYURTMALAR:
        await q.edit_message_text("Buyurtma topilmadi.", reply_markup=kuryer_menu())
        return
    if BUYURTMALAR[oid].get("kuryer_id"):
        await q.edit_message_text("Bu buyurtmani boshqa kuryer olib bo'libdi.", reply_markup=kuryer_menu())
        return
    BUYURTMALAR[oid]["kuryer_id"] = uid
    BUYURTMALAR[oid]["holat"] = "kuryerda"
    fee = delivery_fee_for(KURYERLAR[uid]["transport"])
    BUYURTMALAR[oid]["yetkazish_narxi"] = fee
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 Do'kondan oldim", callback_data=f"kuryer_status_oldim_{oid}")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="role_kuryer")],
    ])
    await q.edit_message_text(f"✅ Buyurtma #{oid} sizda!\n\n1. Do'konga boring\n2. Mahsulotni oling\n3. 'Do'kondan oldim' ni bosing\n\nYetkazib berish: {fee:,} so'm", reply_markup=kb)

async def kuryer_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    active = [(k, v) for k, v in BUYURTMALAR.items() if v.get("kuryer_id") == uid and v.get("holat") in ("kuryerda", "oldim", "yoldaman")]
    if not active:
        await q.edit_message_text("Faol buyurtmangiz yo'q.", reply_markup=kuryer_menu())
        return
    k, v = active[0]
    holat = v.get("holat")
    if holat == "kuryerda":
        btn = [InlineKeyboardButton("🏪 Do'kondan oldim", callback_data=f"kuryer_status_oldim_{k}")]
    elif holat == "oldim":
        btn = [InlineKeyboardButton("🚀 Yoldaman - mijozga ketyapman", callback_data=f"kuryer_status_yoldaman_{k}")]
    else:
        btn = [InlineKeyboardButton("✅ Yetkazdim", callback_data=f"kuryer_status_yetkazdim_{k}")]
    await q.edit_message_text(f"🚀 <b>Faol buyurtma #{k}</b>\n\n{v.get('tovarlar','')} - {v.get('summa',0):,} so'm\nHolat: {holat}\nYetkazib berish: {v.get('yetkazish_narxi',0):,} so'm", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([btn, [InlineKeyboardButton("⬅️ Orqaga", callback_data="role_kuryer")]]))

async def kuryer_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # kuryer_status_oldim_1 / yoldaman_1 / yetkazdim_1
    parts = q.data.split("_")  # ['kuryer','status','oldim','1']
    action = parts[2]
    oid = int(parts[3])
    uid = q.from_user.id
    if oid not in BUYURTMALAR:
        await q.edit_message_text("Buyurtma topilmadi.", reply_markup=kuryer_menu())
        return
    if action == "oldim":
        BUYURTMALAR[oid]["holat"] = "oldim"
        await q.edit_message_text(f"🏪 Buyurtma #{oid} do'kondan olindi.\nEndi mijozga boring.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Yoldaman", callback_data=f"kuryer_status_yoldaman_{oid}")]]))
    elif action == "yoldaman":
        BUYURTMALAR[oid]["holat"] = "yoldaman"
        await q.edit_message_text(f"🚀 Buyurtma #{oid} - yoldasiz.\nYetkazgach 'Yetkazdim' ni bosing.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Yetkazdim", callback_data=f"kuryer_status_yetkazdim_{oid}")]]))
    elif action == "yetkazdim":
        BUYURTMALAR[oid]["holat"] = "yetkazildi"
        fee = BUYURTMALAR[oid].get("yetkazish_narxi", 10000)
        if uid in KURYERLAR:
            KURYERLAR[uid]["yetkazgan"] = KURYERLAR[uid].get("yetkazgan", 0) + 1
            KURYERLAR[uid]["daromad"] = KURYERLAR[uid].get("daromad", 0) + fee
        await q.edit_message_text(f"✅ Buyurtma #{oid} yetkazildi!\n\n💰 Sizga: {fee:,} so'm qo'shildi.", reply_markup=kuryer_menu())

async def kuryer_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in KURYERLAR:
        await q.edit_message_text("Avval ro'yxatdan o'ting.", reply_markup=kuryer_menu())
        return
    k = KURYERLAR[uid]
    await q.edit_message_text(f"💰 <b>Daromad</b>\n\nYetkazgan buyurtma: {k.get('yetkazgan',0)} ta\nJami daromad: {k.get('daromad',0):,} so'm\nTransport: {k['transport']}", parse_mode="HTML", reply_markup=kuryer_menu())


async def test_order_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Faqat test uchun: /testbuyurtma yozsa, kuryer ko'rishi uchun 1 ta test buyurtma yaratadi
    BUYURTMA_ID[0] += 1
    oid = BUYURTMA_ID[0]
    BUYURTMALAR[oid] = {"mijoz_id": update.message.from_user.id, "dokon_id": 0, "tovarlar": "Test - Lag'mon 1 ta", "summa": 35000, "holat": "qabul_qilindi", "kuryer_id": None}
    await update.message.reply_text(f"🧪 Test buyurtma yaratildi: #{oid}\n\nEndi Kuryer paneli -> 📦 Bo'sh buyurtmalar ni bosing, shu buyurtma chiqishi kerak.")



# ============================================================
# 3-BOSQICH: ADMIN PANELI
# ============================================================
# Kompyuterdan: https://hurma-bot.onrender.com/admin
# Telegramda: /admin
# Faqat ko'rish uchun - tasdiqlash keyingi versiyada.

def admin_stats():
    try:
        db_save()
    except Exception:
        pass
    orders = list(BUYURTMALAR.values())
    total_buyurtma = sum([o.get("summa",0) for o in orders])
    total_yetkazish = sum([o.get("yetkazish_narxi",0) for o in orders if o.get("holat")=="yetkazildi"])
    return {
        "dokonlar": len(DOKONCHILAR),
        "kuryerlar": len(KURYERLAR),
        "tovarlar": len(TOVARLAR),
        "buyurtmalar": len(orders),
        "yangi": len([o for o in orders if o.get("holat")=="yangi"]),
        "qabul": len([o for o in orders if o.get("holat")=="qabul_qilindi"]),
        "yolda": len([o for o in orders if o.get("holat") in ("kuryerda","oldim","yoldaman")]),
        "yetkazildi": len([o for o in orders if o.get("holat")=="yetkazildi"]),
        "rad": len([o for o in orders if o.get("holat")=="rad_etildi"]),
        "jami_summa": total_buyurtma,
        "jami_yetkazish": total_yetkazish,
        "kuryer_daromad": sum([k.get("daromad",0) for k in KURYERLAR.values()]),
        "dokonlar_list": [{"id": str(k), "nomi": v.get("dokon_nomi",""), "kat": v.get("kategoriya",""), "tel": v.get("telefon",""), "tasdiq": bool(v.get("tasdiqlandi"))} for k,v in DOKONCHILAR.items()],
        "kuryerlar_list": [{"id": str(k), "ism": v.get("ism",""), "tel": v.get("telefon",""), "tr": v.get("transport",""), "online": bool(v.get("online")), "yetkazgan": v.get("yetkazgan",0), "daromad": v.get("daromad",0)} for k,v in KURYERLAR.items()],
        "buyurtmalar_list": [{"id": str(k), "tovar": v.get("tovarlar",""), "summa": v.get("summa",0), "holat": v.get("holat",""), "kuryer": str(v.get("kuryer_id") or "-")} for k,v in BUYURTMALAR.items()],
    }

def admin_html():
    s = admin_stats()
    def row_dokon(d):
        return f"<tr><td>{d['id']}</td><td>{d['nomi']}</td><td>{d['kat']}</td><td>{d['tel']}</td><td>{'✅' if d['tasdiq'] else '⏳'}</td></tr>"
    def row_kuryer(k):
        return f"<tr><td>{k['ism']}</td><td>{k['tel']}</td><td>{k['tr']}</td><td>{'🟢' if k['online'] else '🔴'}</td><td>{k['yetkazgan']}</td><td>{k['daromad']:,} so'm</td></tr>"
    def row_order(o):
        return f"<tr><td>#{o['id']}</td><td>{o['tovar']}</td><td>{o['summa']:,} so'm</td><td>{o['holat']}</td><td>{o['kuryer']}</td></tr>"
    return f"""<!DOCTYPE html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Termez Super Boti - Admin</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1000px;margin:0 auto;padding:16px;background:#f6f6f6}}h1{{font-size:22px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}.card{{background:#fff;padding:14px;border-radius:12px;box-shadow:0 1px 4px #0001}}.card b{{font-size:22px;display:block}}table{{width:100%;background:#fff;border-collapse:collapse;margin:12px 0;border-radius:10px;overflow:hidden}}th,td{{padding:8px;border-bottom:1px solid #eee;text-align:left;font-size:14px}}button{{padding:10px 16px;border:0;border-radius:10px;background:#000;color:#fff;cursor:pointer}}</style></head>
<body><h1>📊 Termez Super Boti - Admin panel</h1><button onclick="location.reload()">🔄 Yangilash</button>
<div class="cards">
<div class="card">Do'konlar<b>{s['dokonlar']}</b></div><div class="card">Kuryerlar<b>{s['kuryerlar']}</b></div><div class="card">Tovarlar<b>{s['tovarlar']}</b></div><div class="card">Buyurtmalar<b>{s['buyurtmalar']}</b></div>
<div class="card">Jami savdo<b>{s['jami_summa']:,} so'm</b></div><div class="card">Yetkazish puli<b>{s['jami_yetkazish']:,} so'm</b></div><div class="card">Kuryer daromadi<b>{s['kuryer_daromad']:,} so'm</b></div><div class="card">Yetkazildi / Yolda / Yangi<b>{s['yetkazildi']} / {s['yolda']} / {s['yangi']}</b></div>
</div>
<h2>🏪 Do'konlar</h2><table><tr><th>ID</th><th>Nomi</th><th>Kategoriya</th><th>Telefon</th><th>Tasdiq</th></tr>{''.join([row_dokon(d) for d in s['dokonlar_list']]) or '<tr><td colspan=5>Hozircha yoq</td></tr>'}</table>
<h2>🛵 Kuryerlar</h2><table><tr><th>Ism</th><th>Telefon</th><th>Transport</th><th>Online</th><th>Yetkazgan</th><th>Daromad</th></tr>{''.join([row_kuryer(k) for k in s['kuryerlar_list']]) or '<tr><td colspan=6>Hozircha yoq</td></tr>'}</table>
<h2>🧾 Buyurtmalar</h2><table><tr><th>ID</th><th>Tovar</th><th>Summa</th><th>Holat</th><th>Kuryer ID</th></tr>{''.join([row_order(o) for o in s['buyurtmalar_list']]) or '<tr><td colspan=5>Hozircha yoq</td></tr>'}</table>
<p style="color:#888;font-size:13px">Eslatma: Render bepul rejimda server uxlab qolsa, ma'lumotlar (dict) tozalanishi mumkin. Keyingi qadam - bazaga (SQLite / Postgres) o'tkazish.</p></body></html>"""

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = admin_stats()
    await update.message.reply_text(
        f"📊 <b>ADMIN</b>\n\n🏪 Do'konlar: {s['dokonlar']}\n🛵 Kuryerlar: {s['kuryerlar']}\n📦 Tovarlar: {s['tovarlar']}\n🧾 Buyurtmalar: {s['buyurtmalar']}\n✅ Yetkazildi: {s['yetkazildi']} | 🚀 Yolda: {s['yolda']} | 🆕 Yangi: {s['yangi']}\n\n💰 Jami savdo: {s['jami_summa']:,} so'm\n🚀 Yetkazish: {s['jami_yetkazish']:,} so'm\n\nKompyuterdan to'liq ko'rish:\nhttps://hurma-bot.onrender.com/admin",
        parse_mode="HTML"
    )


# ---------- RENDER BEPUL WEB SERVICE + UPTIMEROBOT UCHUN - FLASK WEBHOOK ----------
# Muammo: PTB ning run_webhook() i GET / ga 404 beradi.
# UptimeRobot GET / ni tekshiradi, shuning uchun doim "Down" ko'rsatadi.
# Yechim: Flask ni o'zimiz yuritamiz:
#   GET / -> 200 OK (UptimeRobot yashil bo'ladi, Render uyg'onadi)
#   POST /TOKEN -> Telegram xabari botga tushadi

flask_app = Flask(__name__)
bot_loop = None
telegram_app = None

@flask_app.route("/", methods=["GET"])
def health():
    return "Termez Super Boti ishlayapti ✅", 200

@flask_app.route("/admin", methods=["GET"])
def admin_page():
    return admin_html(), 200

@flask_app.route("/api/admin", methods=["GET"])
def admin_api():
    return jsonify(admin_stats())

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), bot_loop)
    except Exception as e:
        print("Webhook xato:", e)
    return "OK", 200

def run_bot_loop():
    global bot_loop, telegram_app
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    db_load()
    threading.Thread(target=db_autosave_loop, daemon=True).start()
    telegram_app = build_app()
    bot_loop.run_until_complete(telegram_app.initialize())
    bot_loop.run_until_complete(telegram_app.start())
    if WEBHOOK_URL:
        bot_loop.run_until_complete(telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}", drop_pending_updates=True))
        print(f"Webhook rejim: {WEBHOOK_URL} - ishga tushdi")
    bot_loop.run_forever()

def main():
    port = int(os.environ.get("PORT", 10000))
    if WEBHOOK_URL:
        # Render bepul Web Service
        threading.Thread(target=run_bot_loop, daemon=True).start()
        flask_app.run(host="0.0.0.0", port=port)
    else:
        # Kompyuterda test - polling
        print("WEBHOOK_URL yo'q, kompyuterda polling bilan ishlayapti...")
        db_load()
        app = build_app()
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
