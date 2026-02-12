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
API_TOKEN = '7948017595:AAHaIfhwWZdoksV6EADvhJnU_RXE7Wd5exs'
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

        # 1. جلب معرف المستخدم لفلترة الأقسام فوراً
        user_id = str(message.from_user.id)
        
        # 2. التعديل الجوهري: إضافة شرط .eq لكي تظهر أقسام المنشئ فقط
        res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
        categories = res.data

        kb = InlineKeyboardMarkup(row_width=1)
        if categories:
            for cat in categories:
                # هنا سيتم عرض أقسام عبير فقط ولن تظهر أقسامك
                kb.add(InlineKeyboardButton(f"📂 {cat['name']}", callback_data=f"manage_questions_{cat['id']}"))

        kb.add(InlineKeyboardButton("⬅️ الرجوع", callback_data="custom_add_menu"))
        await message.answer("📋 اختر أحد أقسامك لإدارة الأسئلة:", reply_markup=kb)

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
# --- 3. نظام إضافة سؤال (تنظيف شامل وإصلاح زر لا) ---
@dp.callback_query_handler(lambda c: c.data.startswith('add_q_'))
async def start_add_question(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    cat_id = c.data.split('_')[-1]
    await state.update_data(current_cat_id=cat_id)
    await Form.waiting_for_question.set()
    # تعديل الرسالة لطلب السؤال
    await c.message.edit_text("❓ **نظام إضافة الأسئلة:**\n\nاكتب الآن السؤال الذي تريد إضافته:")
    # حفظ ID هذه الرسالة لحذفها لاحقاً
    await state.update_data(last_bot_msg_id=c.message.message_id)

@dp.message_handler(state=Form.waiting_for_question)
async def process_q_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(q_content=message.text)
    
    # 1. حذف رسالة المستخدم و رسالة "نظام إضافة الأسئلة"
    try:
        await message.delete()
        await bot.delete_message(message.chat.id, data['last_bot_msg_id'])
    except: pass
    
    await Form.waiting_for_ans1.set()
    # 2. إرسال طلب الإجابة الأولى وحفظ ID الرسالة الجديدة
    msg = await message.answer("✅ تم حفظ نص السؤال.\n\nالآن أرسل **الإجابة الصحيحة** الأولى:")
    await state.update_data(last_bot_msg_id=msg.message_id)

@dp.message_handler(state=Form.waiting_for_ans1)
async def process_first_ans(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(ans1=message.text)
    
    # التعديل: البوت سيحذف فقط رسالة الشخص الذي يضيف السؤال
    try:
        # التأكد أن الشخص الذي أرسل الرسالة هو نفسه من يقوم بالإعداد
        if str(message.from_user.id) == data.get('creator_id') or message.from_user.id == message.from_user.id:
            await message.delete()
            if 'last_bot_msg_id' in data:
                await bot.delete_message(message.chat.id, data['last_bot_msg_id'])
    except: 
        pass
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ نعم، إضافة ثانية", callback_data="add_second_ans"),
        InlineKeyboardButton("❌ لا، إجابة واحدة فقط", callback_data="no_second_ans")
    )
    msg = await message.answer("هل تريد إضافة إجابة ثانية (بديلة) لهذا السؤال؟", reply_markup=kb)
    await state.update_data(last_bot_msg_id=msg.message_id)

# --- معالجة اختيار "نعم" ---
@dp.callback_query_handler(lambda c: c.data == 'add_second_ans', state='*')
async def add_second_ans_start(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await Form.waiting_for_ans2.set()
    # تعديل الرسالة الحالية لطلب الإجابة الثانية
    await c.message.edit_text("📝 أرسل الآن **الإجابة الثانية** البديلة:")

@dp.message_handler(state=Form.waiting_for_ans2)
async def process_second_ans(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data.get('current_cat_id')
    
    # إيقاف الحذف فوراً
    await state.finish()
    
    # حفظ في Supabase (تأكد من وجود العمود alternative_answer)
    supabase.table("questions").insert({
        "category_id": cat_id,
        "question_content": data.get('q_content'),
        "correct_answer": data.get('ans1'),
        "alternative_answer": message.text,
        "created_by": str(message.from_user.id)
    }).execute()
    
    # التعديل: البوت سيحذف فقط رسالة الشخص الذي يضيف السؤال
    try:
        # التأكد أن الشخص الذي أرسل الرسالة هو نفسه من يقوم بالإعداد
        if str(message.from_user.id) == data.get('creator_id') or message.from_user.id == message.from_user.id:
            await message.delete()
            if 'last_bot_msg_id' in data:
                await bot.delete_message(message.chat.id, data['last_bot_msg_id'])
    except: 
        pass
    
    await finalize_msg(message, cat_id)

# --- معالجة اختيار "لا" (تم الإصلاح) ---
@dp.callback_query_handler(lambda c: c.data == 'no_second_ans', state='*')
async def finalize_no_second(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()
    cat_id = data.get('current_cat_id')
    
    # إيقاف الحالة فوراً ليعمل الزر
    await state.finish()
    
    supabase.table("questions").insert({
        "category_id": cat_id,
        "question_content": data.get('q_content'),
        "correct_answer": data.get('ans1'),
        "created_by": str(c.from_user.id)
    }).execute()
    
    try: await c.message.delete()
    except: pass
    
    await finalize_msg(c.message, cat_id)

# دالة رسالة النجاح النهائية
async def finalize_msg(msg_obj, cat_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⚙️ العودة للوحة إعدادات القسم", callback_data=f"manage_questions_{cat_id}"))
    await bot.send_message(msg_obj.chat.id, "✅ تم إضافة السؤال بنجاح!", reply_markup=kb)

# --- 5. نظام عرض الأسئلة (يقرأ الإجابة البديلة) ---
@dp.callback_query_handler(lambda c: c.data.startswith('view_qs_'), state="*")
async def view_questions(c: types.CallbackQuery):
    await c.answer()
    cat_id = c.data.split('_')[-1]
    
    # جلب الأسئلة من Supabase
    questions = supabase.table("questions").select("*").eq("category_id", cat_id).execute()
    
    if not questions.data:
        await c.message.edit_text("⚠️ لا توجد أسئلة مضافة في هذا القسم حالياً.", 
                                  reply_markup=InlineKeyboardMarkup().add(
                                      InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_questions_{cat_id}")
                                  ))
        return

    txt = f"🔍 **قائمة الأسئلة:**\n\n"
    for i, q in enumerate(questions.data, 1):
        txt += f"❓ {i}- {q['question_content']}\n"
        txt += f"✅ ج1: {q['correct_answer']}\n"
        # التحقق من العمود الجديد
        if q.get('alternative_answer'):
            txt += f"💡 ج2: {q['alternative_answer']}\n"
        txt += "--- --- --- ---\n"

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🗑️ حذف الأسئلة", callback_data=f"del_qs_menu_{cat_id}"),
        InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_questions_{cat_id}")
    )
    await c.message.edit_text(txt, reply_markup=kb)

# --- 6. نظام حذف الأسئلة ---
@dp.callback_query_handler(lambda c: c.data.startswith('del_qs_menu_'), state="*")
async def delete_questions_menu(c: types.CallbackQuery):
    await c.answer()
    cat_id = c.data.split('_')[-1]
    questions = supabase.table("questions").select("*").eq("category_id", cat_id).execute()
    
    kb = InlineKeyboardMarkup(row_width=1)
    for q in questions.data:
        kb.add(InlineKeyboardButton(f"🗑️ حذف: {q['question_content'][:25]}...", 
                                    callback_data=f"pre_del_q_{q['id']}_{cat_id}"))
    
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_questions_{cat_id}"))
    await c.message.edit_text("🗑️ اختر السؤال المراد حذفه:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('pre_del_q_'), state="*")
async def confirm_delete_question(c: types.CallbackQuery):
    data = c.data.split('_')
    q_id, cat_id = data[3], data[4]
    
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ نعم، احذف", callback_data=f"final_del_q_{q_id}_{cat_id}"),
        InlineKeyboardButton("❌ تراجع", callback_data=f"del_qs_menu_{cat_id}")
    )
    await c.message.edit_text("⚠️ هل أنت متأكد من حذف هذا السؤال؟", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('final_del_q_'), state="*")
async def execute_delete_question(c: types.CallbackQuery):
    data = c.data.split('_')
    q_id, cat_id = data[3], data[4]
    
    # تنفيذ الحذف
    supabase.table("questions").delete().eq("id", q_id).execute()
    await c.answer("🗑️ تم الحذف بنجاح", show_alert=True)
    await delete_questions_menu(c)

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
        # 1. جلب معرف المستخدم الحالي (للتأكد من خصوصية الأقسام)
        user_id = str(c.from_user.id)
        
        # 2. طلب الأقسام التي تخص هذا المستخدم فقط باستخدام .eq()
        # هذا هو السطر الذي سيمنع عبير من رؤية أقسامك
        res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
        categories = res.data

        if not categories:
            await c.answer("⚠️ ليس لديك أقسام خاصة بك حالياً.", show_alert=True)
            return

        kb = InlineKeyboardMarkup(row_width=1)
        for cat in categories:
            # صنع زر لكل قسم خاص بالمستخدم فقط
            kb.add(InlineKeyboardButton(f"📂 {cat['name']}", callback_data=f"manage_questions_{cat['id']}"))

        kb.add(InlineKeyboardButton("⬅️ الرجوع", callback_data="custom_add_menu"))
        await c.message.edit_text("📋 اختر أحد أقسامك لإدارة الأسئلة:", reply_markup=kb)

    except Exception as e:
        logging.error(f"Filter Error: {e}")
        await c.answer("⚠️ حدث خطأ في تصفية الأقسام.")
        
def generate_members_keyboard(members, selected_list):
    kb = InlineKeyboardMarkup(row_width=2)
    for m in members:
        m_id = str(m['user_id'])
        mark = "✅ " if m_id in selected_list else ""
        kb.insert(InlineKeyboardButton(f"{mark}{m['name']}", callback_data=f"toggle_mem_{m_id}"))
    
    kb.add(InlineKeyboardButton("➡️ التالي (اختيار الأقسام)", callback_data="go_to_cats_selection"))
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz"))
    return kb

# --- 1. واجهة تهيئة المسابقة (متاحة للجميع) ---
@dp.callback_query_handler(lambda c: c.data == 'setup_quiz', state="*")
async def setup_quiz_main(c: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await c.answer()
    text = "🎉  أهلاً بك! قم بتهيئة المسابقة عن طريق اختيار أحد الخيارات التالية منهنا يمكنك بدا وتشعيل المسابقات:"
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("👥 أقسام الأعضاء (اختر من إبداعات الآخرين)", callback_data="members_setup_step1"),
        InlineKeyboardButton("👤 أقسامك الخاصة (التي أنشأتها أنت)", callback_data="my_setup_step1"),
        InlineKeyboardButton("🤖 أقسام البوت (قيد التطوير)", callback_data="bot_dev_msg"),
        InlineKeyboardButton("🔙 رجوع خطوة للخلف", callback_data="start_quiz") # الرجوع للقائمة الرئيسية
    )
    await c.message.edit_text(text, reply_markup=kb)

# --- 1.5 - جلب الأقسام الخاصة بالمستخدم (تم إصلاح خطأ slice) ---
@dp.callback_query_handler(lambda c: c.data == 'my_setup_step1', state="*")
async def start_private_selection(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    user_id = str(c.from_user.id)
    
    # جلب الأقسام التي أنشأتها أنت فقط
    res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
    
    if not res.data:
        await c.answer("⚠️ ليس لديك أقسام خاصة بك حالياً!", show_alert=True)
        return

    # حفظ الأقسام لبدء الاختيار (استخدمنا eligible_cats لتطابق دالة الرسم)
    await state.update_data(eligible_cats=res.data, selected_cats=[]) 
    
    # استدعاء دالة رسم الأقسام (الموجودة في السطر 538 في ملفك) ✅
    await render_categories_list(c.message, res.data, [])

    # حفظ الأقسام لبدء الاختيار
    await state.update_data(eligible_list=res.data, selected_members=[user_id]) 
    
    # استدعاء دالة الرسم الموجودة في السطر 480 عندك
    await render_members_list(c.message, res.data, [])
# --- 2. جلب المبدعين (15+ سؤال) ليختار منهم المستخدم ---
@dp.callback_query_handler(lambda c: c.data == "members_setup_step1", state="*")
async def start_member_selection(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    
    # جلب قائمة من أنشأوا أسئلة من Supabase
    res = supabase.table("questions").select("created_by").execute()
    
    if not res.data:
        await c.answer("⚠️ لا يوجد أعضاء لديهم أقسام منشورة حالياً.", show_alert=True)
        return

    from collections import Counter
    counts = Counter([q['created_by'] for q in res.data])
    
    # اختيار الأعضاء الذين لديهم 15 سؤال أو أكثر
    eligible_ids = [m_id for m_id, count in counts.items() if count >= 15]

    if not eligible_ids:
        await c.answer("⚠️ لا يوجد أعضاء حالياً وصلوا لـ 15 سؤال.", show_alert=True)
        return

    await state.update_data(eligible_list=eligible_ids, selected_members=[])
    await render_members_list(c.message, eligible_ids, [])

# --- 3. عرض القائمة العامة للاختيار ✅ ---
async def render_members_list(message, eligible_ids, selected_list):
    kb = InlineKeyboardMarkup(row_width=2)
    for m_id in eligible_ids:
        status = "✅ " if m_id in selected_list else ""
        # إظهار "المبدع" مع آخر 6 أرقام من هويته
        kb.insert(InlineKeyboardButton(f"{status}المبدع: {m_id[-6:]}", callback_data=f"toggle_mem_{m_id}"))
    
    # زر الانتقال للمرحلة التالية (سحب الأقسام)
    if selected_list:
        kb.add(InlineKeyboardButton(f"➡️ تم اختيار ({len(selected_list)}) .. عرض أقسامهم", callback_data="go_to_cats_step"))
    
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz"))
    
    await message.edit_text(
        "👥 **أقسام الأعضاء:**\nاختر المبدعين الذين تود رؤية أقسامهم وضمها لمسابقتك:", 
        reply_markup=kb
    )

# --- 4. منطق التبديل (Toggle) متاح للجميع ---
@dp.callback_query_handler(lambda c: c.data.startswith('toggle_mem_'), state="*")
async def toggle_member(c: types.CallbackQuery, state: FSMContext):
    m_id = c.data.replace('toggle_mem_', '')
    data = await state.get_data()
    selected = data.get('selected_members', [])
    eligible = data.get('eligible_list', [])

    if m_id in selected:
        selected.remove(m_id)
    else:
        selected.append(m_id)
    
    await state.update_data(selected_members=selected)
    await c.answer()
    await render_members_list(c.message, eligible, selected)

# --- 5. عرض الأقسام الخاصة بالمبدعين المختارين (المرحلة التالية) ---
@dp.callback_query_handler(lambda c: c.data == "go_to_cats_step", state="*")
async def show_selected_members_cats(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()
    chosen_ids = data.get('selected_members', [])
    
    if not chosen_ids:
        await c.answer("⚠️ يرجى اختيار مبدع واحد على الأقل!", show_alert=True)
        return

    # جلب الأقسام التابعة لهؤلاء المبدعين من Supabase
    res = supabase.table("categories").select("id, name").in_("created_by", chosen_ids).execute()
    
    if not res.data:
        await c.answer("⚠️ هؤلاء المبدعين ليس لديهم أقسام حالياً.", show_alert=True)
        return

    # تخزين الأقسام المتاحة والبدء بقائمة فارغة من المختار ✅
    await state.update_data(eligible_cats=res.data, selected_cats=[])
    await render_categories_list(c.message, res.data, [])

# --- 6. دالة رسم قائمة الأقسام مع علامة الصح ✅ ---
async def render_categories_list(message, eligible_cats, selected_cats):
    kb = InlineKeyboardMarkup(row_width=2)
    for cat in eligible_cats:
        # إذا كان القسم في قائمة المختارين يظهر بجانبه علامة صح ✅
        status = "✅ " if str(cat['id']) in selected_cats else ""
        kb.insert(InlineKeyboardButton(f"{status}{cat['name']}", callback_data=f"toggle_cat_{cat['id']}"))
    
    # يظهر زر "تم" للانتقال للإعدادات فقط إذا تم اختيار قسم واحد على الأقل
    if selected_cats:
        kb.add(InlineKeyboardButton(f"➡️ تم اختيار ({len(selected_cats)}) .. إعدادات المسابقة", callback_data="final_quiz_settings"))
    
    kb.add(InlineKeyboardButton("🔙 رجوع لاختيار المبدعين", callback_data="members_setup_step1"))
    
    await message.edit_text(
        "📂 **أقسام المبدعين المختارين:**\n"
        "اختر الأقسام التي تود حفظها وتشغيلها في مسابقتك:", 
        reply_markup=kb
    )

# --- 7. تبديل اختيار القسم (Toggle) للأقسام ---
@dp.callback_query_handler(lambda c: c.data.startswith('toggle_cat_'), state="*")
async def toggle_category_selection(c: types.CallbackQuery, state: FSMContext):
    cat_id = c.data.replace('toggle_cat_', '')
    data = await state.get_data()
    selected = data.get('selected_cats', [])
    eligible = data.get('eligible_cats', [])

    if cat_id in selected:
        selected.remove(cat_id)
    else:
        selected.append(cat_id)
    
    await state.update_data(selected_cats=selected)
    await c.answer()
    await render_categories_list(c.message, eligible, selected)

# --- السطر 559: بداية لوحة إعدادات المسابقة الاحترافية ---
@dp.callback_query_handler(lambda c: c.data == "final_quiz_settings", state="*")
async def final_quiz_settings_panel(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()
    
    # جلب القيم أو وضع قيم افتراضية
    q_time = data.get('quiz_time', 15)
    q_count = data.get('quiz_count', 10)
    q_mode = data.get('quiz_mode', 'السرعة ⚡')
    # تحديد نوع القسم بناءً على الاختيار السابق
    q_type = "خاص 👤" if data.get('selected_members') == [str(c.from_user.id)] else "عام 👥"

    # شاشة الرسالة المزخرفة فوق الأزرار
    text = (
        "أهلاً بك في \n"
        "┏━━━━━لوحة اعدادات المسابقه━━━━━┓\n"
        f"📌 عدد الاسئلة: {q_count} 📍\n"
        f"📁 نوع القسم: {q_type}\n"
        f"🔖 نظام الإجابة: {q_mode}\n"
        f"⏳ المهلة: {q_time} ثانية\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛"
    )

    kb = InlineKeyboardMarkup(row_width=3)
    
    # أزرار اختيار العدد (تفاعلية)
    kb.row(InlineKeyboardButton(f"📊 اختر عدد الأسئلة:", callback_data="ignore"))
    kb.row(
        InlineKeyboardButton(f"{'✅ ' if q_count==10 else ''}10", callback_data="set_count_10"),
        InlineKeyboardButton(f"{'✅ ' if q_count==20 else ''}20", callback_data="set_count_20"),
        InlineKeyboardButton(f"{'✅ ' if q_count==30 else ''}30", callback_data="set_count_30")
    )

    # زر الثواني (يتغير في نفس الزر عند الضغط)
    kb.row(InlineKeyboardButton(f"⏱️ المهلة: {q_time} ثانية", callback_data="cycle_time"))

    # نظام الإجابة والأقسام
    kb.row(
        InlineKeyboardButton(f"🔖 النظام: {q_mode}", callback_data="cycle_mode"),
        InlineKeyboardButton("⚙️ الأقسام الرسمية (قيد التطوير)", callback_data="bot_dev_msg")
    )

    # أزرار الحفظ والإغلاق
    kb.row(InlineKeyboardButton("💾 حفظ المسابقة الآن", callback_data="save_quiz_process"))
    kb.row(InlineKeyboardButton("❌ إغلاق النافذة", callback_data="close_window"))

    try:
        await c.message.edit_text(text, reply_markup=kb)
    except:
        pass

# --- محركات التغيير التفاعلية (توضع تحتها مباشرة) ---

@dp.callback_query_handler(lambda c: c.data == "cycle_time", state="*")
async def cycle_time(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current = data.get('quiz_time', 15)
    # 15 -> 20 -> 30 -> 45 -> 15
    next_time = 20 if current == 15 else (30 if current == 20 else (45 if current == 30 else 15))
    await state.update_data(quiz_time=next_time)
    await final_quiz_settings_panel(c, state)

@dp.callback_query_handler(lambda c: c.data.startswith('set_count_'), state="*")
async def set_count_direct(c: types.CallbackQuery, state: FSMContext):
    new_count = int(c.data.split('_')[-1])
    await state.update_data(quiz_count=new_count)
    await final_quiz_settings_panel(c, state)

@dp.callback_query_handler(lambda c: c.data == "cycle_mode", state="*")
async def cycle_mode(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current = data.get('quiz_mode', 'السرعة ⚡')
    next_mode = 'الوقت الكامل ⏳' if current == 'السرعة ⚡' else 'السرعة ⚡'
    await state.update_data(quiz_mode=next_mode)
    await final_quiz_settings_panel(c, state)
    # --- عملية الحفظ ---
@dp.callback_query_handler(lambda c: c.data == "save_quiz_process", state="*")
async def start_save(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await c.message.edit_text("📝 **يا بطل، أرسل الآن اسم المسابقة التي تريد حفظها:**\n(مثلاً: تحدي الأذكياء)")
    # نستخدم حالة مخصصة لاستقبال الاسم
    await state.set_state("wait_for_name")

@dp.message_handler(state="wait_for_name")
async def process_quiz_name(message: types.Message, state: FSMContext):
    quiz_name = message.text
    user_id = str(message.from_user.id)
    data = await state.get_data()
    
    # حفظ في سوبابيس (تأكد من وجود جدول باسم saved_quizzes)
    payload = {
        "created_by": user_id,
        "quiz_name": quiz_name,
        "time_limit": data.get('quiz_time', 15),
        "questions_count": data.get('quiz_count', 10),
        "mode": data.get('quiz_mode', 'السرعة ⚡'),
        "cats": [cat['id'] for cat in data.get('eligible_cats', [])]
    }
    supabase.table("saved_quizzes").insert(payload).execute()
    
    await message.answer(f"✅ **تم حفظ المسابقة ({quiz_name}) بنجاح!**\n\n🚀 لتشغيلها في أي وقت، أرسل كلمة: **مسابقة**")
    await state.finish()
    @dp.message_handler(lambda message: message.text == "مسابقة")
async def show_quizzes(message: types.Message):
    u_id = str(message.from_user.id)
    res = supabase.table("saved_quizzes").select("*").eq("created_by", u_id).execute()
    
    if not res.data:
        await message.answer("⚠️ ليس لديك مسابقات محفوظة باسمك.")
        return

    kb = InlineKeyboardMarkup(row_width=1)
    for q in res.data:
        # نربط الزر بـ ID صاحب الرسالة للحماية
        kb.add(InlineKeyboardButton(f"🎬 تشغيل: {q['quiz_name']}", callback_data=f"run_{q['id']}_{u_id}"))
    
    kb.add(InlineKeyboardButton("⚙️ الأقسام المختارة (قيد التطوير)", callback_data="bot_dev_msg"))
    kb.add(InlineKeyboardButton("❌ إغلاق النافذة", callback_data=f"close_{u_id}"))
    
    await message.reply(f"🎁 **مسابقاتك المحفوظة يا {message.from_user.first_name}:**", reply_markup=kb)

# حماية الأزرار
@dp.callback_query_handler(lambda c: c.data.startswith(('run_', 'close_')), state="*")
async def handle_secure(c: types.CallbackQuery):
    owner_id = c.data.split('_')[-1]
    if str(c.from_user.id) != owner_id:
        await c.answer("🚫 لا يسمح لك بلمس أزرار غيرك! اطلب مسابقتك بنفسك.", show_alert=True)
        return
    
    if "close" in c.data:
        await c.message.delete()
    else:
        await c.answer("🚀 جارٍ إطلاق المسابقة.. استعد!")
    # --- 1. محركات التصميم والزخرفة ---
async def countdown_timer(message: types.Message, seconds=5):
    text = "🚀 **تجهيز المسابقة...**\n\nستبدأ المسابقة خلال: {}"
    msg = await message.answer(text.format(seconds))
    for i in range(seconds - 1, 0, -1):
        await asyncio.sleep(1)
        await msg.edit_text(text.format(i))
    await asyncio.sleep(1)
    await msg.delete()

async def send_quiz_question(chat_id, q_data, current_num, total_num, settings):
    text = (
        "═════════════════════\n"
        f"🎓 الـمنـظـم: {settings['owner_name']}\n"
        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        f"📌 السؤال: « {current_num} » من « {total_num} » 📍\n"
        f"📁 نوع القسم: {settings['cat_name']}\n"
        f"🚀 نظام الإجابة: {settings['mode']}\n"
        f"⏳ المهلة: {settings['time_limit']} ثانية\n"
        f"✍️ الكاتب: {q_data.get('created_by_name', 'مبدع مجهول')}\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n"
        "  ╔════════════════════╗\n"
        "    ❓ السؤال هو :\n"
        f"« {q_data['question_text']} »\n\n"
        "══════════════════════"
    )
    return await bot.send_message(chat_id, text)

async def send_answer_summary(chat_id, correct_ans, extra_ans, winners, losers, overall_rank):
    winners_list = "\n".join([f"{i+1}- {w['name']} (+10)" for i, w in enumerate(winners)]) if winners else "لا يوجد"
    losers_list = "\n".join([f"{i+1}- {l['name']}" for i, l in enumerate(losers)]) if losers else "لا يوجد"
    
    ranks = ["🥇", "🥈", "🥉"]
    rank_text = ""
    for i, user in enumerate(overall_rank[:3]):
        rank_text += f"{ranks[i]} {user['name']} - {user['points']} نقطة\n"

    text = (
        f"✅ الإجابة الصحيحة: {correct_ans}\n"
        f"➕ إجابة إضافية: {extra_ans if extra_ans else 'لا يوجد'}\n"
        "━━━━━━━━━━━━━━\n"
        "╭─── قائمة المبدعين (صح) ✅ ───╮\n"
        f"{winners_list}\n"
        "╰──────────────────╯\n"
        "╭─── المحاولات القادمة (خطأ) ❌ ───╮\n"
        f"{losers_list}\n"
        "╰──────────────────╯\n"
        "╭─── الترتيب العام للمسابقة 📊 ───╮\n"
        f"{rank_text if rank_text else 'لا يوجد نقاط بعد'}"
        "╰──────────────────╯"
    )
    await bot.send_message(chat_id, text)
    # --- 2. محرك تشغيل المسابقة ---
active_quizzes = {}

async def run_quiz_logic(chat_id, quiz_data, owner_name):
    res = supabase.table("questions").select("*").in_("category_id", quiz_data['cats']).limit(quiz_data['questions_count']).execute()
    questions = res.data
    random.shuffle(questions)
    overall_scores = {}

    for i, q in enumerate(questions):
        active_quizzes[chat_id] = {"is_active": True, "correct_ans": q['answer_text'].strip(), "winners": [], "losers": []}
        settings = {'owner_name': owner_name, 'cat_name': "أقسامك الخاصة", 'mode': quiz_data['mode'], 'time_limit': quiz_data['time_limit']}
        
        await send_quiz_question(chat_id, q, i+1, len(questions), settings)
        
        start_time = time.time()
        while time.time() - start_time < quiz_data['time_limit']:
            await asyncio.sleep(0.1)
            if quiz_data['mode'] == 'السرعة ⚡' and not active_quizzes[chat_id]['is_active']:
                break

        active_quizzes[chat_id]['is_active'] = False
        
        # إضافة نقاط للفائزين وتحديث الترتيب
        for w in active_quizzes[chat_id]['winners']:
            uid = w['id']
            if uid not in overall_scores: overall_scores[uid] = {"name": w['name'], "points": 0}
            overall_scores[uid]['points'] += 10

        top_3 = sorted(overall_scores.values(), key=lambda x: x['points'], reverse=True)[:3]
        await send_answer_summary(chat_id, q['answer_text'], "", active_quizzes[chat_id]['winners'], active_quizzes[chat_id]['losers'], top_3)
        await asyncio.sleep(3)

    await bot.send_message(chat_id, "🏁 **انتهت المسابقة! تحية لكل المبدعين.**")
    # --- 3. محرك رصد الإجابات الذكي ---
@dp.message_handler(lambda message: not message.text.startswith('/'))
async def check_answers(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in active_quizzes or not active_quizzes[chat_id]['is_active']:
        return

    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_answer = message.text.strip()
    
    if user_answer == active_quizzes[chat_id]['correct_ans']:
        active_quizzes[chat_id]['is_active'] = False
        active_quizzes[chat_id]['winners'].append({"name": user_name, "id": user_id})
    else:
        if not any(l['id'] == user_id for l in active_quizzes[chat_id]['losers']):
            active_quizzes[chat_id]['losers'].append({"name": user_name, "id": user_id})
            
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
    
    
