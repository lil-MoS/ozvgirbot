import sqlite3
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, CallbackContext
from telegram.ext.filters import Filters

# توکن بات و آیدی مدیر
TOKEN = "_"
ADMIN_ID = "_"

# دیتابیس رو راه‌اندازی می‌کنیم
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, coins INTEGER DEFAULT 0, referral_code TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY, user_id INTEGER, member_count INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups (group_id TEXT PRIMARY KEY, user_id INTEGER, member_count INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_joined (user_id INTEGER, channel_group_id TEXT, PRIMARY KEY (user_id, channel_group_id))''')
    conn.commit()
    conn.close()

# گرفتن تعداد سکه‌های کاربر
def get_user_coins(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

# منوی اصلی
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, coins) VALUES (?, 0)", (user_id,))
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("💰 جمع‌آوری سکه", callback_data="collect_coins")],
        [InlineKeyboardButton("📢 ثبت کانال", callback_data="register_channel"), InlineKeyboardButton("👥 ثبت گروه", callback_data="register_group")],
        [InlineKeyboardButton("💰 سکه‌های من", callback_data="my_coins")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
        [InlineKeyboardButton("🛒 خرید سکه", callback_data="buy_coins"), InlineKeyboardButton("📣 زیرمجموعه‌گیری", callback_data="referral")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("👋 به بات خوش آمدید!\nلطفاً گزینه‌ای رو انتخاب کنید:", reply_markup=reply_markup)

# مدیریت دکمه‌ها
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    query.answer()

    if data == "collect_coins":
        collect_coins(query, context, 0)  # شروع از تبلیغ اول
    elif data == "register_channel":
        query.message.reply_text("📢 لطفاً آیدی یا لینک کانال رو بفرستید (مثلاً @ChannelName):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_menu")]]))
        context.user_data["state"] = "awaiting_channel"
    elif data == "register_group":
        query.message.reply_text("👥 لطفاً آیدی یا لینک گروه رو بفرستید (مثلاً @GroupName):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_menu")]]))
        context.user_data["state"] = "awaiting_group"
    elif data == "settings":
        settings(query, context)
    elif data == "help":
        help(query, context)
    elif data == "buy_coins":
        keyboard = [
            [InlineKeyboardButton("100 سکه - 50 هزار تومان", url="https://zarinp.al/692055")],
            [InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_menu")]
        ]
        query.message.reply_text(
            "🛒 برای خرید سکه، از لینک زیر استفاده کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "check_admin":
        check_admin(query, context)
    elif data == "referral":
        send_referral_link(query, context)
    elif data == "my_coins":
        coins = get_user_coins(user_id)
        query.message.reply_text(f"💰 تعداد سکه‌های شما: {coins}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_menu")]]))
    elif data.startswith("join_"):
        check_membership(query, context, data.split("_")[1])
    elif data == "continue_collect":
        collect_coins(query, context, context.user_data.get("current_ad_index", 0))
    elif data == "next_ad":
        current_index = context.user_data.get("current_ad_index", 0) + 1
        collect_coins(query, context, current_index)
    elif data == "back_to_menu":
        context.user_data["state"] = None
        # ویرایش پیام فعلی برای نمایش منوی اصلی
        keyboard = [
            [InlineKeyboardButton("💰 جمع‌آوری سکه", callback_data="collect_coins")],
            [InlineKeyboardButton("📢 ثبت کانال", callback_data="register_channel"), InlineKeyboardButton("👥 ثبت گروه", callback_data="register_group")],
            [InlineKeyboardButton("💰 سکه‌های من", callback_data="my_coins")],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
            [InlineKeyboardButton("🛒 خرید سکه", callback_data="buy_coins"), InlineKeyboardButton("📣 زیرمجموعه‌گیری", callback_data="referral")],
            [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text("👋 به بات خوش آمدید!\nلطفاً گزینه‌ای رو انتخاب کنید:", reply_markup=reply_markup)
    elif data == "cancel_register":
        context.user_data["state"] = None
        query.message.reply_text("❌ ثبت کانال/گروه لغو شد.")
        # برگشت به منوی اصلی
        keyboard = [
            [InlineKeyboardButton("💰 جمع‌آوری سکه", callback_data="collect_coins")],
            [InlineKeyboardButton("📢 ثبت کانال", callback_data="register_channel"), InlineKeyboardButton("👥 ثبت گروه", callback_data="register_group")],
            [InlineKeyboardButton("💰 سکه‌های من", callback_data="my_coins")],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
            [InlineKeyboardButton("🛒 خرید سکه", callback_data="buy_coins"), InlineKeyboardButton("📣 زیرمجموعه‌گیری", callback_data="referral")],
            [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text("👋 به بات خوش آمدید!\nلطفاً گزینه‌ای رو انتخاب کنید:", reply_markup=reply_markup)

# جمع‌آوری سکه (بهینه‌شده برای جلوگیری از مشکلات)
def collect_coins(query, context: CallbackContext, ad_index):
    user_id = query.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT channel_id FROM channels")
    channels = c.fetchall()
    c.execute("SELECT group_id FROM groups")
    groups = c.fetchall()
    # گرفتن چت‌هایی که کاربر قبلاً سکه گرفته
    c.execute("SELECT channel_group_id FROM user_joined WHERE user_id = ?", (user_id,))
    joined_chats = [row[0] for row in c.fetchall()]
    conn.close()

    # فقط چت‌هایی که بات ادمینه و کاربر عضو نیست و قبلاً سکه نگرفته
    all_ads = []
    for ch in channels:
        chat_id = ch[0]
        try:
            # چک کردن ادمین بودن بات
            if not check_admin_status(context, chat_id, user_id):
                continue
            # چک کردن عضویت کاربر
            member = context.bot.get_chat_member(chat_id, user_id)
            if member.status not in ["member", "administrator", "creator"] and chat_id not in joined_chats:
                all_ads.append((chat_id, "📢 کانال"))
        except:
            if chat_id not in joined_chats and check_admin_status(context, chat_id, user_id):
                all_ads.append((chat_id, "📢 کانال"))

    for gr in groups:
        chat_id = gr[0]
        try:
            if not check_admin_status(context, chat_id, user_id):
                continue
            member = context.bot.get_chat_member(chat_id, user_id)
            if member.status not in ["member", "administrator", "creator"] and chat_id not in joined_chats:
                all_ads.append((chat_id, "👥 گروه"))
        except:
            if chat_id not in joined_chats and check_admin_status(context, chat_id, user_id):
                all_ads.append((chat_id, "👥 گروه"))

    if not all_ads:
        keyboard = [
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]
        ]
        query.message.reply_text("❌ تبلیغی دیگه برای نمایش نیست!", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if ad_index >= len(all_ads):
        ad_index = 0  # برگشت به اول اگه به آخر خط برسه

    chat_id, chat_type = all_ads[ad_index]
    context.user_data["current_ad_index"] = ad_index
    keyboard = [
        [InlineKeyboardButton("✅ بررسی عضویت", callback_data=f"join_{chat_id}")],
        [InlineKeyboardButton("➡️ بعدی", callback_data="next_ad")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        f"{chat_type}: <a href='https://t.me/{chat_id[1:]}'>{chat_id}</a>\nبا عضویت 1 سکه بگیرید! ❗️",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# بررسی عضویت و دادن سکه
def check_membership(query, context: CallbackContext, chat_id):
    user_id = query.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM user_joined WHERE user_id = ? AND channel_group_id = ?", (user_id, chat_id))
    already_joined = c.fetchone()
    
    try:
        member = context.bot.get_chat_member(chat_id, user_id)
        if member.status in ["member", "administrator", "creator"]:
            if not already_joined:
                c.execute("INSERT INTO user_joined (user_id, channel_group_id) VALUES (?, ?)", (user_id, chat_id))
                c.execute("UPDATE users SET coins = coins + 1 WHERE user_id = ?", (user_id,))
                conn.commit()
                keyboard = [
                    [InlineKeyboardButton("💰 ادامه جمع‌آوری سکه", callback_data="continue_collect")],
                    [InlineKeyboardButton("🏠 برگشت به منوی اصلی", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(
                    "✅ شما 1 سکه دریافت کردید!\nمی‌خواهید ادامه بدید؟",
                    reply_markup=reply_markup
                )
            else:
                query.message.reply_text("⚠️ شما قبلاً از این کانال/گروه سکه گرفتید!")
        else:
            query.message.reply_text("⚠️ لطفاً اول در کانال/گروه عضو بشید!")
    except Exception as e:
        query.message.reply_text(f"")
    conn.close()

# ثبت کانال یا گروه
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text
    state = context.user_data.get("state")

    if state == "awaiting_channel":
        if check_admin_status(context, text, user_id):
            update.message.reply_text("📢 تعداد اعضای درخواستی برای کانال رو وارد کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_menu")]]))
            context.user_data["channel_id"] = text
            context.user_data["state"] = "awaiting_channel_members"
        else:
            keyboard = [[InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]]
            update.message.reply_text("❌ کانال شما ثبت نشده! لطفاً اول از تنظیمات، بات رو در کانال ادمین کنید.", reply_markup=InlineKeyboardMarkup(keyboard))
    elif state == "awaiting_group":
        if check_admin_status(context, text, user_id):
            update.message.reply_text("👥 تعداد اعضای درخواستی برای گروه رو وارد کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_menu")]]))
            context.user_data["group_id"] = text
            context.user_data["state"] = "awaiting_group_members"
        else:
            keyboard = [[InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]]
            update.message.reply_text("❌ گروه شما ثبت نشده! لطفاً اول از تنظیمات، بات رو در گروه ادمین کنید.", reply_markup=InlineKeyboardMarkup(keyboard))
    elif state in ["awaiting_channel_members", "awaiting_group_members"]:
        try:
            member_count = int(text)
            coins = get_user_coins(user_id)
            if coins < member_count:
                keyboard = [
                    [InlineKeyboardButton("❌ لغو ثبت", callback_data="cancel_register")]
                ]
                update.message.reply_text(
                    f"⚠️ سکه‌های شما کافی نیست!\n📊 تعداد درخواستی: {member_count}\nلطفاً تعداد کمتری وارد کنید:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                conn = sqlite3.connect("bot.db")
                c = conn.cursor()
                if state == "awaiting_channel_members":
                    c.execute("INSERT OR REPLACE INTO channels (channel_id, user_id, member_count) VALUES (?, ?, ?)", (context.user_data["channel_id"], user_id, member_count))
                    update.message.reply_text(f"📢 بات در حال ارسال {member_count} عضو به کانال {context.user_data['channel_id']} است.")
                else:
                    c.execute("INSERT OR REPLACE INTO groups (group_id, user_id, member_count) VALUES (?, ?, ?)", (context.user_data["group_id"], user_id, member_count))
                    update.message.reply_text(f"👥 بات در حال ارسال {member_count} عضو به گروه {context.user_data['group_id']} است.")
                c.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (member_count, user_id))
                conn.commit()
                conn.close()
                context.user_data["state"] = None
        except ValueError:
            update.message.reply_text("❌ لطفاً یه عدد معتبر وارد کنید!")
    elif state == "awaiting_admin_check":  # مدیریت یوزرنیم برای بررسی ادمین
        chat_id = text.strip()
        if not chat_id.startswith("@"):
            update.message.reply_text("❌ لطفاً یوزرنیم رو درست وارد کنید (مثلاً @ChannelName)")
            return
        if check_admin_status(context, chat_id, user_id):
            update.message.reply_text(f"✅ بات با موفقیت در {chat_id} ادمین شده است!")
        else:
            update.message.reply_text(f"❌ بات در {chat_id} ادمین نیست! لطفاً بات رو ادمین کنید.")
        context.user_data["state"] = None
        # برگشت به منوی اصلی
        keyboard = [
            [InlineKeyboardButton("💰 جمع‌آوری سکه", callback_data="collect_coins")],
            [InlineKeyboardButton("📢 ثبت کانال", callback_data="register_channel"), InlineKeyboardButton("👥 ثبت گروه", callback_data="register_group")],
            [InlineKeyboardButton("💰 سکه‌های من", callback_data="my_coins")],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
            [InlineKeyboardButton("🛒 خرید سکه", callback_data="buy_coins"), InlineKeyboardButton("📣 زیرمجموعه‌گیری", callback_data="referral")],
            [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("👋 به بات خوش آمدید!\nلطفاً گزینه‌ای رو انتخاب کنید:", reply_markup=reply_markup)

# بررسی ادمین بودن بات
def check_admin_status(context: CallbackContext, chat_id, user_id):
    try:
        admins = context.bot.get_chat_administrators(chat_id)
        bot_id = context.bot.id
        return any(admin.user.id == bot_id for admin in admins)
    except:
        return False

# بررسی اینکه کاربر خودش مدیر چت هست یا نه
def is_user_admin(context: CallbackContext, chat_id, user_id):
    try:
        admins = context.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False

# تنظیمات (اصلاح‌شده برای گرفتن یوزرنیم)
def settings(query, context: CallbackContext):
    bot_username = context.bot.username
    user_id = query.from_user.id
    keyboard = [
        [InlineKeyboardButton("✅ بررسی ادمین بودن بات", callback_data="check_admin")],
        [InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_menu")]
    ]
    query.message.reply_text(
        f"⚙️ برای ثبت کانال یا گروه، بات رو ادمین کنید:\n"
        f"1️⃣ به تنظیمات کانال/گروه برید.\n"
        f"2️⃣ گزینه‌ی 'ادمین‌ها' رو انتخاب کنید.\n"
        f"3️⃣ 'اضافه کردن ادمین' رو بزنید.\n"
        f"4️⃣ آیدی بات رو وارد کنید: <code>{bot_username}</code> (کلیک کنید تا کپی بشه).\n"
        f"5️⃣ دسترسی‌های لازم رو بدید و ذخیره کنید.\n"
        f"بعدش دکمه‌ی زیر رو بزنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# بررسی ادمین (اصلاح‌شده برای گرفتن یوزرنیم)
def check_admin(query, context: CallbackContext):
    query.message.reply_text(
        "📋 لطفاً یوزرنیم کانال یا گروه رو بفرستید (مثلاً @ChannelName):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_menu")]])
    )
    context.user_data["state"] = "awaiting_admin_check"

# زیرمجموعه‌گیری
def send_referral_link(query, context: CallbackContext):
    user_id = query.from_user.id
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    keyboard = [[InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_menu")]]
    query.message.reply_text(
        f"📣 زیرمجموعه‌گیری:\n"
        f"با دعوت دوستانتون، به ازای هر نفر 5 سکه بگیرید!\n"
        f"🔗 لینک دعوت شما:\n{referral_link}\n"
        f"این لینک رو به دوستانتون بفرستید تا با ورودشون 5 سکه بهتون اضافه بشه!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# راهنما
def help(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        update.message.reply_text(
            "ℹ️ دستورات مدیر:\n"
            "/stats - نمایش آمار بات\n"
            "/broadcast_users - پیام همگانی به کاربران\n"
            "/broadcast_chats - پیام همگانی به کانال‌ها و گروه‌ها\n"
            "/coin - دادن سکه به کاربر\n"
            "/help - نمایش این پیام\n"
            "/db - دریافت فایل دیتابیس"
        )
    else:
        update.message.reply_text(
            "ℹ️ راهنما - بات چطور کار می‌کنه؟\n"
            "این بات به شما اجازه می‌ده با سکه‌ها کار کنید:\n"
            "1️⃣ *جمع‌آوری سکه*: توی کانال‌ها و گروه‌هایی که نشون داده می‌شه عضو بشید و سکه بگیرید.\n"
            "2️⃣ *ثبت کانال/گروه*: کانال یا گروهتون رو ثبت کنید، بات رو ادمین کنید و با سکه‌هاتون برای اون‌ها عضو بخرید.\n"
            "3️⃣ *زیرمجموعه‌گیری*: دوستانتون رو دعوت کنید و به ازای هر نفر 5 سکه بگیرید.\n"
            "4️⃣ *سکه‌ها*: هر سکه برابر با یک عضوه. سکه‌هاتون رو جمع کنید و برای کانال/گروهتون خرج کنید!"
        )

# دستورات مدیر
def stats(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("❌ شما مدیر نیستید!")
        return

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    user_count = c.fetchone()[0]
    c.execute("SELECT channel_id FROM channels")
    channels = c.fetchall()
    c.execute("SELECT group_id FROM groups")
    groups = c.fetchall()
    conn.close()

    valid_channels = [ch[0] for ch in channels if check_admin_status(context, ch[0], ADMIN_ID)]
    valid_groups = [gr[0] for gr in groups if check_admin_status(context, gr[0], ADMIN_ID)]
    ad_count = len(valid_channels) + len(valid_groups)

    update.message.reply_text(
        f"📊 آمار بات:\n"
        f"👤 تعداد کاربران: {user_count}\n"
        f"📢 کانال‌های فعال: {len(valid_channels)}\n{chr(10).join(valid_channels) if valid_channels else 'هیچ‌کدام'}\n"
        f"👥 گروه‌های فعال: {len(valid_groups)}\n{chr(10).join(valid_groups) if valid_groups else 'هیچ‌کدام'}\n"
        f"📣 تعداد تبلیغات: {ad_count}"
    )

def broadcast_users(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("❌ شما مدیر نیستید!")
        return
    update.message.reply_text("📩 لطفاً پیامتون رو برای ارسال به کاربران بفرستید:")
    context.user_data["state"] = "awaiting_broadcast_users"

def broadcast_chats(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("❌ شما مدیر نیستید!")
        return
    update.message.reply_text("📩 لطفاً پیامتون رو برای ارسال به کانال‌ها و گروه‌ها بفرستید:")
    context.user_data["state"] = "awaiting_broadcast_chats"

def coin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("❌ شما مدیر نیستید!")
        return
    update.message.reply_text("💰 لطفاً آیدی عددی کاربر رو بفرستید:")
    context.user_data["state"] = "awaiting_coin_user_id"

def send_db(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("❌ شما مدیر نیستید!")
        return
    db_file = "bot.db"
    if os.path.exists(db_file):
        with open(db_file, "rb") as f:
            context.bot.send_document(chat_id=ADMIN_ID, document=f, filename="bot.db")
        update.message.reply_text("✅ فایل دیتابیس ارسال شد!")
    else:
        update.message.reply_text("❌ فایل دیتابیس پیدا نشد!")

def handle_admin_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return

    text = update.message.text
    state = context.user_data.get("state")

    if state == "awaiting_broadcast_users":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = c.fetchall()
        conn.close()

        for user in users:
            try:
                context.bot.send_message(chat_id=user[0], text=text)
            except:
                pass
        update.message.reply_text("✅ پیام به همه کاربران ارسال شد!")
        context.user_data["state"] = None

    elif state == "awaiting_broadcast_chats":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT channel_id FROM channels")
        channels = c.fetchall()
        c.execute("SELECT group_id FROM groups")
        groups = c.fetchall()
        conn.close()

        valid_chats = [ch[0] for ch in channels if check_admin_status(context, ch[0], user_id)] + \
                      [gr[0] for gr in groups if check_admin_status(context, gr[0], user_id)]

        for chat in valid_chats:
            try:
                context.bot.send_message(chat_id=chat, text=text)
            except:
                pass
        update.message.reply_text("✅ پیام به همه کانال‌ها و گروه‌ها ارسال شد!")
        context.user_data["state"] = None

    elif state == "awaiting_coin_user_id":
        try:
            target_user_id = int(text)
            update.message.reply_text("💰 لطفاً تعداد سکه‌ای که می‌خواهید به کاربر بدید رو بفرستید:")
            context.user_data["target_user_id"] = target_user_id
            context.user_data["state"] = "awaiting_coin_amount"
        except ValueError:
            update.message.reply_text("❌ لطفاً یه آیدی عددی معتبر بفرستید!")

    elif state == "awaiting_coin_amount":
        try:
            amount = int(text)
            target_user_id = context.user_data["target_user_id"]
            conn = sqlite3.connect("bot.db")
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, coins) VALUES (?, 0)", (target_user_id,))
            c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, target_user_id))
            conn.commit()
            conn.close()
            update.message.reply_text(f"✅ {amount} سکه به کاربر با آیدی {target_user_id} ارسال شد!")
            context.bot.send_message(chat_id=target_user_id, text=f"🎉 شما {amount} سکه از مدیر دریافت کردید!")
            context.user_data["state"] = None
        except ValueError:
            update.message.reply_text("❌ لطفاً یه عدد معتبر بفرستید!")

# استارت بات
def main():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda update, context: handle_text(update, context) if context.user_data.get("state") in ["awaiting_channel", "awaiting_group", "awaiting_channel_members", "awaiting_group_members", "awaiting_admin_check"] else handle_admin_message(update, context)))
    # دستورات مدیر
    dispatcher.add_handler(CommandHandler("stats", stats))
    dispatcher.add_handler(CommandHandler("broadcast_users", broadcast_users))
    dispatcher.add_handler(CommandHandler("broadcast_chats", broadcast_chats))
    dispatcher.add_handler(CommandHandler("coin", coin))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("db", send_db))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()