# ============================================
# self_storage.py — دیتابیس ابری با Turso + ذخیره سشن
# مدیریت کاربران، گروه‌ها، وضعیت بات، سکوت و سشن تلگرام
# ============================================

import libsqlclient as sql
import json

# لینک دیتابیس Turso (libSQL)
DB_URL = "libsql://selfbot-tiam.aws-ap-northeast-1.turso.io?authToken=YOUR_AUTH_TOKEN"

class Storage:
    def __init__(self):
        self.conn = sql.connect(DB_URL)

        # ایجاد جداول اگر موجود نباشند
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            data TEXT
        );
        """)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id TEXT PRIMARY KEY,
            data TEXT
        );
        """)
        self.conn.execute("""
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
        row = self.conn.execute("SELECT data FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return json.loads(row[0])
        else:
            default = {
                "profile": {
                    "name": "کاربر",
                    "id": user_id,
                    "username": "",
                    "role": "عادی"
                },
                "session": None,  # مسیر یا داده سشن تلگرام
                "access_token": None,
                "active": False,
                "clock": {"timezone": "Asia/Tehran","bio_enabled": False,"name_enabled": False,"font_id": None},
                "silence": {"is_silenced": False,"expire_time": 0,"reason": ""},
                "block": {"is_blocked": False},
                "welcome": {"enabled": False,"message": ""},
                "status": {"online": True}
            }
            self.conn.execute("INSERT INTO users(user_id, data) VALUES (?, ?)", (user_id, json.dumps(default)))
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

    # ================================
    # ذخیره سشن کامل تلگرام
    # ================================
    def set_user_session(self, user_id, session_data):
        user = self._user(user_id)
        user['session'] = session_data  # می‌تواند path فایل .session یا json رشته‌ای باشد
        self.conn.execute("REPLACE INTO users(user_id, data) VALUES (?, ?)", (str(user_id), json.dumps(user)))

    def get_user_session(self, user_id):
        user = self._user(user_id)
        return user.get('session')

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
                "settings": {"max_warnings": 8,"auto_mute_time": 60}
            }
            self.conn.execute("INSERT INTO groups(chat_id, data) VALUES (?, ?)", (chat_id, json.dumps(default)))
            return default

    def get_group_key(self, chat_id, key):
        group = self._group(chat_id)
        return group.get(key)

    def set_group_key(self, chat_id, key, value):
        group = self._group(chat_id)
        group[key] = value
        self.conn.execute("REPLACE INTO groups(chat_id, data) VALUES (?, ?)", (str(chat_id), json.dumps(group)))

    # ================================
    # وضعیت بات
    # ================================
    def get_bot_status(self, key):
        row = self.conn.execute("SELECT value FROM bot_status WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_bot_status(self, key, value):
        self.conn.execute("REPLACE INTO bot_status(key, value) VALUES (?, ?)", (key, str(value)))
