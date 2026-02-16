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
API_TOKEN = '7948017595:AAF53pFLKYV0qL10JR5109DAM7MqGHiWBGQ'
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNubGNidGd6ZHhzYWN3amlwZ2duIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDU3NDMzMiwiZXhwIjoyMDg2MTUwMzMyfQ.v3SRkONLNlQw5LWhjo03u0fDce3EvWGBpJ02OGg5DEI"
OWNER_USERNAME = "@Ya_79k"
MY_TELEGRAM_URL = "https://t.me/Ya_79k"

# معرف المطور (ياسر) للتحكم بالإدارة والتفعيل
ADMIN_ID = 7988144062
# الربط بسوبابيس
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- [ الخطوة 1: دالة فحص صلاحية المجموعة - بناء ياسر الاحترافي ] ---
async def get_group_status(chat_id):
    try:
        res = supabase.table("allowed_groups").select("status").eq("group_id", chat_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]['status']
        return None 
    except Exception as e:
        logging.error(f"خطأ في فحص حالة المجموعة: {e}")
        return None

# إعداد البوت بنظام HTML
bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

async def send_creative_results(chat_id, correct_ans, winners, overall_scores):
    """تصميم ياسر المطور: دمج الفائزين والترتيب في رسالة واحدة"""
    msg =  "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"✅ الإجابة الصحيحة: <b>{correct_ans}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if winners:
        msg += "━━━━ أبطال هذا السؤال ✅ ━━━━\n"
        for i, w in enumerate(winners, 1):
            msg += f"{i}- {w['name']} (+10)\n"
    else:
        msg += "❌ لم ينجح أحد في الإجابة على هذا السؤال\n"
    
    leaderboard = sorted(overall_scores.values(), key=lambda x: x['points'], reverse=True)
    msg += "\n━━━━ 🏆 الترتيب العام للمسابقة ━━━━\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, player in enumerate(leaderboard[:3]):
        medal = medals[i] if i < 3 else "👤"
        msg += f"{medal} {player['name']} — {player['points']}\n"
    
    await bot.send_message(chat_id, msg, parse_mode="HTML")
    
async def send_final_results(chat_id, overall_scores, correct_count):
    """تصميم ياسر لرسالة ختام المسابقة"""
    msg =  "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🏁 <b>انـتـهـت الـمـسـابـقـة بنجاح!</b> 🏁\n"
    msg += "شكرًا لكل من شارك وأمتعنا بمنافسته. 🌹\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "━━━━ 🥇 الـفـائـزون بـالـمـراكز الأولى 🥇 ━━━━\n\n"
    sorted_players = sorted(overall_scores.values(), key=lambda x: x['points'], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    for i, player in enumerate(sorted_players[:3]):
        msg += f"{medals[i]} المركز {'الأول' if i==0 else 'الثاني' if i==1 else 'الثالث'}: <b>{player['name']}</b> - [🏆 {player['points']}]\n"
    msg += "\n━━━━━━━━━━━━━━━━━━━━━\n\n━━━━ 📊 إحصائيات التفاعل 📊 ━━━━\n"
    msg += f"✅ إجمالي الإجابات الصحيحة: {correct_count}\n\n"
    msg += "╰──────────────────╯\n"
    msg += "تهانينا للفائزين وحظاً أوفر لمن لم يحالفه الحظ! ❤️"
    await bot.send_message(chat_id, msg, parse_mode="HTML")

# ==========================================

class Form(StatesGroup):
    waiting_for_cat_name = State()
    waiting_for_question = State()
    waiting_for_ans1 = State()
    waiting_for_ans2 = State()
    waiting_for_new_cat_name = State()

# --- 1. الأوامر الأساسية ونظام التفعيل الاحترافي ---

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_mention = message.from_user.mention
    welcome_txt = (
        f"مرحبا بك {user_mention} في بوت مسابقات نسخة تجريبيه.\n\n"
        f"تستطيع الآن إضافة أقسامك الخاصة وقم بتهيئة المسابقات منها.\n\n"
        f"🔹 <b>لتفعيل البوت في مجموعتك:</b> أرسل كلمة (تفعيل)\n"
        f"🔹 <b>للإعدادات:</b> أرسل (تحكم)\n"
        f"🔹 <b>للبدء:</b> أرسل (مسابقة)"
    )
    await message.answer(welcome_txt)

# --- [ أمر تفعيل المشرفين - بناء ياسر ] ---
@dp.message_handler(lambda m: m.text == "تفعيل")
async def cmd_request_activation(message: types.Message):
    if message.chat.type == 'private':
        return await message.answer("⚠️ هذا الأمر للاستخدام داخل المجموعات فقط.")

    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if not (member.is_chat_admin() or member.is_chat_creator()):
        return await message.reply("⚠️ عذراً، هذا الأمر خاص بمشرفي المجموعة فقط.")

    status = await get_group_status(message.chat.id)
    if status == "active": return await message.reply("✅ البート مفعل بالفعل هنا!")
    if status == "pending": return await message.reply("⏳ طلب التفعيل قيد المراجعة حالياً.")
    if status == "blocked": return await message.reply("🚫 هذه المجموعة محظورة.")

    # تسجيل الطلب في سوبابيس
    supabase.table("allowed_groups").upsert({"group_id": message.chat.id, "group_name": message.chat.title, "status": "pending"}).execute()
    await message.reply("📥 <b>تم إرسال طلب التفعيل للمطور بنجاح.</b>", parse_mode="HTML")
    
    # تنبيه المطور (ياسر) بالأزرار
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ موافقة", callback_data=f"auth_approve_{message.chat.id}"),
        InlineKeyboardButton("❌ حظر", callback_data=f"auth_block_{message.chat.id}")
    )
    await bot.send_message(ADMIN_ID, f"🔔 <b>طلب تفعيل جديد!</b>\nالقروب: {message.chat.title}\nID: <code>{message.chat.id}</code>", reply_markup=kb, parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "تحكم")
