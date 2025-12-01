import os, json, asyncio
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError, PasswordHashInvalidError
from self_config import self_config

class Cfg:
    api_id = 24645053
    api_hash = "88c0167b74a24fac0a85c26c1f6d1991"
    bot_token = "
    8314662501:AAENsAlvyeGQJgxa2lvN-JI8VcDyes4nn_0"

cfg = Cfg()

# مسیر ذخیره داده‌ها روی Render
USER_DATA_DIR = os.path.join(os.getcwd(), "user_data")
SESSION_DIR = os.path.join(os.getcwd(), "sessions")
os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(SESSION_DIR, exist_ok=True)

BOT_CLIENT = TelegramClient("bot", cfg.api_id, cfg.api_hash).start(bot_token=cfg.bot_token)

# --------------------------
# مدیریت داده کاربران
# --------------------------
def get_user_file(user_id):
    return os.path.join(USER_DATA_DIR, f"{user_id}.json")

def load_user_data(user_id):
    fp = get_user_file(user_id)
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as fr:
            return json.load(fr)
    return {"profile":{"name":"کاربر","id":user_id,"username":"","role":"عادی"},"bots":[]}

def save_user_data(user_id, data):
    fp = get_user_file(user_id)
    with open(fp, "w", encoding="utf-8") as fw:
        json.dump(data, fw, ensure_ascii=False, indent=2)

# --------------------------
# هندلرها
# --------------------------
active_handlers = {}

def remove_handler(user_id, key):
    if user_id in active_handlers and key in active_handlers[user_id]:
        handler_info = active_handlers[user_id][key]
        if isinstance(handler_info, tuple):
            BOT_CLIENT.remove_event_handler(handler_info[0], handler_info[1])
        else:
            BOT_CLIENT.remove_event_handler(handler_info)
        del active_handlers[user_id][key]
        if user_id in active_handlers and not active_handlers[user_id]:
            del active_handlers[user_id]

# --------------------------
# پنل شروع
# --------------------------
@BOT_CLIENT.on(events.NewMessage(pattern="/start"))
async def start_panel(event):
    user_id = event.message.sender_id
    data = load_user_data(user_id)

    if not data['profile'].get('username'):
        try:
            user_entity = await event.client.get_entity(user_id)
            data['profile']['name'] = user_entity.first_name if user_entity.first_name else data['profile']['name']
            data['profile']['username'] = user_entity.username if user_entity.username else ""
            save_user_data(user_id, data)
        except:
            pass

    buttons = [
        [Button.inline("پروفایل من", b"profile")],
        [Button.inline("وضعیت ربات", b"bot_status")],
        [Button.inline("فعال‌سازی ربات", b"buy")]
    ]

    await event.respond(
        f"سلام {data['profile'].get('name','کاربر')}!\nبه پنل ربات خوش آمدید.",
        buttons=buttons
    )

