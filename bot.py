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
API_TOKEN = '7948017595:AAGfcem-UyxilXhHTYttvhWLnwoymBtRTgI'
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNubGNidGd6ZHhzYWN3amlwZ2duIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDU3NDMzMiwiZXhwIjoyMDg2MTUwMzMyfQ.v3SRkONLNlQw5LWhjo03u0fDce3EvWGBpJ02OGg5DEI"
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
    waiting_for_new_cat_name = State()
    
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
    await c.answer() # هذا السطر يخبر تليجرام أن الأمر وصل فيلغي التعليق فوراً
    await Form.waiting_for_cat_name.set()
    await c.message.answer("📝 اكتب اسم القسم الجديد (دين، عامة...):")
@dp.message_handler(state=Form.waiting_for_cat_name)
async def save_cat(message: types.Message, state: FSMContext):
    try:
        # 1. إرسال البيانات بشكل صحيح لتجنب خطأ 23502
        supabase.table("categories").insert({
            "name": message.text, 
            "created_by": str(message.from_user.id)
        }).execute()
        
        await state.finish()
        await message.answer(f"✅ تم حفظ القسم '{message.text}' بنجاح.")

        # 2. جلب الأقسام لعرضها فوراً كما طلبت
        res = supabase.table("categories").select("*").execute()
        categories = res.data

        kb = InlineKeyboardMarkup(row_width=1)
        if categories:
            for cat in categories:
                kb.add(InlineKeyboardButton(f"📂 {cat['name']}", callback_data=f"manage_questions_{cat['id']}"))
        
        kb.add(InlineKeyboardButton("⬅️ الرجوع", callback_data="custom_add"))
        await message.answer("📋 اختر القسم لإدارة الأسئلة:", reply_markup=kb)

    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("⚠️ حدث خطأ أثناء الحفظ، جرب مرة أخرى.")
        
# 1. نافذة إعدادات القسم عند الضغط على اسمه
@dp.callback_query_handler(lambda c: c.data.startswith('manage_questions_'))
async def manage_questions_window(c: types.CallbackQuery):
    await c.answer()
    cat_id = c.data.split('_')[-1]
    
    # جلب معلومات القسم وعدد الأسئلة
    cat_res = supabase.table("categories").select("name").eq("id", cat_id).single().execute()
    q_res = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
    
    cat_name = cat_res.data['name']
    q_count = q_res.count if q_res.count else 0

    txt = (f"⚙️ **إعدادات القسم: {cat_name}**\n\n"
           f"📊 عدد الأسئلة المضافة: {q_count}\n"
           f"ماذا تريد أن تفعل الآن؟")

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ إضافة سؤال مباشر", callback_data=f"add_q_{cat_id}"),
        InlineKeyboardButton("📝 تعديل اسم القسم", callback_data=f"edit_cat_{cat_id}")
    )
    kb.add(
        InlineKeyboardButton("🔍 عرض الأسئلة", callback_data=f"view_qs_{cat_id}"),
        InlineKeyboardButton("🗑️ حذف الأسئلة", callback_data=f"del_qs_menu_{cat_id}")
    )
    kb.add(InlineKeyboardButton("❌ حذف القسم", callback_data=f"confirm_del_cat_{cat_id}"))
    kb.add(
        InlineKeyboardButton("🔙 رجوع", callback_data="list_cats"),
        InlineKeyboardButton("🏠 التحكم الرئيسية", callback_data="back_to_control")
    )
    
    await c.message.edit_text(txt, reply_markup=kb)
    # --- 1. تعديل اسم القسم (تعديل الرسالة الحالية) ---
