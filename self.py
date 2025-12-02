import os
import json
import asyncio
import requests

from telethon import TelegramClient, events, Button
from self_config import self_config

# ========= CONFIG =========
class Cfg:
    api_id = 24645053
    api_hash = "88c0167b74a24fac0a85c26c1f6d1991"
    bot_token = "8314662501:AAENsAlvyeGQJgxa2lvN-JI8VcDyes4nn_0"

    # آدرس وب‌سرویس لاگین (روی Render)
    login_server = "https://YOUR-LOGIN-SERVER.onrender.com"

cfg = Cfg()

# ========= PATHS =========
USER_DATA_DIR = os.path.join(os.getcwd(), "user_data")
os.makedirs(USER_DATA_DIR, exist_ok=True)

BOT_CLIENT = TelegramClient("bot", cfg.api_id, cfg.api_hash).start(bot_token=cfg.bot_token)


# ========= USER STORAGE =========
def get_user_file(user_id):
    return os.path.join(USER_DATA_DIR, f"{user_id}.json")

def load_user_data(user_id):
    fp = get_user_file(user_id)
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as fr:
            return json.load(fr)
    return {"profile":{"name":"کاربر","id":user_id,"username":"","role":"عادی"},"access_token":None,"active":False}

def save_user_data(user_id, data):
    fp = get_user_file(user_id)
    with open(fp, "w", encoding="utf-8") as fw:
        json.dump(data, fw, ensure_ascii=False, indent=2)


# ========= START PANEL =========
@BOT_CLIENT.on(events.NewMessage(pattern="/start"))
async def start_panel(event):
    user_id = event.message.sender_id
    data = load_user_data(user_id)

    if not data["profile"].get("username"):
        try:
            user_entity = await event.client.get_entity(user_id)
            data["profile"]["name"] = user_entity.first_name or "کاربر"
            data["profile"]["username"] = user_entity.username or ""
            save_user_data(user_id, data)
        except:
            pass

    buttons = [
        [Button.inline("پروفایل من", b"profile")],
        [Button.inline("وضعیت ربات", b"bot_status")],
        [Button.inline("فعال‌سازی ربات", b"buy")]
    ]

    await event.respond(f"سلام {data['profile'].get('name')} 👋\nبه پنل خوش اومدی", buttons=buttons)


# ========= CALLBACK HANDLER =========
@BOT_CLIENT.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.query.user_id
    data = load_user_data(user_id)
    btn = event.data.decode("utf-8")

    if btn == "profile":
        p = data["profile"]
        await event.edit(
            f"🧑 پروفایل شما:\n\nاسم: {p.get('name')}\nآیدی: {p.get('id')}\nیوزرنیم: @{p.get('username')}\nنقش: {p.get('role')}\nفعال: {'✅' if data.get('active') else '❌'}"
        )

    elif btn == "bot_status":
        msg = "✅ ربات شما فعال است" if data.get("active") else "❌ ربات شما هنوز فعال نشده"
        await event.edit(msg)

    elif btn == "buy":
        login_link = f"{cfg.login_server}/?uid={user_id}"
        await event.edit(f"🔐 برای فعال‌سازی ربات:\n\n1️⃣ روی لینک بزن\n2️⃣ شماره خودت رو وارد کن\n3️⃣ کد تأیید رو بزن\n4️⃣ برگرد و روی «وضعیت ربات» بزن\n\n🌐 لینک ورود:\n{login_link}")


# ========= AUTO CHECK LOGIN (BACKGROUND) =========
async def check_users_activation():
    while True:
        await asyncio.sleep(10)
        for filename in os.listdir(USER_DATA_DIR):
            if not filename.endswith(".json"):
                continue

            user_id = filename.replace(".json", "")
            data = load_user_data(user_id)
            if data.get("active"):
                continue

            try:
                r = requests.get(f"{cfg.login_server}/check/{user_id}", timeout=5)
                if r.status_code == 200:
                    res = r.json()
                    if res.get("status") == "verified":
                        data["active"] = True
                        data["access_token"] = res.get("access_token")
                        save_user_data(user_id, data)
                        await BOT_CLIENT.send_message(int(user_id), "✅ ربات شما با موفقیت فعال شد!")
            except:
                pass


# ========= RUN =========
async def main():
    asyncio.create_task(check_users_activation())
    print("🤖 Bot is running on Render...")
    await BOT_CLIENT.run_until_disconnected()

if __name__ == "__main__":
    BOT_CLIENT.loop.run_until_complete(main())
