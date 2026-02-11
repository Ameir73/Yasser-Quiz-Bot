import logging
import asyncio
import random
import time
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client

# --- البيانات الخاصة بياسر ---
API_TOKEN = '7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY'
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_secret_HNrHo_fDfAQ7KzOGdk8-HA_OXlxZ-cC"
OWNER_USERNAME = "@Ya_79k"
MY_TELEGRAM_URL = "https://t.me/Ya_79k"

# الربط بسوبابيس
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعداد البوت
bot = Bot(token=API_TOKEN, parse_mode="Markdown")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Form(StatesGroup):
    waiting_for_cat_name = State()
    waiting_for_question = State()
    waiting_for_ans1 = State()
    waiting_for_ans2 = State()

last_clicks = {} # للحذف بلمستين
selected_members = {} # لتخزين اختيارات الأعضاء مؤقتاً

# --- 1. الأوامر الأساسية ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_mention = message.from_user.mention
    welcome_txt = (
        f"مرحبا بك {user_mention} في بوت مسابقات كوين.\n\n"
        f"تستطيع الآن إضافة أقسامك الخاصة وقم بتهيئة المسابقات منها أو من أقسام المشتركين الآخرين.\n\n"
        f"أرسل (تحكم) للإعدادات | أرسل (مسابقة) للتشغيل"
    )
    await message.answer(welcome_txt)

@dp.message_handler(lambda m: m.text == "تحكم")
async def control_panel(message: types.Message):
    txt = (f"👋 أهلاً بك في أعدادات المسابقات المطور الخاص ببوت كوين\n"
           f"👑 المطور: [{OWNER_USERNAME}]({MY_TELEGRAM_URL})")
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("📝 إضافة مخصصة", callback_data="custom_add"),
        InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev"),
        InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz"),
        InlineKeyboardButton("📊 لوحة الصدارة", callback_data="leaderboard"),
        InlineKeyboardButton("🛑 إغلاق", callback_data="close_bot")
    )
    await message.answer(txt, reply_markup=kb, disable_web_page_preview=True)

