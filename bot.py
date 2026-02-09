import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات (تم تنظيف الأرقام لتجنب أخطاء Render) ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062 # تأكد أن هذا هو معرفك الصحيح

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- لوحة التحكم الرئيسية ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 أقسامك الخاصة", callback_data="gui_view_cats")],
        [InlineKeyboardButton("🛒 سوق", callback_data="market"), InlineKeyboardButton("🏆 مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    msg = await update.message.reply_text("أهلاً بك يا ياسر ☁️\nتم تحديث الكود وحل مشكلة التوقف.\nارسل (**تحكم**) للبدء.", reply_markup=get_main_menu())
    context.user_data['last_msg_id'] = msg.message_id

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
        await query.edit_message_text("📂 أقسامك:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        cat_res = supabase.table("categories").select("name").eq("id", cat_id).single().execute()
        keyboard = [
            [InlineKeyboardButton("➕ إضافة سؤال", callback_data=f"add_q_{cat_id}")],
            [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"del_cat_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(f"⚙️ إدارة قسم: {cat_res.data['name']}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("add_q_"):
        cat_id = data.split("_")[2]
        context.user_data.update({'state': 'WAIT_Q', 'cur_cat': cat_id})
        await query.edit_message_text("📝 ارسل نص السؤال الآن:")

    elif data == "back_to_main":
        await query.edit_message_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if update.effective_user.id != OWNER_ID: return
    state = context.user_data.get('state')
    last_id = context.user_data.get('last_msg_id')
    await update.message.delete()

    if text == "تحكم":
        msg = await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        context.user_data['last_msg_id'] = msg.message_id
        return

    if state == 'WAIT_Q':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_A1'})
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_id, text="✅ استلمت السؤال.\nالآن ارسل **الإجابة الأولى**:")
    
    elif state == 'WAIT_A1':
        context.user_data.update({'a1': text, 'state': 'WAIT_A2'})
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_id, text="✅ استلمت الإجابة 1.\nالآن ارسل **الإجابة الثانية** (أو اكتب 'لا يوجد'):")
    
    elif state == 'WAIT_A2':
        cat_id = context.user_data['cur_cat']
        q = context.user_data['q_txt']
        a1 = context.user_data['a1']
        a2 = text if text != "لا يوجد" else None
        
        # حفظ البيانات في الأعمدة التي جهزناها (بما فيها alt_answer)
        supabase.table("questions").insert({
            "category_id": int(cat_id), 
            "question_content": q, 
            "correct_answer": a1, 
            "alt_answer": a2
        }).execute()
        
        context.user_data['state'] = None
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🎉 تم حفظ السؤال بنجاح في قاعدة البيانات!")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
        
