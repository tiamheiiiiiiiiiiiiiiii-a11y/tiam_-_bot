# self_config.py
# نسخه کامل با پشتیبانی از چند اکانت، ساعت، تایمر، مدل‌های AI و News API

class self_config:
    def __init__(self):
        # =======================
        # تنظیمات مرکزی (API، HF، Bot)
        # =======================
        self.api_id = "24645053"
        self.api_hash = "88c0167b74a24fac0a85c26c1f6d1991"
        self.bot_token = "8314662501:AAENsAlvyeGQJgxa2lvN-JI8VcDyes4nn_0"
        self.hf_token = "a75a2caa67254c738aa1ce92f17beea1"
        self.owner_id  =  6433381392
        
        self.prefix = "!"
        self.bot_language = "fa"

        # =======================
        # News API
        # =======================
        self.news_api_key = "a75a2caa67254c738aa1ce92f17beea1"

        # =======================
        # مدل‌های هوش مصنوعی برای دستورات
        # =======================
        self.ai_models = {
            ".جواب": "HF_MODEL_TEXT",
            ".عکس": "HF_MODEL_IMAGE",
            ".گربه": "HF_MODEL_CAT",
            ".سگ": "HF_MODEL_DOG",
            ".تیام": "HF_MODEL_CHAT"
        }

        # =======================
        # ذخیره‌سازی داده‌ها
        # =======================
        self.storage = {
            "users": {},   # user_id: {profile, clock, timers, ai_prefs, ...}
            "bots": {},    # bot_account: {active, owner, coins_consumed}
            "sessions": {} # session data for each account
        }

        # =======================
        # اکانت‌ها (تا ۳۰ اکانت)
        # =======================
        self.ACCOUNTS = {f"account_{i+1}": 0 for i in range(2)}
        self.default_bot_account = None  # اکانت فعال خودکار

    # =======================
    # مدیریت News API
    # =======================
    def get_news_api_key(self):
        return self.news_api_key

    def set_news_api_key(self, key: str):
        self.news_api_key = key

    # =======================
    # مدیریت مدل‌های AI
    # =======================
    def get_ai_model(self, command):
        return self.ai_models.get(command, None)

    def set_ai_model(self, command, model_name):
        self.ai_models[command] = model_name

    # =======================
    # داده‌های کاربر
    # =======================
    def get_user_data(self, user_id):
        if user_id not in self.storage['users']:
            self.storage['users'][user_id] = {
                "clock": {"status": False, "target": "bio", "font_index": 0, "timezone": "Asia/Tehran"},
                "timers": {},
                "ai_prefs": {"default_model": ".تیام", "language": "fa"},
                "profile": {"bio": "", "username": "", "display_name": ""},
                "settings": {"notifications": True, "dark_mode": False}
            }
        return self.storage['users'][user_id]

    def set_user_data(self, user_id, data):
        self.storage['users'][user_id] = data

    # =======================
    # مدیریت ساعت کاربر
    # =======================
    def get_user_clock(self, user_id):
        return self.get_user_data(user_id).get("clock", {})

    def set_user_clock(self, user_id, key, value):
        user = self.get_user_data(user_id)
        clock = user.get("clock", {"status": False, "target": "bio", "font_index": 0, "timezone": "Asia/Tehran"})
        clock[key] = value
        user["clock"] = clock
        self.set_user_data(user_id, user)

    def toggle_clock(self, user_id, status: bool):
        self.set_user_clock(user_id, "status", status)

    # =======================
    # مدیریت تایمر کاربر
    # =======================
    def get_user_timers(self, user_id):
        return self.get_user_data(user_id).get("timers", {})

    def set_user_timer(self, user_id, name, timer_data):
        user = self.get_user_data(user_id)
        timers = user.get("timers", {})
        timers[name] = timer_data
        user["timers"] = timers
        self.set_user_data(user_id, user)

    def remove_user_timer(self, user_id, name):
        user = self.get_user_data(user_id)
        timers = user.get("timers", {})
        if name in timers:
            del timers[name]
        user["timers"] = timers
        self.set_user_data(user_id, user)

    # =======================
    # مدیریت تنظیمات شخصی کاربر
    # =======================
    def get_user_settings(self, user_id):
        return self.get_user_data(user_id).get("settings", {})

    def set_user_setting(self, user_id, key, value):
        user = self.get_user_data(user_id)
        settings = user.get("settings", {})
        settings[key] = value
        user["settings"] = settings
        self.set_user_data(user_id, user)

    # =======================
    # مدیریت پروفایل کاربر
    # =======================
    def get_user_profile(self, user_id):
        return self.get_user_data(user_id).get("profile", {})

    def set_user_profile(self, user_id, key, value):
        user = self.get_user_data(user_id)
        profile = user.get("profile", {})
        profile[key] = value
        user["profile"] = profile
        self.set_user_data(user_id, user)

    # =======================
    # مدیریت تنظیمات عمومی
    # =======================
    def get_prefix(self):
        return self.prefix

    def set_prefix(self, new_prefix: str):
        self.prefix = new_prefix

    def get_language(self):
        return self.bot_language

    def set_language(self, new_language: str):
        self.bot_language = new_language

    # =======================
    # مدیریت اکانت‌ها
    # =======================
    def detect_logged_in_account(self, user_id):
        for name, uid in self.ACCOUNTS.items():
            if uid == user_id:
                self.default_bot_account = name
                return name
        return None

    def set_account_userid(self, account_name, user_id):
        self.ACCOUNTS[account_name] = user_id

    def get_active_account(self):
        return self.default_bot_account

    # =======================
    # بررسی مالکیت دستور (Self-Mode)
    # =======================
    def is_authorized(self, user_id):
        if self.default_bot_account is None:
            return False
        owner_id = self.ACCOUNTS.get(self.default_bot_account)
        return owner_id == user_id

    # =======================
    # ریست کردن تنظیمات کاربر
    # =======================
    def reset_user(self, user_id):
        if user_id in self.storage['users']:
            del self.storage['users'][user_id]

    # =======================
    # خروجی خلاصه برای دیباگ
    # =======================
    def summary(self, user_id):
        user = self.get_user_data(user_id)
        return {
            "account": self.default_bot_account,
            "clock_status": user["clock"]["status"],
            "timezone": user["clock"]["timezone"],
            "timers": list(user["timers"].keys()),
            "language": user["ai_prefs"]["language"],
            "prefix": self.prefix
        }

