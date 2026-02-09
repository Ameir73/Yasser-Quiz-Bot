import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات (نظيفة لضمان التشغيل على Render) ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- القوائم الرسومية ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), 
         InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev_msg")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev_msg"),
         InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    welcome = "أهلاً بك يا ياسر ☁️\nتم تحديث الكود الشامل بنجاح.\nارسل (تحكم) للبدء."
    msg = await update.message.reply_text(welcome, reply_markup=get_main_menu())
    context.user_data['last_msg_id'] = msg.message_id

# --- معالج الأزرار التفاعلية ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    
    # واجهة عرض الأقسام (إصلاح إضافة قسم)
    if data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ لإضافة قسم", callback_data="gui_add_cat")])
        keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
        await query.edit_message_text("📂 أقسامك الخاصة المتاحة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "gui_add_cat":
        context.user_data['state'] = 'WAIT_CAT_NAME'
        await query.edit_message_text("📝 ارسل اسم القسم الجديد الذي تريد إنشاؤه:")

    # واجهة إدارة القسم الكاملة (أزرار بوت إسلام)
    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        cat_res = supabase.table("categories").select("name").eq("id", cat_id).single().execute()
        q_res = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
        text = f"📌 أنت الآن في قسم: {cat_res.data['name']}\n🔢 عدد الأسئلة: {q_res.count}"
        keyboard = [
            [InlineKeyboardButton("حذف القسم", callback_data=f"del_cat_{cat_id}"), InlineKeyboardButton("تغيير الاسم", callback_data=f"edit_n_{cat_id}")],
            [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("➕ مباشر سريع", callback_data=f"add_q_{cat_id}")],
            [InlineKeyboardButton("➕ سؤال خيارات", callback_data="dev_msg"), InlineKeyboardButton("➕ أبيات تنقيط", callback_data="dev_msg")],
            [InlineKeyboardButton("🌀 بعثرة حروف", callback_data="dev_msg"), InlineKeyboardButton("🔀 بعثرة كلمات", callback_data="dev_msg")],
            [InlineKeyboardButton("عرض الأسئلة 📝", callback_data=f"vq_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # أزرار تهيئة المسابقة (جديد)
    elif data == "setup_quiz":
        keyboard = [
            [InlineKeyboardButton("⏱️ تحديد الوقت", callback_data="dev_msg"), InlineKeyboardButton("📉 عدد الجولات", callback_data="dev_msg")],
            [InlineKeyboardButton("📢 إرسال إعلان للمسابقة", callback_data="dev_msg")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        await query.edit_message_text("🏆 لوحة تهيئة المسابقة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("vq_"):
        cat_id = data.split("_")[1]
        questions = supabase.table("questions").select("*").eq("category_id", cat_id).execute()
        txt = "📑 قائمة أسئلتك:\n\n" if questions.data else "⚠️ القسم فارغ."
        for i, q in enumerate(questions.data, 1):
            ans2 = f" أو {q['alt_answer']}" if q.get('alt_answer') else ""
            txt += f"{i}- {q['question_content']}\n✅ الجواب: {q['correct_answer']}{ans2}\n\n"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_cat_{cat_id}")]]))

    elif data == "back_to_main":
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=get_main_menu())

    elif data == "dev_msg":
        await query.message.reply_text("🚧 هذه الميزة قيد التطوير البرمجي  .")

    elif data.startswith("add_q_"):
        cat_id = data.split("_")[2]
        context.user_data.update({'state': 'WAIT_Q', 'cur_cat': cat_id})
        await query.edit_message_text("📝 ارسل نص السؤال:")

# --- معالجة النصوص وحفظ البيانات ---
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

    # تنفيذ إضافة قسم (إصلاح الخلل)
    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_id, text=f"✅ تم إضافة قسم '{text}' بنجاح!", reply_markup=get_main_menu())

    # تنفيذ إضافة سؤال بإجابتين
    elif state == 'WAIT_Q':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_A1'})
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_id, text="✅ استلمت السؤال. ارسل الإجابة الأولى:")
    elif state == 'WAIT_A1':
        context.user_data.update({'a1': text, 'state': 'WAIT_A2'})
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_id, text="ارسل الإجابة الثانية (أو 'لا يوجد'):")
    elif state == 'WAIT_A2':
        cat_id = context.user_data['cur_cat']
        ans2 = text if text != "لا يوجد" else None
        supabase.table("questions").insert({
            "category_id": int(cat_id), "question_content": context.user_data['q_txt'],
            "correct_answer": context.user_data['a1'], "alt_answer": ans2
        }).execute()
        context.user_data['state'] = None
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_id, text="🎉 تم حفظ السؤال بنجاح!", reply_markup=get_main_menu())

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
