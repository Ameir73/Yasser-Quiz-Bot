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

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# 1. الترحيب (ياسر @Ya_79k)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "أهلاً بك في بوت المسابقات المتطور\n\n"
        "البوت متاح للجميع لإنشاء أقسامهم الخاصة\n\n"
        "كيفية التشغيل:\n"
        "• ارسل كلمة (تحكم) لفتح لوحتك الخاصة\n"
        "• يمكنك إدارة أقسامك وأسئلتك بخصوصية تامة\n\n"
        "تم تطوير هذا البوت بواسطة المطور: ياسر ( @Ya_79k )"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu())

# 2. معالج الأزرار المصلح بالكامل
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    try:
        if data == "gui_view_cats":
            # جلب الأقسام الخاصة بالمستخدم فقط
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
            
            # ميزة الأدمن ياسر: رؤية كل الأقسام
            if user_id == OWNER_ID:
                keyboard.append([InlineKeyboardButton("👁 استعراض أقسام الجميع (أدمن)", callback_data="view_all_admin")])
                
            keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
            await query.edit_message_text("أقسامك الخاصة المتاحة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "view_all_admin" and user_id == OWNER_ID:
            res = supabase.table("categories").select("*").execute()
            keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")])
            await query.edit_message_text("كافة أقسام النظام (وضع الإدارة):", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "gui_add_cat":
            context.user_data['state'] = 'WAIT_CAT_NAME'
            await query.edit_message_text("ارسل اسم القسم الجديد الآن:")

        elif data.startswith("manage_cat_"):
            cat_id = data.split("_")[2]
            cat_res = supabase.table("categories").select("*").eq("id", cat_id).single().execute()
            
            # التأكد من الملكية أو صلاحية الأدمن
            if cat_res.data['created_by'] != user_id and user_id != OWNER_ID:
                await query.edit_message_text("⚠️ هذا القسم ليس ملكك.")
                return

            keyboard = [
                [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"conf_del_{cat_id}"), InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"edit_n_{cat_id}")],
                [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("📝 عرض الأسئلة", callback_data=f"vq_{cat_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
            ]
            await query.edit_message_text(f"قسم: {cat_res.data['name']}\nتحكم في إعداداتك:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("conf_del_"):
            cat_id = data.split("_")[2]
            keyboard = [[InlineKeyboardButton("نعم، احذف ✅", callback_data=f"exec_del_{cat_id}"), 
                         InlineKeyboardButton("لا، تراجع ❌", callback_data=f"manage_cat_{cat_id}")]]
            await query.edit_message_text("⚠️ هل أنت متأكد من حذف القسم؟", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("exec_del_"):
            cat_id = data.split("_")[2]
            supabase.table("categories").delete().eq("id", cat_id).execute()
            await query.edit_message_text("✅ تم الحذف بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="gui_view_cats")]]))

        elif data == "ask_alt_yes":
            context.user_data['state'] = 'WAIT_A2'
            await query.edit_message_text("ارسل الإجابة البديلة الثانية:")

        elif data == "ask_alt_no":
            await save_question(update, context, None)

        elif data == "back_to_main":
            await query.edit_message_text("لوحة التحكم الرئيسية:", reply_markup=get_main_menu())

    except Exception as e:
        logging.error(f"Error: {e}")

# 3. معالج النصوص
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    state = context.user_data.get('state')
    await update.message.delete()

    if text == "تحكم":
        await update.message.reply_text("لوحة التحكم الخاصة بك:", reply_markup=get_main_menu())
        return

    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text, "created_by": user_id}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم إنشاء قسم {text} بنجاح!")

    elif state == 'WAIT_Q':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_A1'})
        await update.message.reply_text("ارسل الإجابة الأولى:")

    elif state == 'WAIT_A1':
        context.user_data.update({'a1': text, 'state': None})
        keyboard = [[InlineKeyboardButton("نعم ✅", callback_data="ask_alt_yes"), InlineKeyboardButton("لا ❌", callback_data="ask_alt_no")]]
        await update.message.reply_text("هل تريد إضافة إجابة ثانية؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == 'WAIT_A2':
        await save_question(update, context, text)

async def save_question(update, context, alt_ans):
    cat_id = context.user_data['cur_cat']
    supabase.table("questions").insert({
        "category_id": int(cat_id), "question_content": context.user_data['q_txt'], 
        "correct_answer": context.user_data['a1'], "alt_answer": alt_ans, "created_by": update.effective_user.id
    }).execute()
    context.user_data['state'] = None
    await update.effective_chat.send_message("🎉 تم حفظ السؤال بنجاح!")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
    
