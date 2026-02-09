import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- قائمة التحكم الرئيسية ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 1. رسالة الترحيب للمستخدمين (باسمك وحساب التليجرام) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # رابط حسابك على التليجرام (يرجى التأكد من كتابة اليوزر نيم الخاص بك مكان 'Ameir73' إذا كان مختلفاً)
    telegram_link = "https://t.me/Ya_79k" 
    
    welcome_text = (
        "👋 أهلاً بك في بوت المسابقات كوين!\n\n"
        "📖 كيفية التشغيل واستخدام البوت:\n"
        "• إذا كنت المسؤول: ارسل كلمة (تحكم) لفتح لوحة الإدارة.\n"
        "• يمكنك إنشاء أقسام خاصة بك وإضافة الأسئلة بسهولة.\n"
        "• نظام الأسئلة يدعم (إجابة أولى) و (إجابة ثانية) لضمان الدقة.\n\n"
        "👑 *دتم تطوير وبرمجة هذا البوت بواسطة:\n"
        f"المطور [ياسر]({telegram_link})\n\n"
        "📢 تواصل مع المطور للاستفسارات أو طلب نسخ خاصة."
    )
    
    # للمسؤول فقط يظهر زر التحكم، وللمستخدم العادي تظهر الرسالة فقط
    reply_markup = get_main_menu() if update.effective_user.id == OWNER_ID else None
    
    msg = await update.message.reply_text(
        welcome_text, 
        reply_markup=reply_markup, 
        parse_mode='Markdown', 
        disable_web_page_preview=False
    )
    context.user_data['last_msg_id'] = msg.message_id

# --- 2. معالج الأزرار التفاعلية (كل الإصلاحات السابقة مدمجة) ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ لإضافة قسم", callback_data="gui_add_cat")])
        keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
        await query.edit_message_text("📂 أقسامك الخاصة المتاحة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "gui_add_cat":
        context.user_data['state'] = 'WAIT_CAT_NAME'
        await query.edit_message_text("📝 ارسل اسم القسم الجديد الآن:")

    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        cat_res = supabase.table("categories").select("name").eq("id", cat_id).single().execute()
        q_res = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
        text = f"📌 أنت الآن في قسم: {cat_res.data['name']}\n🔢 عدد الأسئلة: {q_res.count}"
        keyboard = [
            [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"conf_del_{cat_id}"), InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"edit_n_{cat_id}")],
            [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("📝 عرض الأسئلة", callback_data=f"vq_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("conf_del_"):
        cat_id = data.split("_")[2]
        keyboard = [[InlineKeyboardButton("✅ نعم، احذف", callback_data=f"execute_del_{cat_id}"), 
                     InlineKeyboardButton("❌ لا، تراجع", callback_data=f"manage_cat_{cat_id}")]]
        await query.edit_message_text("⚠️ هل أنت متأكد من الحذف؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("execute_del_"):
        cat_id = data.split("_")[2]
        supabase.table("categories").delete().eq("id", cat_id).execute()
        await query.edit_message_text("🗑️ تم حذف القسم.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="gui_view_cats")]]))

    elif data.startswith("vq_"):
        cat_id = data.split("_")[1]
        questions = supabase.table("questions").select("*").eq("category_id", cat_id).execute()
        txt = "📑 قائمة الأسئلة:\n\n" if questions.data else "⚠️ القسم فارغ."
        for i, q in enumerate(questions.data, 1):
            txt += f"{i}- {q['question_content']}\n✅ إجابة 1: {q['correct_answer']}\n"
            if q.get('alt_answer'): txt += f"✅ إجابة 2: {q['alt_answer']}\n"
            txt += "----------------\n"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_cat_{cat_id}")]]))

    elif data == "back_to_main":
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=get_main_menu())

    elif data == "ask_alt_yes":
        context.user_data['state'] = 'WAIT_A2'
        await query.edit_message_text("📝 ارسل الإجابة الثانية الآن:")
    
    elif data == "ask_alt_no":
        await save_question(update, context, None)

    elif data.startswith("add_q_"):
        cat_id = data.split("_")[2]
        context.user_data.update({'state': 'WAIT_Q', 'cur_cat': cat_id})
        await query.edit_message_text("📝 ارسل نص السؤال:")

# --- 3. معالج النصوص (تحكم + حفظ بيانات) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if update.effective_user.id != OWNER_ID: return
    state = context.user_data.get('state')
    await update.message.delete()

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        return

    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        # العودة لقائمة الأقسام فوراً
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ لإضافة قسم", callback_data="gui_add_cat")])
        await update.message.reply_text(f"✅ تم إضافة قسم '{text}' بنجاح!", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == 'WAIT_Q':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_A1'})
        await update.message.reply_text("ارسل الإجابة الأولى:")

    elif state == 'WAIT_A1':
        context.user_data.update({'a1': text, 'state': None})
        keyboard = [[InlineKeyboardButton("✅ نعم", callback_data="ask_alt_yes"), InlineKeyboardButton("❌ لا", callback_data="ask_alt_no")]]
        await update.message.reply_text("هل تريد إضافة إجابة ثانية؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == 'WAIT_A2':
        await save_question(update, context, text)

async def save_question(update, context, alt_ans):
    cat_id = context.user_data['cur_cat']
    supabase.table("questions").insert({"category_id": int(cat_id), "question_content": context.user_data['q_txt'], "correct_answer": context.user_data['a1'], "alt_answer": alt_ans}).execute()
    context.user_data['state'] = None
    await update.effective_chat.send_message("🎉 تم حفظ السؤال بنجاح!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقسم", callback_data=f"manage_cat_{cat_id}")]]))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
    
