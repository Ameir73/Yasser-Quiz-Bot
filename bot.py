import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- إعدادات ياسر الأساسية ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062
DEVELOPER_CHAT = "https://t.me/Ya_79k"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- دالة الترحيب (Start) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "👋 أهلاً بك يا ياسر في بوت المسابقات المطور.\n\nاكتب كلمة **تحكم** للبدء."
    await update.message.reply_text(welcome_text)

# --- معالج النصوص (إضافة الأقسام والأسئلة وتعديلها) ---
async def handle_text_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    if user_id != OWNER_ID: return 

    state = context.user_data.get('state')

    if text == "تحكم":
        context.user_data.clear()
        keyboard = [[InlineKeyboardButton("➕ إضافة قسم أسئلة", callback_data="gui_add_cat")],
                    [InlineKeyboardButton("📚 إدارة الأقسام والأسئلة", callback_data="gui_view_cats")]]
        await update.message.reply_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # استقبال اسم القسم
    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم إضافة قسم ( {text} ) بنجاح!", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]))

    # استقبال نص السؤال الجديد
    elif state and state.startswith('WAIT_Q_TEXT_'):
        cat_id = state.split('_')[3]
        context.user_data['temp_q'] = text
        context.user_data['state'] = f'WAIT_Q_ANS_{cat_id}'
        await update.message.reply_text(f"✅ السؤال: {text}\n\nارسل الآن **الإجابة الصحيحة**:")

    # استقبال الإجابات المتعددة
    elif state and state.startswith('WAIT_Q_ANS_'):
        cat_id = state.split('_')[3]
        if 'temp_ans' not in context.user_data: context.user_data['temp_ans'] = []
        context.user_data['temp_ans'].append(text)
        keyboard = [[InlineKeyboardButton("✅ نعم", callback_data=f"add_more_ans_{cat_id}"),
                     InlineKeyboardButton("❌ لا", callback_data=f"finish_q_{cat_id}")]]
        await update.message.reply_text(f"✅ تم إضافة الإجابة: {text}\n\nهل تريد إضافة إجابة أخرى؟", reply_markup=InlineKeyboardMarkup(keyboard))

# --- معالج الأزرار الشفافة ولوحة التحكم الخماسية ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_main":
        context.user_data.clear()
        keyboard = [[InlineKeyboardButton("➕ إضافة قسم أسئلة", callback_data="gui_add_cat")],
                    [InlineKeyboardButton("📚 إدارة الأقسام والأسئلة", callback_data="gui_view_cats")]]
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "gui_add_cat":
        context.user_data['state'] = 'WAIT_CAT_NAME'
        await query.edit_message_text("➕ ارسل الآن اسم القسم الجديد:")

    # إنهاء السؤال وعرض اللوحة الخماسية
    elif data.startswith("finish_q_"):
        cat_id = data.split("_")[2]
        q_text = context.user_data.get('temp_q')
        ans_list = "|".join(context.user_data.get('temp_ans', []))
        
        # حفظ السؤال في Supabase
        res = supabase.table("questions").insert({"category_id": int(cat_id), "question_content": q_text, "correct_answer": ans_list, "timer": 20}).execute()
        q_id = res.data[0]['id']

        msg = f"📝 **مراجعة السؤال المضاف:**\n\n**السؤال:** {q_text}\n**الإجابات:** {ans_list.replace('|', ' - ')}"
        keyboard = [
            [InlineKeyboardButton("1️⃣ تعديل السؤال", callback_data=f"edit_q_{q_id}"),
             InlineKeyboardButton("2️⃣ تعديل الإجابة", callback_data=f"edit_a_{q_id}")],
            [InlineKeyboardButton("3️⃣ حذف السؤال", callback_data=f"del_q_{q_id}"),
             InlineKeyboardButton("4️⃣ إضافة سؤال جديد", callback_data=f"add_q_{cat_id}")],
            [InlineKeyboardButton("5️⃣ رجوع لصفحة القسم", callback_data=f"manage_cat_{cat_id}")]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# --- تشغيل البوت الأساسي ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_logic))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 البوت يعمل الآن بنجاح يا ياسر!")
    app.run_polling()

if __name__ == "__main__":
    main()
                            
