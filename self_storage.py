# ============================================
# self_storage.py — دیتابیس ابری با Turso (Python)
# مدیریت کاربران، گروه‌ها، وضعیت بات و سکوت
# ============================================

import json
from turso_python import Database

# لینک دیتابیس Turso + auth token
DB_URL = "selfbot-tiam.aws-ap-northeast-1.turso.io"
AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjI1NTM1Mzc0NDYsImlhdCI6MTc2NDYxOTA0NiwiaWQiOiJiZmRiYjE5OS1iMGZjLTRkZDUtYWE4Zi00YThlNzg0OTQ5MzkiLCJyaWQiOiJmOThhODM0MC03NTMzLTQ5YjMtYjU0Zi01MjgzYmE5MGE5ZTcifQ.zDBp12oCw4o9Tu6IAyRkfti8IYGaBqQxEIPYuWDPzOfROLjj-F-UP3rLpIlJFFtSKr7hhLAkEOauKTOVzYr5AQ"

class Storage:
    def __init__(self):
        # اتصال به دیتابیس Turso
        self.db = Database(DB_URL, auth_token=AUTH_TOKEN)

        # ایجاد جداول اگر موجود نباشند
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            data TEXT
        );
        """)
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id TEXT PRIMARY KEY,
            data TEXT
        );
        """)
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS bot_status (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)

    # ================================
    # کاربران
    # ================================
    def _user(self, user_id):
        user_id = str(user_id)
        row = self.db.execute("SELECT data FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return json.loads(row[0])
        else:
            default = {
                "clock": {"timezone": "Asia/Tehran","bio_enabled": False,"name_enabled": False,"font_id": None},
                "silence": {"is_silenced": False,"expire_time": 0,"reason": ""},
                "block": {"is_blocked": False},
                "welcome": {"enabled": False,"message": ""},
                "status": {"online": True},
                "session_data": {}  # <-- اینجا داده سشن ذخیره می‌شود
            }
            self.db.execute("INSERT INTO users(user_id, data) VALUES (?, ?)", (user_id, json.dumps(default)))
            return default

    def get_user_key(self, user_id, section, key):
        user = self._user(user_id)
        return user.get(section, {}).get(key)

    def set_user_key(self, user_id, section, key, value):
        user = self._user(user_id)
        if section not in user:
            user[section] = {}
        user[section][key] = value
        self.db.execute("REPLACE INTO users(user_id, data) VALUES (?, ?)", (str(user_id), json.dumps(user)))

    # ================================
    # گروه‌ها
    # ================================
    def _group(self, chat_id):
        chat_id = str(chat_id)
        row = self.db.execute("SELECT data FROM groups WHERE chat_id = ?", (chat_id,)).fetchone()
        if row:
            return json.loads(row[0])
        else:
            default = {
                "welcome_enabled": False,
                "welcome_message": "",
                "muted_users": [],
                "blocked_users": [],
                "settings": {"max_warnings": 8,"auto_mute_time": 60}
            }
            self.db.execute("INSERT INTO groups(chat_id, data) VALUES (?, ?)", (chat_id, json.dumps(default)))
            return default

    def get_group_key(self, chat_id, key):
        group = self._group(chat_id)
        return group.get(key)

    def set_group_key(self, chat_id, key, value):
        group = self._group(chat_id)
        group[key] = value
        self.db.execute("REPLACE INTO groups(chat_id, data) VALUES (?, ?)", (str(chat_id), json.dumps(group)))

    # ================================
    # وضعیت بات
    # ================================
    def get_bot_status(self, key):
        row = self.db.execute("SELECT value FROM bot_status WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_bot_status(self, key, value):
        self.db.execute("REPLACE INTO bot_status(key, value) VALUES (?, ?)", (key, str(value)))
