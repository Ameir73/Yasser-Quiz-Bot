import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- الدوال الأساسية للوحات ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- رسالة الترحيب ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_telegram = "https://t.me/Ya_79k"
    text = f"👋 أهلاً بك يا {update.effective_user.first_name}\nارسل كلمة (**تحكم**) للبدء.\n\n👑 المطور: [ياسر]({my_telegram})"
    await update.message.reply_text(text, reply_markup=get_main_menu(), parse_mode='Markdown', disable_web_page_preview=True)

# --- معالج الأزرار ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, update.effective_user.id
    
    # إدارة الأقسام
    if data == "gui_view_cats":
        res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
        keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"mng_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="add_new_cat")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
        await query.edit_message_text("📂 أقسامك الحالية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "add_new_cat":
        context.user_data['state'] = 'WAIT_CAT_NAME'
        await query.edit_message_text("📝 ارسل اسم القسم الجديد الآن:")

    elif data.startswith("mng_"):
        cat_id = data.split("_")[1]
        context.user_data['cur_cat'] = cat_id
        keyboard = [
            [InlineKeyboardButton("➕ إضافة سؤال", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"del_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(f"📍 إدارة القسم:", reply_markup=InlineKeyboardMarkup(keyboard))

    # إضافة سؤال
    elif data.startswith("add_q_"):
        context.user_data['state'] = 'WAIT_Q_TXT'
        await query.edit_message_text("📝 ارسل نص السؤال:")

    elif data == "ask_alt_no":
        await save_q_to_db(query, context, None)
    
    elif data == "ask_alt_yes":
        context.user_data['state'] = 'WAIT_ALT_ANS'
        await query.edit_message_text("📝 ارسل الإجابة البديلة:")

    # حذف القسم
    elif data.startswith("del_"):
        cid = data.split("_")[1]
        keyboard = [[InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_del_{cid}"), InlineKeyboardButton("❌ لا، تراجع", callback_data=f"mng_{cid}")]]
        await query.edit_message_text("⚠️ هل أنت متأكد من حذف القسم؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("confirm_del_"):
        cid = data.split("_")[2]
        supabase.table("categories").delete().eq("id", cid).execute()
        await query.edit_message_text("✅ تم الحذف بنجاح.", reply_markup=get_main_menu())

    elif data == "back_main":
        await query.edit_message_text("⚙️ الرئيسية:", reply_markup=get_main_menu())

# --- حفظ السؤال ---
async def save_q_to_db(update_or_query, context, alt):
    d = context.user_data
    supabase.table("questions").insert({
        "category_id": int(d['cur_cat']), "question_content": d['q_txt'],
        "correct_answer": d['ans'], "alt_answer": alt, "created_by": update_or_query.from_user.id
    }).execute()
    d['state'] = None
    text = "🎉 تم حفظ السؤال بنجاح!"
    if hasattr(update_or_query, 'edit_message_text'): await update_or_query.edit_message_text(text, reply_markup=get_main_menu())
    else: await update_or_query.reply_text(text, reply_markup=get_main_menu())

# --- معالج النصوص ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, state, uid = update.message.text.strip(), context.user_data.get('state'), update.effective_user.id

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        return

    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text, "created_by": uid}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم إضافة القسم: {text}", reply_markup=get_main_menu())

    elif state == 'WAIT_Q_TXT':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_ANS'})
        await update.message.reply_text("✅ ارسل الإجابة الصحيحة:")

    elif state == 'WAIT_ANS':
        context.user_data.update({'ans': text, 'state': None})
        keyboard = [[InlineKeyboardButton("✅ نعم", callback_data="ask_alt_yes"), InlineKeyboardButton("❌ لا", callback_data="ask_alt_no")]]
        await update.message.reply_text("هل تريد إضافة إجابة بديلة؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == 'WAIT_ALT_ANS':
        await save_q_to_db(update, context, text)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
    
