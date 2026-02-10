import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات الثابتة ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- الدوال المساعدة للوحات التحكم ---

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(settings):
    keyboard = [
        [InlineKeyboardButton(f"📊 عدد الأسئلة: {settings['num_questions']}", callback_data="none")],
        [InlineKeyboardButton(f"✅ {n}" if settings['num_questions'] == n else str(n), callback_data=f"set_num_{n}") for n in [20, 25, 30, 35, 40, 45]],
        [
            InlineKeyboardButton(f"🚀 السرعة" if settings['timing_mode'] == 'السرعة' else "🕒 الوقت", callback_data="toggle_timing"),
            InlineKeyboardButton(f"المنافسة: {settings['comp_type']}", callback_data="toggle_comp")
        ],
        [
            InlineKeyboardButton(f"● مباشرة" if settings['ans_type'] == 'مباشرة' else "○ مباشرة", callback_data="ans_direct"),
            InlineKeyboardButton(f"● خيارات" if settings['ans_type'] == 'خيارات' else "○ خيارات", callback_data="ans_opt"),
            InlineKeyboardButton(f"● الكل" if settings['ans_type'] == 'الكل' else "○ الكل", callback_data="ans_all")
        ],
        [InlineKeyboardButton("حفظ المسابقة وتسميتها ✅", callback_data="save_quiz_final")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz")]
    ]
    return InlineKeyboardMarkup(keyboard)

# 1. رسالة الترحيب (تحتوي على حسابك)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_telegram = "https://t.me/Ya_79k" 
    welcome_text = (
        f"👋 أهلاً بك في بوت المسابقات المطور!\n\n"
        f"📖 **كيفية التشغيل:**\n"
        f"• ارسل كلمة (**تحكم**) لإدارة الأقسام والمسابقات.\n\n"
        f"👑 **المطور:** [ياسر]({my_telegram})"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode='Markdown')

# --- دالة حفظ السؤال النهائية ---
async def save_question_db(update_or_query, context, alt_ans=None):
    cat_id = context.user_data.get('cur_cat')
    user_id = update_or_query.from_user.id
    try:
        supabase.table("questions").insert({
            "category_id": int(cat_id), "question_content": context.user_data['q_txt'], 
            "correct_answer": context.user_data['a1'], "alt_answer": alt_ans, "created_by": user_id
        }).execute()
        context.user_data['state'] = None
        text = "🎉 تم حفظ السؤال بنجاح!"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للقسم", callback_data=f"manage_cat_{cat_id}")]])
        if hasattr(update_or_query, 'edit_message_text'): await update_or_query.edit_message_text(text, reply_markup=reply_markup)
        else: await update_or_query.reply_text(text, reply_markup=reply_markup)
    except Exception as e: logging.error(f"Save Error: {e}")

# 2. معالج الأزرار المصلح بالكامل (إدارة + تهيئة)
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, update.effective_user.id
    
    if 'temp_setup' not in context.user_data:
        context.user_data['temp_setup'] = {'num_questions': 20, 'timing_mode': 'الوقت', 'comp_type': 'خاصة', 'ans_type': 'مباشرة'}

    # --- إدارة الأقسام ---
    if data == "gui_view_cats":
        res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
        keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
        await query.edit_message_text("📂 أقسامك الشخصية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        context.user_data['cur_cat'] = cat_id
        cat_res = supabase.table("categories").select("*").eq("id", cat_id).single().execute()
        text = f"📌 إدارة قسم: {cat_res.data['name']}"
        keyboard = [
            [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"conf_del_{cat_id}"), InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"edit_nm_{cat_id}")],
            [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("📝 عرض الأسئلة", callback_data=f"vq_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # --- تأكيد الحذف (نعم/لا) ---
    elif data.startswith("conf_del_"):
        cat_id = data.split("_")[2]
        keyboard = [[InlineKeyboardButton("✅ نعم، احذف", callback_data=f"exec_del_{cat_id}"), InlineKeyboardButton("❌ لا، تراجع", callback_data=f"manage_cat_{cat_id}")]]
        await query.edit_message_text("⚠️ هل أنت متأكد من حذف هذا القسم نهائياً؟", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("exec_del_"):
        cat_id = data.split("_")[2]
        supabase.table("categories").delete().eq("id", cat_id).execute()
        await query.edit_message_text("✅ تم حذف القسم بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="gui_view_cats")]]))

    # --- تهيئة المسابقة ---
    elif data == "setup_quiz":
        keyboard = [
            [InlineKeyboardButton("أقسام الأعضاء", callback_data="quiz_m"), InlineKeyboardButton("أقسام البوت", callback_data="quiz_b")],
            [InlineKeyboardButton("⚙️ الإعدادات الفنية", callback_data="go_to_settings")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        await query.edit_message_text("🏆 قم بتهيئة المسابقة الجديدة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "go_to_settings":
        await query.edit_message_text("⚙️ الإعدادات الفنية:", reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

    elif data.startswith("set_num_"):
        context.user_data['temp_setup']['num_questions'] = int(data.split("_")[2])
        await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

    # --- الإجابة البديلة (نعم/لا) ---
    elif data == "ask_alt_yes":
        context.user_data['state'] = 'WAIT_A2'
        await query.edit_message_text("📝 ارسل الإجابة البديلة الآن:")
    
    elif data == "ask_alt_no":
        await save_question_db(query, context)

    elif data == "back_to_main":
        await query.edit_message_text("⚙️ القائمة الرئيسية:", reply_markup=get_main_menu())

# --- معالج النصوص (الحالات) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, state, uid = update.message.text.strip(), context.user_data.get('state'), update.effective_user.id

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        return

    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text, "created_by": uid}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم إضافة القسم: {text}", reply_markup=get_main_menu())

    elif state == 'WAIT_Q':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_A1'})
        await update.message.reply_text("✅ الآن ارسل الإجابة الصحيحة الأولى:")

    elif state == 'WAIT_A1':
        context.user_data.update({'a1': text, 'state': None})
        keyboard = [[InlineKeyboardButton("✅ نعم", callback_data="ask_alt_yes"), InlineKeyboardButton("❌ لا", callback_data="ask_alt_no")]]
        await update.message.reply_text("هل تريد إضافة إجابة بديلة لهذا السؤال؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == 'WAIT_A2':
        await save_question_db(update, context, text)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
        
