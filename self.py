import asyncio
import requests
from telethon import TelegramClient, events, Button
from self_config import self_config
from self_storage import Storage  # دیتابیس ابری

# ========= CONFIG =========
class Cfg:
    api_id = 24645053
    api_hash = "88c0167b74a24fac0a85c26c1f6d1991"
    bot_token = "8314662501:AAENsAlvyeGQJgxa2lvN-JI8VcDyes4nn_0"

    # آدرس وب‌سرویس لاگین (روی Render)
    login_server = "https://YOUR-LOGIN-SERVER.onrender.com"

cfg = Cfg()
STORAGE = Storage()  # استفاده از دیتابیس ابری

BOT_CLIENT = TelegramClient("bot", cfg.api_id, cfg.api_hash).start(bot_token=cfg.bot_token)


# ========= START PANEL =========
@BOT_CLIENT.on(events.NewMessage(pattern="/start"))
async def start_panel(event):
    user_id = event.message.sender_id

    # بارگذاری یا ایجاد کاربر
    data = STORAGE._user(user_id)

    # به‌روزرسانی پروفایل
    if not data["profile"].get("username"):
        try:
            user_entity = await event.client.get_entity(user_id)
            data["profile"]["name"] = user_entity.first_name or "کاربر"
            data["profile"]["username"] = user_entity.username or ""
            STORAGE.set_user_key(user_id, "profile", "name", data["profile"]["name"])
            STORAGE.set_user_key(user_id, "profile", "username", data["profile"]["username"])
        except:
            pass

    buttons = [
        [Button.inline("پروفایل من", b"profile")],
        [Button.inline("وضعیت ربات", b"bot_status")],
        [Button.inline("فعال‌سازی ربات", b"buy")]
    ]

    await event.respond(
        f"سلام {data['profile'].get('name')} 👋\nبه پنل خوش اومدی",
        buttons=buttons
    )


# ========= CALLBACK HANDLER =========
@BOT_CLIENT.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.query.user_id
    data = STORAGE._user(user_id)
    btn = event.data.decode("utf-8")

    if btn == "profile":
        p = data["profile"]
        await event.edit(
            f"🧑 پروفایل شما:\n\n"
            f"اسم: {p.get('name')}\n"
            f"آیدی: {p.get('id')}\n"
            f"یوزرنیم: @{p.get('username')}\n"
            f"نقش: {p.get('role')}\n"
            f"فعال: {'✅' if data.get('active') else '❌'}"
        )

    elif btn == "bot_status":
        msg = "✅ ربات شما فعال است" if data.get("active") else "❌ ربات شما هنوز فعال نشده"
        await event.edit(msg)

    elif btn == "buy":
        login_link = f"{cfg.login_server}/?uid={user_id}"
        await event.edit(
            f"🔐 برای فعال‌سازی ربات:\n\n"
            f"1️⃣ روی لینک بزن\n2️⃣ شماره خودت رو وارد کن\n3️⃣ کد تأیید رو بزن\n4️⃣ برگرد و روی «وضعیت ربات» بزن\n\n"
            f"🌐 لینک ورود:\n{login_link}"
        )


# ========= AUTO CHECK LOGIN (BACKGROUND) =========
async def check_users_activation():
    while True:
        await asyncio.sleep(10)
        # لیست کاربرهای موجود در دیتابیس
        for user_id in STORAGE.conn.execute("SELECT user_id FROM users").fetchall():
            user_id = user_id[0]
            data = STORAGE._user(user_id)
            if data.get("active"):
                continue

            try:
                r = requests.get(f"{cfg.login_server}/check/{user_id}", timeout=5)
                if r.status_code == 200:
                    res = r.json()
                    if res.get("status") == "verified":
                        STORAGE.set_user_key(user_id, "active", None, True)
                        STORAGE.set_user_key(user_id, "access_token", None, res.get("access_token"))
                        await BOT_CLIENT.send_message(int(user_id), "✅ ربات شما با موفقیت فعال شد!")
            except:
                pass


# ========= RUN =========
async def main():
    asyncio.create_task(check_users_activation())
    print("🤖 Bot is running...")
    await BOT_CLIENT.run_until_disconnected()


if __name__ == "__main__":
    BOT_CLIENT.loop.run_until_complete(main())