# ========================
# لیست شهرها (به فارسی)
# ========================
city_timezones = {
    "تهران": "Asia/Tehran",
    "نیویورک": "America/New_York",
    "لندن": "Europe/London",
    "پاریس": "Europe/Paris",
    "مسکو": "Europe/Moscow",
    "دوبی": "Asia/Dubai",
    "توکیو": "Asia/Tokyo",
    "سئول": "Asia/Seoul",
    "دهلی": "Asia/Kolkata",
    "شانگهای": "Asia/Shanghai",
    "سیدنی": "Australia/Sydney",
    "استانبول": "Europe/Istanbul",
    "برلین": "Europe/Berlin",
    "لوس‌آنجلس": "America/Los_Angeles",
    "رم": "Europe/Rome",
    "قاهره": "Africa/Cairo",
    "ریاض": "Asia/Riyadh",
    "بغداد": "Asia/Baghdad",
    "باکو": "Asia/Baku",
    "آنکارا": "Europe/Istanbul",
    "پکن": "Asia/Shanghai",
    "مدرید": "Europe/Madrid",
    "آتن": "Europe/Athens",
    "تورنتو": "America/Toronto",
    "ونکوور": "America/Vancouver",
    "مکزیکوسیتی": "America/Mexico_City",
    "برازیلیا": "America/Sao_Paulo",
    "پراگ": "Europe/Prague",
    "کی‌یف": "Europe/Kyiv",
    "آمستردام": "Europe/Amsterdam"
}