@dp.callback_query_handler(lambda c: c.data.startswith('edit_cat_'))
async def edit_category_start(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    cat_id = c.data.split('_')[-1]
    await state.update_data(edit_cat_id=cat_id)
    await Form.waiting_for_new_cat_name.set()
    
    # هنا السر: نقوم بتعديل نفس الرسالة بدلاً من إرسال رسالة جديدة
    await c.message.edit_text("📝 **نظام التعديل:**\n\nأرسل الآن الاسم الجديد للقسم:")
    
# --- 1. تعديل اسم القسم المطور (مع حذف الرسالة والرجوع التلقائي) ---
@dp.message_handler(state=Form.waiting_for_new_cat_name)
async def save_edited_category(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data['edit_cat_id']
    new_name = message.text
    
    # تحديث الاسم في Supabase
    supabase.table("categories").update({"name": new_name}).eq("id", cat_id).execute()
    
    # تنظيف الشات: حذف رسالة المستخدم "الاسم الجديد"
    try:
        await message.delete()
    except:
        pass

    await state.finish()
    
    # جلب البيانات المحدثة لإعادة عرض اللوحة
    cat_res = supabase.table("categories").select("name").eq("id", cat_id).single().execute()
    q_res = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
    q_count = q_res.count if q_res.count else 0
    
    txt = (f"⚙️ **إعدادات القسم: {cat_res.data['name']}**\n\n"
           f"✅ تم تحديث الاسم بنجاح!\n"
           f"📊 عدد الأسئلة المضافة: {q_count}\n"
           f"ماذا تريد أن تفعل الآن؟")

    # إعادة بناء الأزرار
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ إضافة سؤال مباشر", callback_data=f"add_q_{cat_id}"),
        InlineKeyboardButton("📝 تعديل اسم القسم", callback_data=f"edit_cat_{cat_id}")
    )
    kb.add(
        InlineKeyboardButton("🔍 عرض الأسئلة", callback_data=f"view_qs_{cat_id}"),
        InlineKeyboardButton("🗑️ حذف الأسئلة", callback_data=f"del_qs_menu_{cat_id}")
    )
    kb.add(InlineKeyboardButton("❌ حذف القسم", callback_data=f"confirm_del_cat_{cat_id}"))
    kb.add(
        InlineKeyboardButton("🔙 رجوع", callback_data="list_cats"),
        InlineKeyboardButton("🏠 التحكم الرئيسية", callback_data="back_to_control")
    )

    await message.answer(txt, reply_markup=kb)
# --- 3. نظام إضافة سؤال (إصلاح مشكلة التعليق والحذف المستمر) ---
@dp.callback_query_handler(lambda c: c.data.startswith('add_q_'))
async def start_add_question(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    cat_id = c.data.split('_')[-1]
    await state.update_data(current_cat_id=cat_id)
    await Form.waiting_for_question.set()
    await c.message.edit_text("❓ **نظام إضافة الأسئلة:**\n\nاكتب الآن السؤال الذي تريد إضافته:")

@dp.message_handler(state=Form.waiting_for_question)
async def process_q_text(message: types.Message, state: FSMContext):
    await state.update_data(q_content=message.text)
    try: await message.delete() 
    except: pass
    await Form.waiting_for_ans1.set()
    msg = await message.answer("✅ تم حفظ نص السؤال.\n\nالآن أرسل **الإجابة الصحيحة** الأولى:")
    await state.update_data(last_bot_msg_id=msg.message_id)

@dp.message_handler(state=Form.waiting_for_ans1)
async def process_first_ans(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(ans1=message.text)
    try:
        await message.delete()
        await bot.delete_message(message.chat.id, data['last_bot_msg_id'])
    except: pass
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ نعم، إضافة ثانية", callback_data="add_second_ans"),
        InlineKeyboardButton("❌ لا، إجابة واحدة فقط", callback_data="no_second_ans")
    )
    msg = await message.answer("هل تريد إضافة إجابة ثانية (بديلة) لهذا السؤال؟", reply_markup=kb)
    await state.update_data(last_bot_msg_id=msg.message_id)

# --- معالجة اختيار "نعم" + استقبال الإجابة الثانية ---
@dp.callback_query_handler(lambda c: c.data == 'add_second_ans', state='*')
async def add_second_ans_start(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await Form.waiting_for_ans2.set() # تفعيل الحالة الثانية
    await c.message.edit_text("📝 أرسل الآن **الإجابة الثانية** البديلة:")

@dp.message_handler(state=Form.waiting_for_ans2) # هذا المعالج هو الذي كان ينقصك
async def process_second_ans(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try: await message.delete() # حذف إجابتك الثانية
    except: pass
    
    # الحفظ في Supabase مع إجابتين
    supabase.table("questions").insert({
        "category_id": data['current_cat_id'],
        "question_content": data['q_content'],
        "correct_answer": data['ans1'],
        "alternative_answer": message.text,
        "created_by": str(message.from_user.id)
    }).execute()
    
    await finalize_and_stop_deleting(message, state, data['current_cat_id'])

# --- معالجة اختيار "لا" ---
@dp.callback_query_handler(lambda c: c.data == 'no_second_ans', state='*')
async def finalize_no_second(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()
    
    supabase.table("questions").insert({
        "category_id": data['current_cat_id'],
        "question_content": data['q_content'],
        "correct_answer": data['ans1'],
        "created_by": str(c.from_user.id)
    }).execute()
    
    try: await c.message.delete()
    except: pass
    await finalize_and_stop_deleting(c.message, state, data['current_cat_id'])

# الدالة السحرية التي تنهي الحالة وتظهر الزر
async def finalize_and_stop_deleting(message_obj, state, cat_id):
    await state.finish() # إيقاف الحالة فوراً (لن يحذف رسائلك بعدها)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⚙️ العودة للوحة إعدادات القسم", callback_data=f"manage_questions_{cat_id}"))
    await bot.send_message(message_obj.chat.id, "✅ تم إضافة السؤال والاجابات بنجاح!", reply_markup=kb)
    
# --- 2. حذف القسم مع التأكيد ---
@dp.callback_query_handler(lambda c: c.data.startswith('confirm_del_cat_'))
async def confirm_delete_cat(c: types.CallbackQuery):
    await c.answer()
    cat_id = c.data.split('_')[-1]
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ نعم، احذف", callback_data=f"final_del_cat_{cat_id}"),
        InlineKeyboardButton("❌ لا، تراجع", callback_data=f"manage_questions_{cat_id}")
    )
    await c.message.edit_text("⚠️ هل أنت متأكد من حذف هذا القسم نهائياً مع كل أسئلته؟", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('final_del_cat_'))
async def execute_delete_cat(c: types.CallbackQuery):
    cat_id = c.data.split('_')[-1]
    supabase.table("categories").delete().eq("id", cat_id).execute()
    await c.answer("🗑️ تم الحذف بنجاح", show_alert=True)
    # الرجوع لقائمة الأقسام الرئيسية
    await custom_add_menu(c)
    
@dp.callback_query_handler(lambda c: c.data == 'list_cats')
async def list_categories_for_questions(c: types.CallbackQuery):
    try:
        # جلب الأقسام التي تم حفظها بنجاح
        res = supabase.table("categories").select("*").execute()
        categories = res.data

        if not categories:
            await c.answer("⚠️ لا توجد أقسام مضافة حالياً", show_alert=True)
            return

        kb = InlineKeyboardMarkup(row_width=1)
        for cat in categories:
            # صنع زر لكل قسم لإضافة الأسئلة إليه
            kb.add(InlineKeyboardButton(f"📂 {cat['name']}", callback_data=f"manage_questions_{cat['id']}"))
        
        kb.add(InlineKeyboardButton("⬅️ الرجوع", callback_data="custom_add"))
        
        await c.message.edit_text("📋 اختر القسم لإدارة الأسئلة:", reply_markup=kb)

    except Exception as e:
        logging.error(f"Error: {e}")
        await c.answer("⚠️ حدث خطأ في عرض الأقسام")

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
    
    