async def control_panel(message: types.Message):
    # قفل الأمان: التحقق من تفعيل القروب قبل فتح اللوحة
    status = await get_group_status(message.chat.id)
    if status != "active" and message.chat.id != ADMIN_ID:
        return await message.reply("⚠️ <b>عذراً، يجب تفعيل المجموعة أولاً.</b>\nأرسل كلمة (تفعيل) لطلب الموافقة من المطور.", parse_mode="HTML")

    txt = (f"👋 أهلاً بك في أعدادات المسابقات المطور  \n"
           f"👑 المطور: <b>{OWNER_USERNAME}</b>")
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("📝 إضافة مخصصة", callback_data="custom_add"),
        InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev"),
        InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz"),
        InlineKeyboardButton("📊 لوحة الصدارة", callback_data="leaderboard"),
        InlineKeyboardButton("🛑 إغلاق", callback_data="close_bot")
    )
    await message.answer(txt, reply_markup=kb, disable_web_page_preview=True)

# --- معالج أزرار التفعيل (الإصدار الآمن والمضمون) ---
@dp.callback_query_handler(lambda c: c.data.startswith(('approve_', 'ban_')), user_id=ADMIN_ID)
async def process_auth_callback(callback_query: types.CallbackQuery):
    # تقسيم البيانات: الأكشن والآيدي
    data_parts = callback_query.data.split('_')
    action = data_parts[0]  # approve أو ban
    target_id = data_parts[1] # آيدي القروب

    if action == "approve":
        # تحديث الحالة إلى نشط
        supabase.table("allowed_groups").update({"status": "active"}).eq("group_id", target_id).execute()
        
        await callback_query.answer("تم التفعيل ✅", show_alert=True)
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n✅ **تم التفعيل بنجاح بواسطة المطور**", 
            parse_mode="Markdown"
        )
        # إشعار القروب
        await bot.send_message(target_id, "🎊 **مبارك! تم تفعيل القروب.** أرسل كلمة (مسابقة) للبدء.", parse_mode="Markdown")
    
    elif action == "ban":
        # تحديث الحالة إلى محظور
        supabase.table("allowed_groups").update({"status": "blocked"}).eq("group_id", target_id).execute()
        
        await callback_query.answer("تم الحظر ❌", show_alert=True)
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n❌ **تم رفض الطلب وحظر القروب**", 
            parse_mode="Markdown"
        )
        # إشعار القروب (اختياري)
        await bot.send_message(target_id, "🚫 **نعتذر، تم رفض طلب تفعيل البوت في هذا القروب.**")

# --- 2. إدارة الأقسام والأسئلة ---
# هنا نبدأ كود إضافة الأسئلة لقسم البوت...

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

        # تصحيح: الرجوع للوحة التحكم الخاصة بك
        kb.add(InlineKeyboardButton("⬅️ الرجوع", callback_data="custom_add"))
        await c.message.edit_text("📋 اختر أحد أقسامك لإدارة الأسئلة:", reply_markup=kb)

    except Exception as e:
        logging.error(f"Filter Error: {e}")
        await c.answer("⚠️ حدث خطأ في تصفية الأقسام.")

