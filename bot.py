import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- إعدادات ياسر ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ إضافة قسم أسئلة", callback_data="gui_add_cat")],
        [InlineKeyboardButton("📚 إدارة الأقسام والأسئلة", callback_data="gui_view_cats")],
        [InlineKeyboardButton("❌ إغلاق القائمة", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    msg = await update.message.reply_text("👋 أهلاً بك في بوت كوين في لوحة التحكم.\nارسل كلمة **تحكم** لفتح الإدارة.", reply_markup=get_main_menu())
    context.user_data['last_msg_id'] = msg.message_id

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    message_id = query.message.message_id
    context.user_data['last_msg_id'] = message_id

    if data == "back_to_main":
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=get_main_menu())
    elif data == "gui_add_cat":
        context.user_data['state'] = 'WAIT_CAT_NAME'
        await query.edit_message_text("📝 ارسل الآن اسم القسم الجديد:")
    elif data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(f"📂 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
        await query.edit_message_text("📌 اختر القسم المراد إدارته:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        keyboard = [[InlineKeyboardButton("➕ إضافة سؤال", callback_data=f"add_q_{cat_id}")],
                    [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"del_cat_{cat_id}")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]
        await query.edit_message_text(f"📁 إدارة القسم (ID: {cat_id})", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("del_cat_"):
        cat_id = data.split("_")[2]
        supabase.table("categories").delete().eq("id", cat_id).execute()
        await query.edit_message_text("🗑️ تم حذف القسم بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]))
    elif data.startswith("add_q_"):
        cat_id = data.split("_")[2]
        context.user_data.update({'state': f'WAIT_Q_TEXT_{cat_id}', 'temp_ans': []})
        await query.edit_message_text("📝 ارسل **نص السؤال** الجديد:")
    elif data.startswith("finish_q_"):
        cat_id = data.split("_")[2]
        q_text = context.user_data.get('temp_q')
        ans_list = "|".join(context.user_data.get('temp_ans', []))
        supabase.table("questions").insert({"category_id": int(cat_id), "question_content": q_text, "correct_answer": ans_list, "timer": 20}).execute()
        await query.edit_message_text(f"✅ تم حفظ السؤال بنجاح!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("إضافة سؤال آخر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("رجوع", callback_data=f"manage_cat_{cat_id}")]]))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if update.effective_user.id != OWNER_ID: return
    state = context.user_data.get('state')
    last_msg_id = context.user_data.get('last_msg_id')
    chat_id = update.effective_chat.id
    await update.message.delete()
    if text == "تحكم":
        msg = await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        context.user_data['last_msg_id'] = msg.message_id
        return
    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        await context.bot.edit_message_text(chat_id=chat_id, message_id=last_msg_id, text=f"✅ تم إنشاء القسم '{text}'", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="gui_view_cats")]]))
    elif state and state.startswith('WAIT_Q_TEXT_'):
        cat_id = state.split('_')[3]
        context.user_data.update({'temp_q': text, 'state': f'WAIT_Q_ANS_{cat_id}'})
        await context.bot.edit_message_text(chat_id=chat_id, message_id=last_msg_id, text=f"❓ السؤال: {text}\n\nارسل الآن **الجواب الصحيح**:")
    elif state and state.startswith('WAIT_Q_ANS_'):
        cat_id = state.split('_')[3]
        context.user_data['temp_ans'].append(text)
        keyboard = [[InlineKeyboardButton("✅ نعم", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("❌ لا (حفظ)", callback_data=f"finish_q_{cat_id}")]]
        await context.bot.edit_message_text(chat_id=chat_id, message_id=last_msg_id, text=f"✅ أضفت: {text}\nهل تريد إضافة إجابة أخرى؟", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
        
