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
        kb.insert(InlineKeyboardButton(f"{status} المبدع: {str(m_id)[-6:]}", callback_data=f"toggle_mem_{m_id}"))
        
    
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

# --- عملية الحفظ المفلترة ---
@dp.message_handler(state="wait_for_name")
async def process_quiz_name(message: types.Message, state: FSMContext):
    quiz_name = message.text
    user_id = str(message.from_user.id)
    data = await state.get_data()
    
    # جلب الأقسام المختارة فعلياً (التي بجانبها علامة الصح ✅)
    selected_ids = [int(i) for i in data.get('selected_cats', [])]

    if not selected_ids:
        await message.answer("⚠️ خطأ: لم تختار أي قسم! ارجع واختار قسم واحد على الأقل قبل الحفظ.")
        return

    payload = {
        "created_by": user_id,
        "quiz_name": quiz_name,
        "time_limit": data.get('quiz_time', 15),
        "questions_count": data.get('quiz_count', 10),
        "mode": data.get('quiz_mode', 'السرعة ⚡'),
        "cats": selected_ids  # تخزين دقيق للأقسام
    }
    
    try:
        supabase.table("saved_quizzes").insert(payload).execute()
        await message.answer(f"✅ **تم حفظ المسابقة ({quiz_name}) بنجاح!**\n\n🚀 لتشغيلها، أرسل كلمة: **مسابقة**")
        await state.finish()
    except Exception as e:
        logging.error(f"Save error: {e}")
        await message.answer(f"❌ حدث خطأ أثناء الحفظ.")

# --- [1] عرض القائمة الرئيسية (خرافية ومحمية) ---
@dp.message_handler(lambda message: message.text == "مسابقة")
async def show_quizzes(obj):
    user = obj.from_user
    u_id = str(user.id)
    
    # جلب المسابقات الخاصة بالمستخدم فقط
    res = supabase.table("saved_quizzes").select("*").eq("created_by", u_id).execute()
    kb = InlineKeyboardMarkup(row_width=1)
    
    if not res.data:
        msg_text = "⚠️ ليس لديك مسابقات محفوظة باسمك حالياً."
        if isinstance(obj, types.Message): await obj.answer(msg_text)
        else: await obj.message.edit_text(msg_text)
        return

    # عرض المسابقات مع تشفير معرف المالك u_id في كل زر
    for q in res.data:
        kb.add(InlineKeyboardButton(f"🏆 مسابقة: {q['quiz_name']}", callback_data=f"manage_quiz_{q['id']}_{u_id}"))
    
    kb.add(InlineKeyboardButton("🤖 أسئلة البوت (قيد التطوير)", callback_data=f"bot_dev_msg_{u_id}"))
    kb.add(InlineKeyboardButton("❌ إغلاق النافذة", callback_data=f"close_{u_id}"))
    
    title = f"🎁 **مسابقاتك المحفوظة يا {user.first_name}:**\nاختر المسابقة لإدارتها أو تعديلها:"
    if isinstance(obj, types.Message): await obj.reply(title, reply_markup=kb)
    else: await obj.message.edit_text(title, reply_markup=kb)