# --- 2. إدارة الأقسام والأسئلة ---
@dp.callback_query_handler(lambda c: c.data == 'custom_add')
async def custom_add_menu(c: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="add_new_cat"),
        InlineKeyboardButton("📋 قائمة الأقسام", callback_data="list_cats"),
        InlineKeyboardButton("🔙 الرجوع صفحه التحكم", callback_data="back_to_control")
    )
    await c.message.edit_text("أهلاً بك في لوحة اعدادات أقسامك الخاصة:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == 'add_new_cat')
async def btn_add_cat(c: types.CallbackQuery):
    await Form.waiting_for_cat_name.set()
    await c.message.answer("📝 اكتب اسم القسم الجديد (دين، عامة...):")

@dp.message_handler(state=Form.waiting_for_cat_name)
async def save_cat(message: types.Message, state: FSMContext):
    supabase.table("categories").insert({"name": message.text, "created_by": message.from_user.id}).execute()
    await state.finish()
    await message.answer(f"✅ تم حفظ القسم بنجاح.")
    await control_panel(message)

# --- 3. نظام اختيار الأعضاء (المؤهلين >= 45 سؤال) ---
@dp.callback_query_handler(lambda c: c.data == 'members_cats')
async def list_eligible_members(c: types.CallbackQuery):
    # جلب المستخدمين الذين لديهم 45 سؤال أو أكثر عبر Supabase
    res = supabase.rpc('get_eligible_users').execute() # نفترض وجود دالة rpc أو استعلام تجميعي
    # إذا لم تكن الدالة موجودة، نستخدم استعلام الأسئلة يدوياً
    qs = supabase.table("questions").select("created_by").execute()
    counts = {}
    for q in qs.data:
        uid = q['created_by']
        counts[uid] = counts.get(uid, 0) + 1
    
    eligible_ids = [uid for uid, count in counts.items() if count >= 45]
    
    if not eligible_ids:
        return await c.answer("⚠️ لا يوجد أعضاء لديهم 45 سؤال أو أكثر حالياً.", show_alert=True)
    
    admin_id = c.from_user.id
    selected_members[admin_id] = []
    
    # جلب أسماء هؤلاء الأعضاء من جدول user_stats
    users_res = supabase.table("user_stats").select("user_id, name").in_("user_id", eligible_ids).execute()
    
    kb = generate_members_keyboard(users_res.data, [])
    await c.message.edit_text("اختر الأعضاء (أصحاب الأقسام > 45 سؤال):", reply_markup=kb)

def generate_members_keyboard(members, selected_list):
    kb = InlineKeyboardMarkup(row_width=2)
    for m in members:
        m_id = str(m['user_id'])
        mark = "✅ " if m_id in selected_list else ""
        kb.insert(InlineKeyboardButton(f"{mark}{m['name']}", callback_data=f"toggle_mem_{m_id}"))
    
    kb.add(InlineKeyboardButton("➡️ التالي (اختيار الأقسام)", callback_data="go_to_cats_selection"))
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz"))
    return kb

@dp.callback_query_handler(lambda c: c.data.startswith('toggle_mem_'))
async def toggle_member_selection(c: types.CallbackQuery):
    m_id = c.data.split('_')[-1]
    admin_id = c.from_user.id
    if admin_id not in selected_members: selected_members[admin_id] = []
    
    if m_id in selected_members[admin_id]:
        selected_members[admin_id].remove(m_id)
    else:
        selected_members[admin_id].append(m_id)
    
    # تحديث الواجهة فوراً
    res = supabase.table("user_stats").select("user_id, name").execute() # تبسيط للجلب
    kb = generate_members_keyboard(res.data, selected_members[admin_id])
    await c.message.edit_reply_markup(reply_markup=kb)

# --- 4. اختيار الأقسام (Category Selection) ---
@dp.callback_query_handler(lambda c: c.data == 'go_to_cats_selection')
async def list_selected_members_cats(c: types.CallbackQuery):
    admin_id = c.from_user.id
    chosen_ids = selected_members.get(admin_id, [])
    if not chosen_ids:
        return await c.answer("⚠️ يرجى اختيار عضو واحد على الأقل!", show_alert=True)
    
    res = supabase.table("categories").select("id, name").in_("created_by", chosen_ids).execute()
    kb = InlineKeyboardMarkup(row_width=1)
    for cat in res.data:
        kb.add(InlineKeyboardButton(cat['name'], callback_data=f"sel_cat_{cat['id']}"))
    
    kb.add(InlineKeyboardButton("✅ تم اختيار الأقسام", callback_data="setup_quiz"))
    await c.message.edit_text("الآن اختر الأقسام التي تريد تضمينها:", reply_markup=kb)

# --- 5. واجهة الإعدادات المزخرفة 🇵🇸 ---
@dp.callback_query_handler(lambda c: c.data == 'setup_quiz')
async def setup_quiz_panel(c: types.CallbackQuery):
    text = (
        "؜؜╮━━━━━━━━━━━━━╭\n"
        "                 *إعدادات المسابقة*\n"
        "؜╯━━━━━━━━━━━━━╰\n\n"
        "*طبيعة المنافسة*: خاصة👤\n"
        "                                          ━━━━━━━━━\n"
        "🇵🇸| اعتبــار:  السرعة🚀\n"
        "🇵🇸| الاسئلة:  20\n"
        "🇵🇸| النقـاط:  20  \n"
        "                                          ━━━━━━━━━\n"
        " [*نوع الاسئلة*] \n"
        "                                                 ━━━━━━━\n"
        "🇵🇸| مباشـــرة:  ✅\n"
        "🇵🇸| اختيارات:  \n"
        "🇵🇸| الكــــــــل:"
    )
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("👥 أقسام الأعضاء", callback_data="members_cats"),
        InlineKeyboardButton("👤 أقسامك الخاصة", callback_data="list_cats"),
        InlineKeyboardButton("🤖 أقسام البوت (تطوير)", callback_data="dev"),
        InlineKeyboardButton("🔙 رجوع", callback_data="back_to_control")
    )
    await c.message.edit_text(text, reply_markup=kb)

# --- الحذف بلمستين ---
@dp.callback_query_handler(lambda c: c.data.startswith('delq_'))
async def dbl_del(c: types.CallbackQuery):
    qid = c.data.split('_')[1]
    now = time.time()
    if c.from_user.id in last_clicks and qid in last_clicks[c.from_user.id] and now - last_clicks[c.from_user.id][qid] < 0.8:
        supabase.table("questions").delete().eq("id", qid).execute()
        await c.answer("🗑️ تم الحذف")
    else:
        last_clicks.setdefault(c.from_user.id, {})[qid] = now
        await c.answer("⚠️ اضغط مرة أخرى بسرعة!")

@dp.callback_query_handler(lambda c: c.data == 'back_to_control')
async def back_to_ctrl(c: types.CallbackQuery):
    await control_panel(c.message)

@dp.callback_query_handler(lambda c: c.data == 'close_bot')
async def close_msg(c: types.CallbackQuery):
    await c.message.delete()

if __name__ == '__main__':
    # إعداد السجلات (Logging) لمراقبة الأخطاء في Render
    logging.basicConfig(level=logging.INFO)
    print(f"🚀 البوت @Ya_79kbot بدأ العمل على نسخة متوافقة...")
    executor.start_polling(dp, skip_updates=True)
    
    
