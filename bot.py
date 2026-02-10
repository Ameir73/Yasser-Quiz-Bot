import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- القوائم واللوحات ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(settings):
    # لوحة الإعدادات الفنية كما في الفيديو تماماً
    keyboard = [
        [InlineKeyboardButton(f"📊 عدد الأسئلة الحالي: {settings['num_questions']}", callback_data="none")],
        [InlineKeyboardButton(f"✅ {n}" if settings['num_questions'] == n else str(n), callback_data=f"set_num_{n}") for n in [20, 25, 30, 35, 40, 45]],
        [
            InlineKeyboardButton(f"🚀 السرعة" if settings['timing_mode'] == 'السرعة' else "🕒 الوقت", callback_data="toggle_timing"),
            InlineKeyboardButton(f"المنافسة: {settings['comp_type']}", callback_data="toggle_comp")
        ],
        [
            InlineKeyboardButton(f"● مباشرة" if settings['ans_type'] == 'مباشرة' else "○ مباشرة", callback_data="ans_direct"),
            InlineKeyboardButton(f"● خيارات" if settings['ans_type'] == 'خيارات' else "○ خيارات", callback_data="ans_opt")
        ],
        [InlineKeyboardButton("حفظ المسابقة وتسميتها ✅", callback_data="save_quiz_final")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- رسالة الترحيب ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_telegram = "https://t.me/Ya_79k" 
    welcome_text = (
        f"👋 أهلاً بك في بوت المسابقات المطور!\n\n"
        f"📖 **كيفية التشغيل:**\n"
        f"• ارسل كلمة (**تحكم**) لإدارة الأقسام والمسابقات.\n\n"
        f"👑 **المطور:** [ياسر]({my_telegram})"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode='Markdown')

# --- معالج الأزرار (شامل التهيئة والإدارة) ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, update.effective_user.id
    
    # تهيئة إعدادات المسابقة المؤقتة
    if 'temp_setup' not in context.user_data:
        context.user_data['temp_setup'] = {'num_questions': 20, 'timing_mode': 'الوقت', 'comp_type': 'خاصة', 'ans_type': 'مباشرة', 'selected_cats': []}

    # --- [1] تهيئة المسابقة (القسم الذي سألت عنه) ---
    if data == "setup_quiz":
        keyboard = [
            [InlineKeyboardButton("أقسام الأعضاء", callback_data="quiz_m"), InlineKeyboardButton("أقسام البوت", callback_data="quiz_b")],
            [InlineKeyboardButton("⚙️ الإعدادات الفنية", callback_data="go_to_settings")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ]
        await query.edit_message_text("🏆 تهيئة المسابقة الجديدة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "go_to_settings":
        await query.edit_message_text("⚙️ اضبط الإعدادات الفنية:", reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

    elif data.startswith("set_num_"):
        context.user_data['temp_setup']['num_questions'] = int(data.split("_")[2])
        await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

    elif data == "toggle_timing":
        context.user_data['temp_setup']['timing_mode'] = 'السرعة' if context.user_data['temp_setup']['timing_mode'] == 'الوقت' else 'الوقت'
        await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

    # --- [2] إدارة الأقسام (تغيير اسم، حذف بتأكيد، إجابة بديلة) ---
    elif data == "gui_view_cats":
        res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
        keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
        await query.edit_message_text("📂 أقسامك الشخصية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        context.user_data['cur_cat'] = cat_id
        await query.edit_message_text(f"📍 إدارة القسم...", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"conf_del_{cat_id}"), InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"edit_nm_{cat_id}")],
            [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
        ]))

    elif data.startswith("conf_del_"): # تأكيد الحذف نعم/لا
        cat_id = data.split("_")[2]
        keyboard = [[InlineKeyboardButton("✅ نعم، احذف", callback_data=f"exec_del_{cat_id}"), InlineKeyboardButton("❌ لا، تراجع", callback_data=f"manage_cat_{cat_id}")]]
        await query.edit_message_text("⚠️ هل أنت متأكد من حذف القسم؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_main":
        await query.edit_message_text("⚙️ الرئيسية:", reply_markup=get_main_menu())

# --- معالج النصوص (حفظ السؤال وحفظ المسابقة) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, state, uid = update.message.text.strip(), context.user_data.get('state'), update.effective_user.id

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        return

    # منطق الحالات (إضافة قسم، إضافة سؤال، إجابة بديلة)
    if state == 'WAIT_Q':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_A1'})
        await update.message.reply_text("✅ ارسل الإجابة الأولى:")
    elif state == 'WAIT_A1':
        context.user_data.update({'a1': text, 'state': None})
        keyboard = [[InlineKeyboardButton("✅ نعم", callback_data="ask_alt_yes"), InlineKeyboardButton("❌ لا", callback_data="ask_alt_no")]]
        await update.message.reply_text("هل تود إضافة إجابة بديلة؟", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
                                                                                                 