# ==========================================
# [2] المحرك الأمني ولوحة التحكم الشاملة (نسخة التلميح الذكي)
# ==========================================
@dp.callback_query_handler(lambda c: c.data.startswith(('run_', 'close_', 'confirm_del_', 'final_del_', 'edit_time_', 'set_t_', 'manage_quiz_', 'quiz_settings_', 'back_to_list', 'bot_dev_msg', 'edit_count_', 'set_c_', 'toggle_speed_', 'toggle_scope_', 'toggle_hint_')))
async def handle_secure_actions(c: types.CallbackQuery):
    try:
        data_parts = c.data.split('_')
        owner_id = data_parts[-1]
        user_id = str(c.from_user.id)

        # 🛑 الدرع الأمني: منع أي شخص من لمس أزرار غيره
        if user_id != owner_id:
            await c.answer("🚫 عذراً! هذه النافذة ليست لك. استدعِ مسابقتك الخاصة.", show_alert=True)
            return

        # --- شاشة إدارة المسابقة المختارة ---
        if c.data.startswith('manage_quiz_'):
            quiz_id = data_parts[2]
            res = supabase.table("saved_quizzes").select("quiz_name").eq("id", quiz_id).single().execute()
            kb = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("🚀 بدء المسابقة", callback_data=f"run_{quiz_id}_{user_id}"),
                InlineKeyboardButton("⚙️ إعدادات المسابقة", callback_data=f"quiz_settings_{quiz_id}_{user_id}"),
                InlineKeyboardButton("🔙 رجوع للقائمة", callback_data=f"back_to_list_{user_id}")
            )
            await c.message.edit_text(f"💎 **إدارة مسابقة: {res.data['quiz_name']}**\nيمكنك البدء الآن أو التحكم في الإعدادات أدناه:", reply_markup=kb)
            return

        # --- لوحة الإعدادات (نظام تغيير أسماء الأزرار تلقائياً) ---
        if c.data.startswith('quiz_settings_'):
            quiz_id = data_parts[2]
            res = supabase.table("saved_quizzes").select("*").eq("id", quiz_id).single().execute()
            q = res.data
            
            # تحديد المسميات بناءً على الحالة في قاعدة البيانات
            current_mode = q.get('mode', 'السرعة ⚡')
            speed_label = "⚡ نظام السرعة" if current_mode == "السرعة ⚡" else "⏳ نظام الوقت"
            
            current_scope = q.get('quiz_scope', 'خاص')
            scope_label = "🔒 مسابقة قروب" if current_scope == "خاص" else "🌐 مسابقة عامة"

            # زر التلميح الذكي الجديد
            is_hint_on = q.get('smart_hint', False)
            hint_label = "💡 تلميح ذكي: مفعل" if is_hint_on else "💡 تلميح ذكي: معطل"
            
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(
                InlineKeyboardButton(f"⏱️ الوقت: {q['time_limit']}ث", callback_data=f"edit_time_{quiz_id}_{user_id}"),
                InlineKeyboardButton(f"📊 الأسئلة: {q['questions_count']}", callback_data=f"edit_count_{quiz_id}_{user_id}")
            )
            kb.add(
                InlineKeyboardButton(speed_label, callback_data=f"toggle_speed_{quiz_id}_{user_id}"),
                InlineKeyboardButton(scope_label, callback_data=f"toggle_scope_{quiz_id}_{user_id}")
            )
            # إضافة زر التلميح في صف منفصل
            kb.add(InlineKeyboardButton(hint_label, callback_data=f"toggle_hint_{quiz_id}_{user_id}"))
            
            kb.add(InlineKeyboardButton("🗑️ حذف المسابقة", callback_data=f"confirm_del_{quiz_id}_{user_id}"))
            kb.add(InlineKeyboardButton("🔙 رجوع للخلف", callback_data=f"manage_quiz_{quiz_id}_{user_id}"))
            
            await c.message.edit_text(f"⚙️ **إعدادات المسابقة: {q['quiz_name']}**\nتحكم في طريقة عمل مسابقتك الخاصة:", reply_markup=kb)
            return

        # --- تفعيل/تعطيل التلميح الذكي (Smart Hint) ---
        if c.data.startswith('toggle_hint_'):
            quiz_id = data_parts[2]
            res = supabase.table("saved_quizzes").select("smart_hint").eq("id", quiz_id).single().execute()
            new_val = not res.data.get('smart_hint', False)
            supabase.table("saved_quizzes").update({"smart_hint": new_val}).eq("id", quiz_id).execute()
            await c.answer("✅ تفعيل التلميح" if new_val else "❌ تعطيل التلميح")
            await handle_secure_actions(c)
            return

        # --- تعديل عدد الأسئلة (الخيارات: 5، 10، 15، 20، 30، 40) ---
        if c.data.startswith('edit_count_'):
            quiz_id = data_parts[2]
            kb = InlineKeyboardMarkup(row_width=3)
            counts = [5, 10, 15, 20, 30, 40]
            for n in counts:
                kb.insert(InlineKeyboardButton(f"{n} سؤال", callback_data=f"set_c_{quiz_id}_{n}_{user_id}"))
            kb.add(InlineKeyboardButton("🔙 رجوع للإعدادات", callback_data=f"quiz_settings_{quiz_id}_{user_id}"))
            await c.message.edit_text("📊 **تعديل عدد الأسئلة:**\nاختر عدد الأسئلة الجديد لمسابقتك:", reply_markup=kb)
            return

        if c.data.startswith('set_c_'):
            quiz_id, count = data_parts[2], data_parts[3]
            supabase.table("saved_quizzes").update({"questions_count": int(count)}).eq("id", quiz_id).execute()
            await c.answer(f"✅ تم تغيير عدد الأسئلة إلى {count}")
            await handle_secure_actions(c) 
            return

        # --- تعديل الوقت ---
        if c.data.startswith('edit_time_'):
            quiz_id = data_parts[2]
            kb = InlineKeyboardMarkup(row_width=3)
            for t in [10, 15, 20, 30, 45]:
                kb.insert(InlineKeyboardButton(f"{t} ث", callback_data=f"set_t_{quiz_id}_{t}_{user_id}"))
            kb.add(InlineKeyboardButton("🔙 رجوع للإعدادات", callback_data=f"quiz_settings_{quiz_id}_{user_id}"))
            await c.message.edit_text("⏱️ **اختر وقت السؤال الجديد:**", reply_markup=kb)
            return

        if c.data.startswith('set_t_'):
            quiz_id, t = data_parts[2], data_parts[3]
            supabase.table("saved_quizzes").update({"time_limit": int(t)}).eq("id", quiz_id).execute()
            await c.answer(f"✅ تم ضبط الوقت: {t} ثانية")
            await handle_secure_actions(c)
            return

        # --- تبديل الأنظمة (تغيير اسم الزر تفاعلياً) ---
        if c.data.startswith('toggle_speed_'):
            quiz_id = data_parts[2]
            res = supabase.table("saved_quizzes").select("mode").eq("id", quiz_id).single().execute()
            new_mode = "الوقت ⏳" if res.data['mode'] == "السرعة ⚡" else "السرعة ⚡"
            supabase.table("saved_quizzes").update({"mode": new_mode}).eq("id", quiz_id).execute()
            await c.answer(f"🔄 تم التغيير إلى: {new_mode}")
            await handle_secure_actions(c) 
            return

        if c.data.startswith('toggle_scope_'):
            quiz_id = data_parts[2]
            res = supabase.table("saved_quizzes").select("quiz_scope").eq("id", quiz_id).single().execute()
            old_scope = res.data.get('quiz_scope', 'خاص')
            new_scope = "عام" if old_scope == "خاص" else "خاص"
            supabase.table("saved_quizzes").update({"quiz_scope": new_scope}).eq("id", quiz_id).execute()
            msg = "🌐 النوع الجديد: عام" if new_scope == "عام" else "🔒 النوع الجديد: قروب"
            await c.answer(msg)
            await handle_secure_actions(c) 
            return

        # --- نظام الرجوع والحذف والتشغيل ---
        if c.data.startswith('back_to_list'):
            await show_quizzes(c)
            return

        if c.data.startswith('run_'):
            await c.answer("🚀 جارٍ بدء المسابقة..")
            quiz_id = data_parts[1]
            res = supabase.table("saved_quizzes").select("*").eq("id", quiz_id).single().execute()
            q_data = res.data
            await countdown_timer(c.message, 5)
            quiz_config = {
                'cats': q_data.get('cats') or [],
                'questions_count': int(q_data.get('questions_count', 10)),
                'time_limit': int(q_data.get('time_limit', 15)),
                'mode': q_data.get('mode', 'السرعة ⚡'),
                'quiz_name': q_data.get('quiz_name', 'مسابقة'),
                'smart_hint': q_data.get('smart_hint', False) # إضافة حالة التلميح للإعدادات المشغلة
            }
            await c.message.edit_text(f"🏁 **انطلقت الآن: {quiz_config['quiz_name']}**")
            await start_quiz_engine(c.message.chat.id, quiz_config, c.from_user.first_name)
            return

        if c.data.startswith('confirm_del_'):
            quiz_id = data_parts[2]
            kb = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("✅ نعم، احذف", callback_data=f"final_del_{quiz_id}_{user_id}"),
                InlineKeyboardButton("🚫 تراجع", callback_data=f"quiz_settings_{quiz_id}_{user_id}")
            )
            await c.message.edit_text("⚠️ **تنبيه: هل أنت متأكد من حذف هذه المسابقة نهائياً؟**", reply_markup=kb)
            return

        if c.data.startswith('final_del_'):
            supabase.table("saved_quizzes").delete().eq("id", data_parts[2]).execute()
            await c.answer("🗑️ تم الحذف بنجاح")
            await show_quizzes(c)
            return

        if "close" in c.data:
            await c.message.delete()
            return

        if "bot_dev_msg" in c.data:
            await c.answer("🚧 قيد التطوير يا بطل!", show_alert=True)
            return

    except Exception as e:
        logging.error(f"Error in Secure Logic: {e}")
                                                        
