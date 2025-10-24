import telebot, json, os, time
from telebot import types

BOT_TOKEN = "8371780857:AAHWSfIa5dOEiq076qDonY2ugAYcnJTMqdg"
bot = telebot.TeleBot(BOT_TOKEN)

# ======= فایل‌ها =======
CHANNELS_FILE = "channels.json"
VERIFIED_FILE = "verified.json"
channels = json.load(open(CHANNELS_FILE)) if os.path.exists(CHANNELS_FILE) else {}
verified = json.load(open(VERIFIED_FILE)) if os.path.exists(VERIFIED_FILE) else {}
admins = [6433381392]

sent_messages = {}  # (chat_id, user_id) -> message_id
cooldown = {}       # جلوگیری از اسپم
step = {}           # مراحل ادمین
bot_start_time = time.time()  # زمان فعال شدن ربات

# ======= توابع کمکی =======
def save(f, d):
    try:
        json.dump(d, open(f,"w"), indent=2)
    except: pass

def fmt_link(x):
    x = str(x).strip()
    if x.startswith("https://t.me/"): return x
    if x.startswith("@"): return "https://t.me/"+x[1:]
    return "https://t.me/"+x

def verify_channel(link):
    try:
        chat = bot.get_chat(fmt_link(link))
        return chat.type == "channel"
    except:
        return False

def safe_get_member(chat, user):
    try:
        return bot.get_chat_member(chat, user)
    except:
        return None

def is_member(user_id, raw_link):
    try:
        link = fmt_link(raw_link).replace("https://t.me/", "@")
        m = safe_get_member(link, user_id)
        return bool(m and getattr(m,'status',None) in ("creator","administrator","member","restricted"))
    except:
        return False

def get_group_channels(gid):
    return channels.get(str(gid), [])

# ======= بررسی عضویت =======
def check_membership(group_id, user_id, user_name):
    key = (group_id, user_id)
    if key in cooldown and time.time()-cooldown[key]<2:
        return
    cooldown[key] = time.time()
    
    not_joined = []
    for c in get_group_channels(group_id):
        try:
            if not is_member(user_id, c.get("link","")):
                not_joined.append(c)
        except:
            not_joined.append(c)
    
    gid = str(group_id)
    if not not_joined:
        verified.setdefault(gid, [])
        if user_id not in verified[gid]:
            verified[gid].append(user_id)
            save(VERIFIED_FILE, verified)
        if key in sent_messages:
            try: bot.delete_message(group_id, sent_messages.pop(key))
            except: pass
        return True

    # ارسال پیام فقط یکبار
    if key in sent_messages:
        try:
            markup = types.InlineKeyboardMarkup()
            for c in not_joined:
                markup.add(types.InlineKeyboardButton(c.get("name","کانال"), url=fmt_link(c.get("link",""))))
            markup.add(types.InlineKeyboardButton("بررسی عضویت 🔁", callback_data="check_membership"))
            bot.edit_message_text(
                f"*{user_name} برای ارسال پیام ابتدا باید در کانال(ها) عضو شود!*",
                group_id,
                sent_messages[key],
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except: pass
        return False

    try:
        markup = types.InlineKeyboardMarkup()
        for c in not_joined:
            markup.add(types.InlineKeyboardButton(c.get("name","کانال"), url=fmt_link(c.get("link",""))))
        markup.add(types.InlineKeyboardButton("بررسی عضویت 🔁", callback_data="check_membership"))
        msg = bot.send_message(group_id, f"*{user_name} برای ارسال پیام ابتدا باید در کانال(ها) عضو شود!*",
                               reply_markup=markup, parse_mode="Markdown")
        sent_messages[key] = msg.message_id
    except:
        try:
            msg = bot.send_message(group_id, f"*{user_name} لطفاً کانال‌ها را بررسی کنید!*", parse_mode="Markdown")
            sent_messages[key] = msg.message_id
        except: pass
    return False

# ======= هندلر دکمه‌ها =======
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    try:
        if c.data=="check_membership":
            check_membership(c.message.chat.id, c.from_user.id, c.from_user.first_name)
            bot.answer_callback_query(c.id, "در حال بررسی...")
        elif c.data.startswith("delete_channel_"):
            index = int(c.data.split("_")[-1])
            gid = str(c.message.chat.id)
            if gid in channels and index < len(channels[gid]):
                removed = channels[gid].pop(index)
                save(CHANNELS_FILE, channels)
                bot.edit_message_text("کانال حذف شد ✅", c.message.chat.id, c.message.message_id)
    except: pass

# ======= پنل ادمین =======
@bot.message_handler(commands=["panel"])
def panel(m):
    if m.from_user.id not in admins: return
    try:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("افزودن دکمه جدید ➕", callback_data="add_channel"))
        # دکمه‌های حذف کانال
        gid = str(m.chat.id)
        for i, ch in enumerate(channels.get(gid, [])):
            kb.add(types.InlineKeyboardButton(f"❌ {ch['name']}", callback_data=f"delete_channel_{i}"))
        bot.send_message(m.chat.id, "پنل افزودن/حذف دکمه", reply_markup=kb)
    except: pass

@bot.message_handler(func=lambda mm: mm.from_user.id in admins)
def admin_steps(mm):
    try:
        uid = mm.from_user.id
        if uid in step:
            s = step[uid]
            if s["step"] == "name":
                s["name"] = mm.text
                s["step"] = "link"
                bot.send_message(mm.chat.id, "لینک یا @username کانال را ارسال کنید:")
            elif s["step"] == "link":
                if not verify_channel(mm.text):
                    bot.send_message(mm.chat.id,"❌ لینک کانال معتبر نیست. دوباره امتحان کنید.")
                    return
                add = channels.setdefault(str(mm.chat.id), [])
                add.append({"name": s.get("name","کانال"), "link": mm.text})
                save(CHANNELS_FILE, channels)
                bot.send_message(mm.chat.id,"کانال اضافه شد ✅")
                step.pop(uid)
    except: pass

# ======= پیام کاربران =======
@bot.message_handler(content_types=['new_chat_members'])
def welcome(msg):
    try:
        for u in msg.new_chat_members:
            check_membership(msg.chat.id, u.id, u.first_name)
    except: pass

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    try:
        gid, uid = m.chat.id, m.from_user.id
        # فقط پیام‌های بعد از فعال شدن ربات
        if m.date < bot_start_time:
            return

        ok = check_membership(gid, uid, m.from_user.first_name)
        if ok: return
        try: bot.delete_message(gid, m.message_id)
        except: pass
    except: pass

# ======= اجرا =======
print("Bot is running...")
bot.infinity_polling()
