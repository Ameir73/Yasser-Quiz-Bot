import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- إعدادات ياسر الثابتة ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- القوائم الرسومية ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), 
         InlineKeyboardButton("📅 جلسة سابقة", callback_data="old_sessions")],
        [InlineKeyboardButton("🛒 سوق", callback_data="market"),
         InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_setup_quiz_menu():
    keyboard = [
        [InlineKeyboardButton("أقسام الأعضاء", callback_data="members_cats"),
         InlineKeyboardButton("أقسام البوت", callback_data="bot_cats")],
        [InlineKeyboardButton("الأقسام المختارة", callback_data="selected_cats"),
         InlineKeyboardButton("أقسامك الخاصة", callback_data="gui_view_cats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 1. رسالة الترحيب عند تشغيل البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    # رسالة الترحيب التي طلبتها
    welcome_text = (
        "مرحباً بك في بوت مسابقات كوين.\n\n"
        "تستطيع البدء بإرسال عبارة (**لوحة التحكم**) أو (**تحكم**) لإدارة أقسامك وأسئلتك."
    )
    msg = await update.message.reply_text(welcome_text, reply_markup=get_main_menu())
    context.user_data['last_msg_id'] = msg.message_id

# --- 2. معالجة الأزرار (التفاعل) ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    message_id = query.message.message_id
    context.user_data['last_msg_id'] = message_id

    if data == "setup_quiz":
        await query.edit_message_text("⚙️ قم بتهيئة المسابقة الآن:", reply_markup=get_setup_quiz_menu())

    elif data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = []
        temp_row = []
        for c in res.data:
            temp_row.append(InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}"))
            if len(temp_row) == 2:
                keyboard.append(temp_row)
                temp_row = []
        if temp_row: keyboard.append(temp_row)
        keyboard.append([InlineKeyboardButton("➕ لإضافة قسم", callback_data="gui_add_cat")])
        keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
        text = "┏━━━━━━━━━━━━┓\n       أقسامك الخاصة       \n┗━━━━━━━━━━━━┛"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        cat_res = supabase.table("categories").select("name").eq("id", cat_id).single().execute()
        q_res = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
        
        # واجهة إدارة القسم الاحترافية بجميع الأزرار
        text = f"📌 أنت الآن في قسم {cat_res.data['name']}\n🔢 عدد أسئلتك الحالية: {q_res.count}\n\nاختر من الخدمات التالية:"
        keyboard = [
            [InlineKeyboardButton("تغيير اسم القسم", callback_data=f"edit_n_{cat_id}"), InlineKeyboardButton("حذف القسم", callback_data=f"del_cat_{cat_id}")],
            [InlineKeyboardButton("➕ مباشر سريع", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}")],
            [InlineKeyboardButton("➕ سؤال خيارات", callback_data=f"opt_q_{cat_id}")],
            [InlineKeyboardButton("➕ أبيات تنقيط", callback_data=f"dot_q_{cat_id}")],
            [InlineKeyboardButton("🌀 بعثرة حروف أبيات", callback_data=f"scr_q_{cat_id}")],
            [InlineKeyboardButton("🔀 بعثرة كلمات", callback_data=f"wrd_q_{cat_id}")],
            [InlineKeyboardButton("حذف سؤال", callback_data=f"dq_{cat_id}"), InlineKeyboardButton("تعديل سؤال", callback_data=f"eq_{cat_id}")],
            [InlineKeyboardButton("عرض الأسئلة", callback_data=f"vq_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "gui_add_cat":
        context.user_data['state'] = 'WAIT_CAT_NAME'
        await query.edit_message_text("📝 ارسل اسم القسم الجديد:")

    elif data.startswith("add_q_"):
        cat_id = data.split("_")[2]
        context.user_data.update({'state': f'WAIT_Q_TEXT_{cat_id}', 'cur_cat': cat_id})
        await query.edit_message_text("📝 ارسل نص السؤال الآن:")

    elif data == "back_to_main":
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=get_main_menu())

    elif data == "close_menu":
        await query.delete_message()

# --- 3. معالجة الرسائل النصية ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if update.effective_user.id != OWNER_ID: return
    state = context.user_data.get('state')
    last_msg_id = context.user_data.get('last_msg_id')

    if text in ["تحكم", "لوحة التحكم"]:
        await update.message.delete()
        msg = await update.message.reply_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=get_main_menu())
        context.user_data['last_msg_id'] = msg.message_id
        return

    if state == 'WAIT_CAT_NAME':
        await update.message.delete()
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_msg_id, text=f"✅ تم إنشاء قسم: {text}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]))

    elif state and state.startswith('WAIT_Q_TEXT_'):
        cat_id = context.user_data['cur_cat']
        await update.message.delete()
        context.user_data.update({'temp_q': text, 'state': f'WAIT_Q_ANS_{cat_id}'})
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_msg_id, text=f"❓ السؤال: {text}\n\nارسل الآن الجواب الصحيح:")

    elif state and state.startswith('WAIT_Q_ANS_'):
        cat_id = context.user_data['cur_cat']
        q_text = context.user_data['temp_q']
        await update.message.delete()
        # حفظ في قاعدة البيانات
        supabase.table("questions").insert({"category_id": int(cat_id), "question_content": q_text, "correct_answer": text}).execute()
        context.user_data['state'] = None
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_msg_id, text=f"✅ تم حفظ السؤال بنجاح!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للقسم", callback_data=f"manage_cat_{cat_id}")]]))

# --- 4. التشغيل الرئيسي ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start)) # إضافة معالج البدء بالترحيب
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