# ==========================================
# 2. محركات التصميم والزخرفة والتلميح (نسخة الإشعارات العلوية الطائرة)
# ==========================================
async def countdown_timer(message: types.Message, seconds=5):
    try:
        for i in range(seconds, 0, -1):
            await message.edit_text(f"🚀 **تجهيز المسابقة...**\n\nستبدأ خلال: {i}")
            await asyncio.sleep(1)
    except Exception as e:
        logging.error(f"Countdown Error: {e}")

# --- [دالة توليد التلميح الذكي] ---
async def generate_smart_hint(answer_text):
    answer_text = str(answer_text).strip()
    words = answer_text.split()
    if len(words) == 1:
        if len(answer_text) <= 3:
            return f"💡 يبدأ بحرف ( {answer_text[0]} )"
        return f"💡 يبدأ بـ ( {answer_text[:2]} ) وينتهي بـ ( {answer_text[-1]} )"
    else:
        prompt = f"أعطني تلميحاً ذكياً وقصيراً جداً عن ({answer_text}) دون ذكر أي كلمة من الإجابة."
        try:
            ai_hint = await call_gemini_ai(prompt) 
            return f"💡 تلميح ذكي: {ai_hint}"
        except:
            return f"💡 {len(words)} كلمات، تبدأ بـ ( {answer_text[:2]} )"

