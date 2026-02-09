import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات (تم تنظيفها تماماً لتعمل على Render) ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062 

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 1. بناء القوائم الرسومية ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), 
         InlineKeyboardButton("📅 جلسة سابقة", callback_data="old_sessions")],
        [InlineKeyboardButton("🛒 سوق", callback_data="market"),
         InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 2. معالج رسالة الترحيب (/start) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    # رسالة ترحيب مخصصة باسمك [cite: 2026-01-01]
    welcome_text = "أهلاً بك يا ياسر في نظام التحكم الخاص بوت كوين ☁️\n\nلقد تم تحديث النظام وربط قاعدة البيانات بنجاح.\nارسل كلمة (تحكم) لإظهار اللوحة الرئيسية."
    msg = await update.message.reply_text(welcome_text, reply_markup=get_main_menu())
    context.user_data['last_msg_id'] = msg.message_id

# --- 3. معالج الأزرار التفاعلية ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    message_id = query.message.message_id
    context.user_data['last_msg_id'] = message_id

    if data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ لإضافة قسم", callback_data="gui_add_cat"), InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
        await query.edit_message_text("📂 أقسامك الخاصة المتاحة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        cat_res = supabase.table("categories").select("name").eq("id", cat_id).single().execute()
        q_res = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
        
        # واجهة الأزرار الكاملة كما في بوت إسلام
        text = f"📌 أنت الآن في قسم: {cat_res.data['name']}\n🔢 عدد أسئلتك الحالية: {q_res.count}\n\nاختر من الخدمات التالية:"
        keyboard = [
            [InlineKeyboardButton("حذف القسم", callback_data=f"del_cat_{cat_id}"), InlineKeyboardButton("تغيير اسم القسم", callback_data=f"edit_n_{cat_id}")],
            [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("➕ مباشر سريع", callback_data=f"add_q_{cat_id}")],
            [InlineKeyboardButton("➕ سؤال خيارات", callback_data="dev"), InlineKeyboardButton("➕ أبيات تنقيط", callback_data="dev")],
            [InlineKeyboardButton("🌀 بعثرة حروف أبيات", callback_data="dev"), InlineKeyboardButton("🔀 بعثرة كلمات", callback_data="dev")],
            [InlineKeyboardButton("تعديل سؤال", callback_data="dev"), InlineKeyboardButton("حذف سؤال", callback_data="dev")],
            [InlineKeyboardButton("عرض الأسئلة 📝", callback_data=f"vq_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("vq_"):
        cat_id = data.split("_")[1]
        questions = supabase.table("questions").select("*").eq("category_id", cat_id).execute()
        if not questions.data:
            await query.edit_message_text("⚠️ لا توجد أسئلة هنا حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_cat_{cat_id}")]]))
        else:
            txt = "📑 قائمة أسئلتك المسجلة:\n\n"
            for i, q in enumerate(questions.data, 1):
                ans2 = f" أو {q['alt_answer']}" if q.get('alt_answer') else ""
                txt += f"{i}- {q['question_content']}\n✅ الجواب: {q['correct_answer']}{ans2}\n\n"
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_cat_{cat_id}")]]))

    elif data == "dev":
        await query.message.reply_text("🚧 هذه الوظيفة قيد التجهيز البرمجي يا ياسر.")

    elif data.startswith("add_q_"):
        cat_id = data.split("_")[2]
        context.user_data.update({'state': 'WAIT_Q', 'cur_cat': cat_id})
        await query.edit_message_text("📝 ارسل نص السؤال الآن:")

    elif data == "back_to_main":
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=get_main_menu())

# --- 4. معالجة النصوص (إضافة السؤال وتغيير الاسم) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    state = context.user_data.get('state')
    last_id = context.user_data.get('last_msg_id')
    if update.effective_user.id != OWNER_ID: return
    await update.message.delete()

    if text == "تحكم":
        msg = await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        context.user_data['last_msg_id'] = msg.message_id
        return

    if state == 'WAIT_Q':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_A1'})
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_id, text=f"❓ السؤال: {text}\n\nارسل الإجابة الأولى:")
    elif state == 'WAIT_A1':
        context.user_data.update({'a1': text, 'state': 'WAIT_A2'})
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_id, text=f"✅ إجابة 1: {text}\n\nارسل الإجابة البديلة (أو 'لا يوجد'):")
    elif state == 'WAIT_A2':
        cat_id = context.user_data['cur_cat']
        q = context.user_data['q_txt']
        a1 = context.user_data['a1']
        a2 = text if text != "لا يوجد" else None
        # الحفظ في العمود الجديد alt_answer الذي أنشأته
        supabase.table("questions").insert({"category_id": int(cat_id), "question_content": q, "correct_answer": a1, "alt_answer": a2}).execute()
        context.user_data['state'] = None
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_id, text="🎉 تم حفظ السؤال بنجاح!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 للقسم", callback_data=f"manage_cat_{cat_id}")]]))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