# --------------------------
# هندلر CallbackQuery
# --------------------------
@BOT_CLIENT.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.query.user_id
    data = load_user_data(user_id)
    btn_data = event.data.decode("utf-8")

    if btn_data == "profile":
        profile = data["profile"]
        msg = f"""🧑 پروفایل شما:

اسم: {profile.get('name','')}
آیدی عددی: {profile.get('id','')}
یوزرنیم: {profile.get('username','')}
مقام: {profile.get('role','عادی')}
"""
        await event.edit(msg)

    elif btn_data == "bot_status":
        buttons = [[Button.inline("وضعیت"), Button.inline("شماره"), Button.inline("اسم ربات")]]
        for bot_info in data.get("bots", []):
            row = [
                Button.inline("🟢 روشن" if bot_info.get("active") else "🔴 خاموش", f"toggle_{bot_info['id']}".encode()),
                Button.inline(str(bot_info.get("phone","")), b"dummy"),
                Button.inline(bot_info.get("name","Bot"), b"dummy")
            ]
            buttons.append(row)
        await event.edit("📊 وضعیت ربات‌ها:", buttons=buttons)

    elif btn_data == "buy":
        await event.edit("🎉 لطفاً شماره خود را وارد کنید (مثال: +98912xxxxxxx):")
        remove_handler(user_id, "phone")

        async def receive_phone(ev):
            phone = ev.text.strip()
            remove_handler(user_id, "phone")
            await ev.respond("در حال ارسال درخواست کد تایید...")

            session_file = os.path.join(SESSION_DIR, f"user_{user_id}_{phone}.session")
            from telethon import TelegramClient as UserClient
            tg_client = UserClient(session_file, cfg.api_id, cfg.api_hash)
            await tg_client.connect()

            try:
                await tg_client.send_code_request(phone)
            except PhoneNumberInvalidError:
                await ev.respond("❌ شماره نامعتبر است. دوباره تلاش کنید.")
                await tg_client.disconnect()
                return
            except Exception as e:
                await ev.respond(f"❌ خطا: {e}")
                await tg_client.disconnect()
                return

            await ev.respond("لطفاً کد تایید را وارد کنید:")

            async def receive_code(code_ev):
                code = code_ev.text.strip()
                remove_handler(user_id, "code")
                try:
                    await tg_client.sign_in(phone, code)
                except PhoneCodeInvalidError:
                    await code_ev.respond("❌ کد اشتباه است. دوباره تلاش کنید.")
                    await tg_client.disconnect()
                    return
                except SessionPasswordNeededError:
                    await code_ev.respond("🔑 رمز دو مرحله‌ای لازم است. وارد کنید:")

                    async def receive_password(pw_ev):
                        password = pw_ev.text.strip()
                        remove_handler(user_id, "password")
                        try:
                            await tg_client.sign_in(password=password)
                        except PasswordHashInvalidError:
                            await pw_ev.respond("❌ رمز اشتباه است. دوباره تلاش کنید.")
                            await tg_client.disconnect()
                            return

                        await pw_ev.respond("✅ ربات فعال شد!")
                        user_info = await tg_client.get_me()
                        await tg_client.disconnect()

                        user_data = load_user_data(user_id)
                        user_data["bots"].append({
                            "id": len(user_data["bots"]) + 1,
                            "phone": phone,
                            "name": user_info.first_name if user_info.first_name else f"Bot_{len(user_data['bots'])+1}",
                            "active": True,
                            "session_file": session_file
                        })
                        save_user_data(user_id, user_data)

                    handler_pw = BOT_CLIENT.on(events.NewMessage(from_users=user_id))(receive_password)
                    active_handlers.setdefault(user_id, {})["password"] = handler_pw
                    return
                except Exception as e:
                    await code_ev.respond(f"❌ خطا: {e}")
                    await tg_client.disconnect()
                    return

                await code_ev.respond("✅ ربات فعال شد!")
                user_info = await tg_client.get_me()
                await tg_client.disconnect()

                user_data = load_user_data(user_id)
                user_data["bots"].append({
                    "id": len(user_data["bots"]) + 1,
                    "phone": phone,
                    "name": user_info.first_name if user_info.first_name else f"Bot_{len(user_data['bots'])+1}",
                    "active": True,
                    "session_file": session_file
                })
                save_user_data(user_id, user_data)

            handler_code = BOT_CLIENT.on(events.NewMessage(from_users=user_id))(receive_code)
            active_handlers.setdefault(user_id, {})["code"] = handler_code

        handler_phone = BOT_CLIENT.on(events.NewMessage(from_users=user_id))(receive_phone)
        active_handlers.setdefault(user_id, {})["phone"] = handler_phone

# --------------------------
# اجرای بات
# --------------------------
def run_bot():
    print("🤖 بات فعال شد و منتظر کاربران است...")
    BOT_CLIENT.run_until_disconnected()

if __name__ == "__main__":
    run_bot()
