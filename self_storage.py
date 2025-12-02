# ============================================
# self_storage.py — دیتابیس ابری با Turso + libSQL
# مدیریت کاربران، گروه‌ها، وضعیت بات و سکوت
# ============================================

import libsql
import json
import os

# -----------------------------
# تنظیمات دیتابیس
# -----------------------------
DB_FILE = "storage.db"  # فایل محلی
DB_URL = "libsql://selfbot-tiam.aws-ap-northeast-1.turso.io"
AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjI1NTM1Mzc0NDYsImlhdCI6MTc2NDYxOTA0NiwiaWQiOiJiZmRiYjE5OS1iMGZjLTRkZDUtYWE4Zi00YThlNzg0OTQ5MzkiLCJyaWQiOiJmOThhODM0MC03NTMzLTQ5YjMtYjU0Zi01MjgzYmE5MGE5ZTcifQ.zDBp12oCw4o9Tu6IAyRkfti8IYGaBqQxEIPYuWDPzOfROLjj-F-UP3rLpIlJFFtSKr7hhLAkEOauKTOVzYr5AQ"

# اتصال به دیتابیس (local replica)
conn = libsql.connect(DB_FILE, sync_url=DB_URL, auth_token=AUTH_TOKEN)


# -----------------------------
# آماده‌سازی جداول
# -----------------------------
def init_tables():
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        data TEXT
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        chat_id TEXT PRIMARY KEY,
        data TEXT
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS bot_status (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    conn.commit()
    conn.sync()


init_tables()


# =================================================
# کلاس اصلی ذخیره‌سازی
# =================================================
class Storage:
    def __init__(self):
        self.conn = conn

    # ================================
    # کاربران
    # ================================
    def _user(self, user_id):
        user_id = str(user_id)
        row = self.conn.execute("SELECT data FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return json.loads(row[0])
        else:
            default = {
                "clock": {"timezone": "Asia/Tehran", "bio_enabled": False, "name_enabled": False, "font_id": None},
                "silence": {"is_silenced": False, "expire_time": 0, "reason": ""},
                "block": {"is_blocked": False},
                "welcome": {"enabled": False, "message": ""},
                "status": {"online": True}
            }
            self.conn.execute("INSERT INTO users(user_id, data) VALUES (?, ?)", (user_id, json.dumps(default)))
            self.conn.commit()
            self.conn.sync()
            return default

    def get_user_key(self, user_id, section, key):
        user = self._user(user_id)
        return user.get(section, {}).get(key)

    def set_user_key(self, user_id, section, key, value):
        user = self._user(user_id)
        if section not in user:
            user[section] = {}
        user[section][key] = value
        self.conn.execute("REPLACE INTO users(user_id, data) VALUES (?, ?)", (str(user_id), json.dumps(user)))
        self.conn.commit()
        self.conn.sync()

    # ================================
    # گروه‌ها
    # ================================
    def _group(self, chat_id):
        chat_id = str(chat_id)
        row = self.conn.execute("SELECT data FROM groups WHERE chat_id = ?", (chat_id,)).fetchone()
        if row:
            return json.loads(row[0])
        else:
            default = {
                "welcome_enabled": False,
                "welcome_message": "",
                "muted_users": [],
                "blocked_users": [],
                "settings": {"max_warnings": 8, "auto_mute_time": 60}
            }
            self.conn.execute("INSERT INTO groups(chat_id, data) VALUES (?, ?)", (chat_id, json.dumps(default)))
            self.conn.commit()
            self.conn.sync()
            return default

    def get_group_key(self, chat_id, key):
        group = self._group(chat_id)
        return group.get(key)

    def set_group_key(self, chat_id, key, value):
        group = self._group(chat_id)
        group[key] = value
        self.conn.execute("REPLACE INTO groups(chat_id, data) VALUES (?, ?)", (str(chat_id), json.dumps(group)))
        self.conn.commit()
        self.conn.sync()

    # ================================
    # وضعیت بات
    # ================================
    def get_bot_status(self, key):
        row = self.conn.execute("SELECT value FROM bot_status WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_bot_status(self, key, value):
        self.conn.execute("REPLACE INTO bot_status(key, value) VALUES (?, ?)", (key, str(value)))
        self.conn.commit()
        self.conn.sync()