async def send_quiz_question(chat_id, q_data, current_num, total_num, settings):
    text = (
        f"🎓 **الـمنـظـم:** {settings['owner_name']} ☁️☁️\n"
        f"┏━━━━━━━━━━━━━━┓\n"
        f"  📌 **سؤال:** « {current_num} » من « {total_num} » 📍\n"
        f"  📁 **قسم:** {settings['cat_name']} 📂\n"
        f"  🚀 **سرعة:** {settings['mode']} 🚀\n"
        f"  ⏳ **المهلة:** {settings['time_limit']} ثانية ⏳\n"
        f"┗━━━━━━━━━━━━━━┛\n\n"
        f"❓ **السؤال:**\n**{q_data['question_text']}**"
    )
    return await bot.send_message(chat_id, text, parse_mode='Markdown')

# ==========================================
# 3. محرك تشغيل المسابقة (المطور بنظام التلميح الطائر وإخفاء التثبيت)
# ==========================================
active_quizzes = {}

async def start_quiz_engine(chat_id, quiz_data, owner_name):
    try:
        cat_ids = [int(c) for c in quiz_data['cats'] if str(c).isdigit()]
        if not cat_ids:
            await bot.send_message(chat_id, "⚠️ خطأ: لم يتم تحديد أقسام لهذه المسابقة.")
            return

        cat_info = supabase.table("categories").select("name").in_("id", cat_ids).execute()
        cat_names_list = [item['name'] for item in cat_info.data]
        names_str = "، ".join(cat_names_list)

        res = supabase.table("questions") \
            .select("*, categories(name)") \
            .in_("category_id", cat_ids) \
            .limit(int(quiz_data['questions_count'])) \
            .execute()
        
        questions = res.data
        if not questions:
            await bot.send_message(chat_id, "⚠️ لم أجد أسئلة كافية في هذه الأقسام حالياً.")
            return

        welcome_msg = await bot.send_message(chat_id, f"🎯 **استعدوا للمنافسة!**\n📂 الأقسام: {names_str}\n🔢 الأسئلة: {len(questions)}")
        await asyncio.sleep(3)

        random.shuffle(questions)
        overall_scores = {}

        for i, q in enumerate(questions):
            q_text = q.get('question_content', 'نص مفقود')
            cat_name = q.get('categories', {}).get('name', 'عام')
            ans = q.get('correct_answer') or q.get('answer_text') or ""

            active_quizzes[chat_id] = {
                "active": True, 
                "ans": str(ans).strip(), 
                "winners": [], 
                "mode": quiz_data['mode'],
                "hint_sent": False
            }
            
            settings = {'owner_name': owner_name, 'mode': quiz_data['mode'], 'time_limit': quiz_data['time_limit'], 'cat_name': cat_name}
            # إرسال السؤال وحفظ الكائن الخاص بالرسالة
            q_msg = await send_quiz_question(chat_id, {'question_text': q_text}, i+1, len(questions), settings)
            
            start_time = time.time()
            time_limit = int(quiz_data['time_limit'])
            
            while time.time() - start_time < time_limit:
                await asyncio.sleep(0.1)
                
                                                # --- [منطق التلميح الطائر الحقيقي: إشعار علوي بدون أثر تثبيت] ---
                if quiz_data.get('smart_hint') and not active_quizzes[chat_id]['hint_sent']:
                    if (time.time() - start_time) >= (time_limit / 2):
                        # توليد التلميح عبر الذكاء الاصطناعي بناءً على الإجابة
                        hint_text = await generate_smart_hint(ans)
                        
                        # 1. إرسال الرسالة (هذا سيطلق إشعاراً طائراً لكل الأعضاء في المجموعة)
                        hint_msg = await bot.send_message(chat_id, f"💡 تلميح: {hint_text}")
                        active_quizzes[chat_id]['hint_sent'] = True
                        
                        # 2. حذف الرسالة فوراً (بعد 0.5 ثانية فقط)
                        # الإشعار سيبقى في أعلى شاشة اللاعب لعدة ثوانٍ لكنه لن يظهر في الشات أبداً
                        # وبذلك نتخلص نهائياً من جملة "ثبت البوت رسالة"
                        async def make_it_fly_away(msg, cid):
                            await asyncio.sleep(0.5) 
                            try:
                                await msg.delete() 
                            except: pass
                            
                        asyncio.create_task(make_it_fly_away(hint_msg, chat_id))

                if quiz_data['mode'] == 'السرعة ⚡' and not active_quizzes[chat_id]['active']:
                    break

            # --- نهاية السؤال ورصد النقاط ---
            active_quizzes[chat_id]['active'] = False
            for w in active_quizzes[chat_id]['winners']:
                overall_scores.setdefault(w['id'], {"name": w['name'], "points": 0})['points'] += 10

            await bot.send_message(chat_id, f"✅ الإجابة الصحيحة هي: **{ans}**")
            await asyncio.sleep(2)

        # النتائج النهائية
        leaderboard = sorted(overall_scores.values(), key=lambda x: x['points'], reverse=True)
        results_text = "🏆 **جدول الترتيب النهائي:**\n\n"
        
        if not leaderboard:
            results_text += "لم ينجح أحد! ❌"
        else:
            for idx, player in enumerate(leaderboard):
                medal = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else "👤"
                results_text += f"{medal} {player['name']} — {player['points']} نقطة\n"

        await bot.send_message(chat_id, results_text)
        
    except Exception as e:
        logging.error(f"Engine Error: {e}")

# ==========================================
# 4. رصد الإجابات (النسخة المصلحة كلياً)
# ==========================================
@dp.message_handler(lambda m: not m.text.startswith('/'))
async def check_ans(m: types.Message):
    cid = m.chat.id
    if cid in active_quizzes and active_quizzes[cid]['active']:
        # تنظيف الإجابة من المسافات وتحويلها للمطابقة
        user_ans = m.text.strip().lower()
        correct_ans = active_quizzes[cid]['ans'].lower()
        
        if user_ans == correct_ans:
            # منع تكرار نفس الفائز في السؤال الواحد
            if not any(w['id'] == m.from_user.id for w in active_quizzes[cid]['winners']):
                active_quizzes[cid]['winners'].append({"name": m.from_user.first_name, "id": m.from_user.id})
                
                # إشعار سريع بالفوز
                if active_quizzes[cid]['mode'] == 'السرعة ⚡':
                    active_quizzes[cid]['active'] = False
                    await m.reply("⚡ **إجابة صاروخية! أنت الأول.**")
                else:
                    await m.reply("✅ **إجابة صحيحة!**")
    