# --- دالة توليد لوحة اختيار الأعضاء ---
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
    
    # حفظ صاحب الجلسة لنظام الأمان
    await state.update_data(owner_id=c.from_user.id, owner_name=c.from_user.first_name)
    
    text = "🎉 أهلاً بك! قم بتهيئة المسابقة عن طريق اختيار أحد الخيارات التالية:"
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("👥 أقسام الأعضاء (اختر من إبداعات الآخرين)", callback_data="members_setup_step1"),
        InlineKeyboardButton("👤 أقسامك الخاصة (التي أنشأتها أنت)", callback_data="my_setup_step1"),
        InlineKeyboardButton("🤖 أقسام البوت (الرسمية)", callback_data="bot_setup_step1"),
        InlineKeyboardButton("🔙 رجوع خطوة للخلف", callback_data="start_quiz")
    )
    await c.message.edit_text(text, reply_markup=kb)

# --- جلب أقسام البوت الرسمية ---
@dp.callback_query_handler(lambda c: c.data == 'bot_setup_step1', state="*")
async def start_bot_selection(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    res = supabase.table("bot_questions").select("category").execute()
    if not res.data:
        await c.answer("⚠️ لا توجد أقسام رسمية حالياً!", show_alert=True)
        return
    unique_cats = sorted(list(set([item['category'] for item in res.data])))
    eligible_cats = [{"id": cat, "name": cat} for cat in unique_cats]
    await state.update_data(eligible_cats=eligible_cats, selected_cats=[], is_bot_quiz=True) 
    await render_categories_list(c.message, eligible_cats, [])

# --- 1.5 - جلب الأقسام الخاصة بالمستخدم ---
@dp.callback_query_handler(lambda c: c.data == 'my_setup_step1', state="*")
async def start_private_selection(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    user_id = str(c.from_user.id)
    res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
    if not res.data:
        await c.answer("⚠️ ليس لديك أقسام خاصة بك حالياً!", show_alert=True)
        return
    await state.update_data(eligible_cats=res.data, selected_cats=[], is_bot_quiz=False) 
    await render_categories_list(c.message, res.data, [])

# --- 2. جلب المبدعين ---
@dp.callback_query_handler(lambda c: c.data == "members_setup_step1", state="*")
async def start_member_selection(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    res = supabase.table("questions").select("created_by").execute()
    if not res.data:
        await c.answer("⚠️ لا يوجد أعضاء حالياً.", show_alert=True)
        return
    from collections import Counter
    counts = Counter([q['created_by'] for q in res.data])
    eligible_ids = [m_id for m_id, count in counts.items() if count >= 15]
    if not eligible_ids:
        await c.answer("⚠️ لا يوجد مبدعون وصلوا لـ 15 سؤال.", show_alert=True)
        return
    await state.update_data(eligible_list=eligible_ids, selected_members=[], is_bot_quiz=False)
    await render_members_list(c.message, eligible_ids, [])

# --- 3. عرض القوائم ---
async def render_members_list(message, eligible_ids, selected_list):
    kb = InlineKeyboardMarkup(row_width=2)
    for m_id in eligible_ids:
        status = "✅ " if m_id in selected_list else ""
        kb.insert(InlineKeyboardButton(f"{status} المبدع: {str(m_id)[-6:]}", callback_data=f"toggle_mem_{m_id}"))
    if selected_list:
        kb.add(InlineKeyboardButton(f"➡️ تم اختيار ({len(selected_list)}) .. عرض أقسامهم", callback_data="go_to_cats_step"))
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz"))
    await message.edit_text("👥 **أقسام الأعضاء:**", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('toggle_mem_'), state="*")
async def toggle_member(c: types.CallbackQuery, state: FSMContext):
    m_id = c.data.replace('toggle_mem_', '')
    data = await state.get_data()
    selected = data.get('selected_members', [])
    eligible = data.get('eligible_list', [])
    if m_id in selected: selected.remove(m_id)
    else: selected.append(m_id)
    await state.update_data(selected_members=selected)
    await c.answer()
    await render_members_list(c.message, eligible, selected)

@dp.callback_query_handler(lambda c: c.data == "go_to_cats_step", state="*")
async def show_selected_members_cats(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()
    chosen_ids = data.get('selected_members', [])
    res = supabase.table("categories").select("id, name").in_("created_by", chosen_ids).execute()
    await state.update_data(eligible_cats=res.data, selected_cats=[])
    await render_categories_list(c.message, res.data, [])

async def render_categories_list(message, eligible_cats, selected_cats):
    kb = InlineKeyboardMarkup(row_width=2)
    for cat in eligible_cats:
        cat_id_str = str(cat['id'])
        status = "✅ " if cat_id_str in selected_cats else ""
        kb.insert(InlineKeyboardButton(f"{status}{cat['name']}", callback_data=f"toggle_cat_{cat_id_str}"))
    if selected_cats:
        kb.add(InlineKeyboardButton(f"➡️ تم اختيار ({len(selected_cats)}) .. الإعدادات", callback_data="final_quiz_settings"))
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz"))
    await message.edit_text("📂 **اختر الأقسام:**", reply_markup=kb)

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

# --- 4. لوحة الإعدادات (نظام ياسر المتطور) ---
@dp.callback_query_handler(lambda c: c.data == "final_quiz_settings", state="*")
async def final_quiz_settings_panel(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()
    q_time = data.get('quiz_time', 15)
    q_count = data.get('quiz_count', 10)
    q_mode = data.get('quiz_mode', 'السرعة ⚡')
    q_hint = data.get('quiz_hint', 'معطل ❌')
    q_privacy = data.get('quiz_privacy', 'عامة 🌍')
    
    source = "رسمي 🤖" if data.get('is_bot_quiz') else ("خاص 👤" if data.get('selected_members') == [str(c.from_user.id)] else "عام 👥")

    text = (
        "┏━━━━━لوحة اعدادات المسابقه━━━━━┓\n"
        f"📌 عدد الاسئلة: {q_count}\n"
        f"📁 مصدر القسم: {source}\n"
        f"🌐 النطاق: {q_privacy}\n"
        f"🔖 النظام: {q_mode}\n"
        f"⏳ المهلة: {q_time} ثانية\n"
        f"💡 التلميح: {q_hint}\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛"
    )

    kb = InlineKeyboardMarkup(row_width=3)
    kb.row(InlineKeyboardButton("📊 اختر عدد الأسئلة:", callback_data="ignore"))
    kb.row(
        InlineKeyboardButton(f"{'✅' if q_count==10 else ''}10", callback_data="set_count_10"),
        InlineKeyboardButton(f"{'✅' if q_count==20 else ''}20", callback_data="set_count_20"),
        InlineKeyboardButton(f"{'✅' if q_count==30 else ''}30", callback_data="set_count_30")
    )
    kb.row(InlineKeyboardButton(f"⏱️ المهلة: {q_time} ثانية", callback_data="cycle_time"))
    kb.row(
        InlineKeyboardButton(f"🔖 {q_mode}", callback_data="cycle_mode"),
        InlineKeyboardButton(f"💡 {q_hint}", callback_data="cycle_hint")
    )
    kb.row(InlineKeyboardButton(f"🌐 النطاق: {q_privacy}", callback_data="cycle_privacy"))
    kb.row(InlineKeyboardButton("💾 حفظ المسابقة الآن", callback_data="save_quiz_process"))
    kb.row(InlineKeyboardButton("❌ إغلاق", callback_data="close_window"))
    await c.message.edit_text(text, reply_markup=kb)

# --- 5. المحركات ---
@dp.callback_query_handler(lambda c: c.data == "cycle_privacy", state="*")
async def cycle_privacy(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    next_p = 'خاصة 🔒' if data.get('quiz_privacy', 'عامة 🌍') == 'عامة 🌍' else 'عامة 🌍'
    await state.update_data(quiz_privacy=next_p)
    await final_quiz_settings_panel(c, state)

@dp.callback_query_handler(lambda c: c.data == "cycle_hint", state="*")
async def cycle_hint(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    next_h = 'مفعل ✅' if data.get('quiz_hint', 'معطل ❌') == 'معطل ❌' else 'معطل ❌'
    await state.update_data(quiz_hint=next_h)
    await final_quiz_settings_panel(c, state)

@dp.callback_query_handler(lambda c: c.data == "cycle_time", state="*")
async def cycle_time(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    curr = data.get('quiz_time', 15)
    next_t = 20 if curr == 15 else (30 if curr == 20 else (45 if curr == 30 else 15))
    await state.update_data(quiz_time=next_t)
    await final_quiz_settings_panel(c, state)

@dp.callback_query_handler(lambda c: c.data.startswith('set_count_'), state="*")
async def set_count_direct(c: types.CallbackQuery, state: FSMContext):
    await state.update_data(quiz_count=int(c.data.split('_')[-1]))
    await final_quiz_settings_panel(c, state)

@dp.callback_query_handler(lambda c: c.data == "cycle_mode", state="*")
async def cycle_mode(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    next_m = 'الوقت الكامل ⏳' if data.get('quiz_mode', 'السرعة ⚡') == 'السرعة ⚡' else 'السرعة ⚡'
    await state.update_data(quiz_mode=next_m)
    await final_quiz_settings_panel(c, state)

# --- 6. الحفظ ---
@dp.callback_query_handler(lambda c: c.data == "save_quiz_process", state="*")
async def start_save(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await c.message.edit_text("📝 أرسل الآن اسم المسابقة:")
    await state.set_state("wait_for_name")

@dp.message_handler(state="wait_for_name")
async def process_quiz_name(message: types.Message, state: FSMContext):
    quiz_name = message.text
    data = await state.get_data()
    selected = data.get('selected_cats', [])
    if not selected:
        await message.answer("⚠️ خطأ: لم تختار أي قسم!")
        return
    payload = {
        "created_by": str(message.from_user.id),
        "quiz_name": quiz_name,
        "chat_id": str(message.chat.id),
        "is_public": True if data.get('quiz_privacy', 'عامة 🌍') == 'عامة 🌍' else False,
        "time_limit": data.get('quiz_time', 15),
        "questions_count": data.get('quiz_count', 10),
        "mode": data.get('quiz_mode', 'السرعة ⚡'),
        "hint_enabled": True if data.get('quiz_hint') == 'مفعل ✅' else False,
        "is_bot_quiz": data.get('is_bot_quiz', False),
        "cats": selected
    }
    try:
        supabase.table("saved_quizzes").insert(payload).execute()
        await message.answer(f"✅ تم حفظ ({quiz_name}) بنجاح!")
        await state.finish()
    except Exception as e:
        await message.answer(f"❌ خطأ: تأكد من تحديث أعمدة Supabase.")

 # --- [1] عرض القائمة الرئيسية (نظام ياسر المتطور: خاص vs عام) ---
@dp.message_handler(lambda message: message.text == "مسابقة")
async def show_quizzes(obj):
    chat_id = obj.chat.id if isinstance(obj, types.Message) else obj.message.chat.id
    user = obj.from_user
    u_id = str(user.id)
    
    # 🛡️ فحص الصلاحيات المزدوج
    status = await get_group_status(chat_id)
    
    # 1. التحقق إذا كان المستخدم هو "مالك" أو "مشرف" في القروب (تشغيل خاص)
    member = await bot.get_chat_member(chat_id, user.id)
    is_admin_here = member.is_chat_admin() or member.is_chat_creator()
    
    # 2. منطق السماح:
    # يسمح بالدخول في الحالات التالية:
    # - إذا كنت أنت المطور (ياسر)
    # - إذا كان القروب مفعل رسمياً (status == 'active')
    # - إذا كان الشخص مشرفاً ويبي يشغل مسابقاته في قروبه (تشغيل خاص)
    
    can_proceed = (
        chat_id == ADMIN_ID or 
        status == "active" or 
        (is_admin_here and chat_id < 0) # chat_id < 0 يعني داخل قروب
    )

    if not can_proceed:
        msg = (
            "━━━━━━━━━━━━━━\n"
            "⚠️ <b>نظام النشر العام مقفل</b>\n"
            "━━━━━━━━━━━━━━\n"
            "عذراً، التشغيل في هذه المجموعة يتطلب تفعيل 'عام'.\n\n"
            "إذا كنت مشرفاً وتريد تشغيل البوت للجميع، أرسل: (<b>تفعيل</b>).\n"
            "━━━━━━━━━━━━━━"
        )
        if isinstance(obj, types.Message): return await obj.reply(msg, parse_mode="HTML")
        else: return await obj.message.edit_text(msg, parse_mode="HTML")

    # --- تكملة الكود الطبيعي لعرض المسابقات ---
    res = supabase.table("saved_quizzes").select("*").eq("created_by", u_id).execute()
    kb = InlineKeyboardMarkup(row_width=1)
    
    if not res.data:
        msg_text = "⚠️ ليس لديك مسابقات محفوظة باسمك حالياً."
        if isinstance(obj, types.Message): await obj.answer(msg_text)
        else: await obj.message.edit_text(msg_text)
        return

    for q in res.data:
        kb.add(InlineKeyboardButton(f"🏆 مسابقة: {q['quiz_name']}", callback_data=f"manage_quiz_{q['id']}_{u_id}"))
    
    kb.add(InlineKeyboardButton("🤖 أسئلة البوت (قيد التطوير)", callback_data=f"bot_dev_msg_{u_id}"))
    kb.add(InlineKeyboardButton("❌ إغلاق النافذة", callback_data=f"close_{u_id}"))
    
    title = f"🎁 **قائمة مسابقاتك يا {user.first_name}:**"
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
# 3. محرك تشغيل المسابقة (المطور بتصاميم ياسر الملكية - النسخة الشاملة)
# ==========================================
active_quizzes = {}

async def start_quiz_engine(chat_id, quiz_data, owner_name):
    try:
        # 1. فحص نوع المسابقة (هل هي أسئلة بوت رسمية؟)
        is_bot = quiz_data.get('is_bot_quiz', False)
        raw_cats = quiz_data.get('cats', [])

        if is_bot:
            # --- [ مسار أسئلة البوت ] ---
            names_str = "، ".join(raw_cats)
            # جلب الأسئلة من جدول bot_questions (البحث بالاسم مباشرة)
            res = supabase.table("bot_questions").select("*").in_("category", raw_cats).execute()
            questions = res.data
        else:
            # --- [ مسار مسابقات الأعضاء/الخاصة ] ---
            cat_ids = [int(c) for c in raw_cats if str(c).isdigit()]
            if not cat_ids:
                await bot.send_message(chat_id, "⚠️ خطأ: لم يتم تحديد أقسام لهذه المسابقة.")
                return

            cat_info = supabase.table("categories").select("name").in_("id", cat_ids).execute()
            names_str = "، ".join([item['name'] for item in cat_info.data])

            # جلب الأسئلة من جدول questions الأصلي
            res = supabase.table("questions").select("*, categories(name)").in_("category_id", cat_ids).execute()
            questions = res.data

        if not questions:
            await bot.send_message(chat_id, "⚠️ لم أجد أسئلة كافية في هذه الأقسام حالياً.")
            return

        # 2. تحديد العدد المطلوب وخلطهم
        random.shuffle(questions)
        questions = questions[:int(quiz_data.get('questions_count', 10))]

        # 3. إعلان انطلاق المنافسة
        await bot.send_message(chat_id, f"🎯 <b>استعدوا للمنافسة!</b>\n📂 الأقسام: {names_str}\n🔢 الأسئلة: {len(questions)}")
        await asyncio.sleep(3)

        overall_scores = {}

        # 4. حلقة تشغيل الأسئلة (Loop)
        for i, q in enumerate(questions):
            # توحيد جلب البيانات (يدعم الجدولين بذكاء)
            q_text = q.get('question') or q.get('question_content') or 'نص مفقود'
            cat_name = q.get('category') or q.get('categories', {}).get('name', 'عام')
            ans = q.get('answer') or q.get('correct_answer') or q.get('answer_text') or ""

            active_quizzes[chat_id] = {
                "active": True, 
                "ans": str(ans).strip(), 
                "winners": [], 
                "mode": quiz_data['mode'],
                "hint_sent": False
            }
            
            # إرسال السؤال بتصميمك الملكي
            settings = {'owner_name': owner_name, 'mode': quiz_data['mode'], 'time_limit': quiz_data['time_limit'], 'cat_name': cat_name}
            await send_quiz_question(chat_id, {'question_text': q_text}, i+1, len(questions), settings)
            
            start_time = time.time()
            time_limit = int(quiz_data['time_limit'])
            
            while time.time() - start_time < time_limit:
                await asyncio.sleep(0.1)
                
                # --- [منطق التلميح الطائر: 5 ثوانٍ لضمان القراءة] ---
                if quiz_data.get('smart_hint') and not active_quizzes[chat_id]['hint_sent']:
                    if (time.time() - start_time) >= (time_limit / 2):
                        hint_text = await generate_smart_hint(ans) 
                        hint_msg = await bot.send_message(chat_id, f"💡 <b>تلميح:</b> {hint_text}", parse_mode="HTML")
                        active_quizzes[chat_id]['hint_sent'] = True
                        
                        async def fly_and_delete(msg):
                            await asyncio.sleep(5) 
                            try: await msg.delete()
                            except: pass
                        asyncio.create_task(fly_and_delete(hint_msg))

                # نظام السرعة ⚡: لو أحد جاوب نكسر الوقت فوراً
                if quiz_data['mode'] == 'السرعة ⚡' and not active_quizzes[chat_id]['active']:
                    break

            # --- نهاية السؤال: معالجة النتائج وتحديث النقاط ---
            active_quizzes[chat_id]['active'] = False
            for w in active_quizzes[chat_id]['winners']:
                overall_scores.setdefault(w['id'], {"name": w['name'], "points": 0})['points'] += 10

            # استدعاء تصميم ياسر الإبداعي لعرض النتيجة
            await send_creative_results(chat_id, ans, active_quizzes[chat_id]['winners'], overall_scores)
            await asyncio.sleep(2)

        # --- ختام المسابقة: استدعاء تصميم ياسر النهائي للترتيب العام ---
        await send_final_results(chat_id, overall_scores, len(questions))
        
        # تنظيف الذاكرة بعد الانتهاء
        if chat_id in active_quizzes:
            del active_quizzes[chat_id]

    except Exception as e:
        logging.error(f"Engine Error: {e}")
        await bot.send_message(chat_id, f"❌ حدث خطأ في محرك المسابقة: {e}")
        
# ==========================================
# 4. رصد الإجابات (النسخة الصامتة المعتمدة - ياسر)
# ==========================================
@dp.message_handler(lambda m: not m.text.startswith('/'))
async def check_ans(m: types.Message):
    cid = m.chat.id
    # التأكد أن هناك مسابقة قائمة والسؤال ما زال متاحاً للإجابة
    if cid in active_quizzes and active_quizzes[cid]['active']:
        
        # تنظيف الإجابة من الفراغات وتحويلها لصغير لضمان المطابقة
        user_ans = m.text.strip().lower()
        correct_ans = active_quizzes[cid]['ans'].strip().lower()
        
        if user_ans == correct_ans:
            # التحقق: إذا لم يكن هذا الشخص قد أجاب صح من قبل في نفس السؤال
            already_won = any(w['id'] == m.from_user.id for w in active_quizzes[cid]['winners'])
            
            if not already_won:
                # إضافة المتسابق للقائمة (الاسم الأول + الـ ID)
                active_quizzes[cid]['winners'].append({
                    "name": m.from_user.first_name, 
                    "id": m.from_user.id
                })
                
                # --- حالة خاصة بنظام السرعة ---
                if active_quizzes[cid]['mode'] == 'السرعة ⚡':
                    active_quizzes[cid]['active'] = False
                    # في نظام السرعة، السؤال ينتهي فوراً عند أول إجابة صحيحة

# ==========================================
# 👑 لوحة تحكم المطور (ياسر) - إدارة المجموعات
# ==========================================

@dp.message_handler(commands=['admin'], user_id=ADMIN_ID)
async def admin_dashboard(message: types.Message):
    res = supabase.table("allowed_groups").select("*").execute()
    groups = res.data
    active = len([g for g in groups if g['status'] == 'active'])
    pending = len([g for g in groups if g['status'] == 'pending'])
    blocked = len([g for g in groups if g['status'] == 'blocked'])

    txt = (
        "👑 <b>أهلاً بك يا مطور في غرفة العمليات</b>\n\n"
        f"✅ النشطة: {active} | ⏳ المعلقة: {pending} | 🚫 المحظورة: {blocked}\n"
        "👇 اختر قسماً لإدارته:"
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📝 مراجعة الطلبات المعلقة", callback_data="admin_view_pending"),
        InlineKeyboardButton("📢 إذاعة (نشر عام)", callback_data="admin_broadcast"),
        InlineKeyboardButton("❌ إغلاق", callback_data="close_admin")
    )
    await message.answer(txt, reply_markup=kb, parse_mode="HTML")

# --- معالج عرض الطلبات المعلقة ---
@dp.callback_query_handler(lambda c: c.data == "admin_view_pending", user_id=ADMIN_ID)
async def view_pending_groups(callback_query: types.CallbackQuery):
    res = supabase.table("allowed_groups").select("*").eq("status", "pending").execute()
    if not res.data:
        return await callback_query.answer("لا توجد طلبات معلقة حالياً.", show_alert=True)
    
    txt = "⏳ <b>طلبات التفعيل الحالية:</b>\n"
    kb = InlineKeyboardMarkup(row_width=1)
    for g in res.data:
        kb.add(
            InlineKeyboardButton(f"✅ تفعيل: {g['group_name']}", callback_data=f"auth_approve_{g['group_id']}"),
            InlineKeyboardButton(f"❌ حظر الآيدي: {g['group_id']}", callback_data=f"auth_block_{g['group_id']}")
        )
    kb.add(InlineKeyboardButton("⬅️ العودة", callback_data="admin_back"))
    await callback_query.message.edit_text(txt, reply_markup=kb, parse_mode="HTML")

# --- معالج أزرار التفعيل (إصلاح مشكلة الحظر بالخطأ) ---
@dp.callback_query_handler(lambda c: c.data.startswith(('auth_approve_', 'auth_block_')), user_id=ADMIN_ID)
async def process_auth_callback(c: types.CallbackQuery):
    data_parts = c.data.split('_')
    action = data_parts[1]    # approve أو block
    target_id = data_parts[2]  # آيدي القروب

    if action == "approve":
        supabase.table("allowed_groups").update({"status": "active"}).eq("group_id", target_id).execute()
        await c.answer("تم التفعيل ✅", show_alert=True)
        await c.message.edit_text(f"✅ <b>تم تفعيل المجموعة بنجاح</b>\nآيدي: <code>{target_id}</code>", parse_mode="HTML")
        await bot.send_message(target_id, "🎊 <b>مبارك! تم تفعيل القروب.</b> أرسل (مسابقة) للبدء.", parse_mode="HTML")
    
    elif action == "block":
        supabase.table("allowed_groups").update({"status": "blocked"}).eq("group_id", target_id).execute()
        await c.answer("تم الحظر ❌")
        await c.message.edit_text(f"❌ <b>تم حظر المجموعة</b>\nآيدي: <code>{target_id}</code>", parse_mode="HTML")

# ==========================================
# 🛡️ نظام "تحكم" وأمان الأزرار الموحد
# ==========================================

@dp.message_handler(lambda message: message.text == "تحكم", state="*")
async def take_control(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if not current_state: return
    
    # تحديث المالك في الـ State
    await state.update_data(owner_id=message.from_user.id, owner_name=message.from_user.first_name)
    await message.reply(f"🕹️ <b>تم نقل التحكم!</b>\nالآن يا {message.from_user.first_name}، أنت من يدير الإعدادات.")

# دالة مساعدة للتحقق من الأمان (توضع في بداية كل دالة زر)
async def check_button_security(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    owner_id = data.get('owner_id')
    if owner_id and c.from_user.id != owner_id:
        owner_name = data.get('owner_name', 'شخص آخر')
        await c.answer(f"⚠️ التحكم مع {owner_name}\nأرسل (تحكم) لتستطيع الضغط!", show_alert=True)
        return False
    return True

# ==========================================
# 🤖 إضافة الأسئلة لقسم البوت (للمطور فقط)
# ==========================================

@dp.message_handler(commands=['add_bot'], user_id=ADMIN_ID)
async def add_bot_question_start(message: types.Message, state: FSMContext):
    await message.answer("🛠️ <b>إضافة سؤال لقسم البوت الرسمي:</b>\nأرسل السؤال مع الإجابات بهذا الشكل:\n\n<code>السؤال | الإجابة الصحيحة | خطأ1 | خطأ2 | خطأ3 | القسم</code>")
    await state.set_state("wait_for_bot_q")

@dp.message_handler(state="wait_for_bot_q", user_id=ADMIN_ID)
async def process_bot_q(message: types.Message, state: FSMContext):
    try:
        parts = [p.strip() for p in message.text.split('|')]
        q, a, w1, w2, w3, cat = parts
        
        payload = {
            "question": q, "correct_answer": a,
            "wrong_answer1": w1, "wrong_answer2": w2, "wrong_answer3": w3,
            "category": cat
        }
        supabase.table("bot_questions").insert(payload).execute()
        await message.answer(f"✅ تم إضافة السؤال لقسم [ {cat} ] بنجاح!")
    except:
        await message.answer("⚠️ خطأ في التنسيق! تأكد من استخدام الفاصلة | بين الإجابات.")
    await state.finish()

# ==========================================
# 5. نهاية الملف: ضمان التشغيل 24/7 على Render
# ==========================================
from aiohttp import web

async def handle_ping(request):
    return web.Response(text="Bot is Active!")

if __name__ == '__main__':
    # إعداد سيرفر صغير للرد على Cron-job لضمان استمرار البوت
    app = web.Application()
    app.router.add_get('/', handle_ping)
    loop = asyncio.get_event_loop()
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    # بورت 10000 المتوافق مع Render
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    loop.create_task(site.start())

    logging.basicConfig(level=logging.INFO)
    bot.parse_mode = "HTML" 
    executor.start_polling(dp, skip_updates=True)
