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

# --- القوائم الرئيسية ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 1. رسالة الترحيب والتشغيل ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dev_acc = "@Ya_79k"
    welcome_text = (
        "أهلاً بك في بوت المسابقات المتطور\n\n"
        "البوت متاح للجميع لإنشاء أقسامهم الخاصة\n\n"
        "كيفية التشغيل:\n"
        "• ارسل كلمة (تحكم) لفتح لوحتك الخاصة\n"
        "• يمكنك إدارة أقسامك وأسئلتك بخصوصية تامة\n\n"
        f"تم تطوير هذا البوت بواسطة المطور: ياسر ( {dev_acc} )"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu())

# --- 2. معالج الأزرار التفاعلية ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    # استعراض الأقسام (خصوصية: كل شخص يرى قسمه فقط)
    if data == "gui_view_cats" or data == "view_all_admin":
        if data == "view_all_admin" and user_id == OWNER_ID:
            res = supabase.table("categories").select("*").execute()
            title = "استعراض كافة الأقسام (وضع الأدمن):"
        else:
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            title = "أقسامك الخاصة المتاحة:"
            
        keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
        if user_id == OWNER_ID and data != "view_all_admin":
            keyboard.append([InlineKeyboardButton("👁 استعراض أقسام الجميع", callback_data="view_all_admin")])
        keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
        await query.edit_message_text(title, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "gui_add_cat":
        context.user_data['state'] = 'WAIT_CAT_NAME'
        await query.edit_message_text("ارسل اسم القسم الجديد الآن:")

    # إدارة القسم والأسئلة
    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        cat_res = supabase.table("categories").select("*").eq("id", cat_id).single().execute()
        q_res = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
        text = f"قسم: {cat_res.data['name']}\nعدد الأسئلة: {q_res.count}"
        keyboard = [
            [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"conf_del_{cat_id}"), InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"edit_n_{cat_id}")],
            [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("📝 عرض الأسئلة", callback_data=f"vq_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # --- ميزة تهيئة المسابقة (جديد) ---
    elif data == "setup_quiz":
        res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
        if not res.data:
            await query.edit_message_text("⚠️ ليس لديك أقسام بعد، قم بإنشاء قسم أولاً.", reply_markup=get_main_menu())
            return
        keyboard = [[InlineKeyboardButton(f"القسم: {c['name']}", callback_data=f"sel_q_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
        await query.edit_message_text("🏆 اختر القسم الذي تريد بدء المسابقة منه:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("sel_q_cat_"):
        cat_id = data.split("_")[3]
        context.user_data['quiz_cat'] = cat_id
        keyboard = [
            [InlineKeyboardButton("15 ثانية", callback_data="time_15"), InlineKeyboardButton("30 ثانية", callback_data="time_30")],
            [InlineKeyboardButton("60 ثانية", callback_data="time_60"), InlineKeyboardButton("بدون وقت", callback_data="time_0")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz")]
        ]
        await query.edit_message_text("⏱ حدد وقت الإجابة لكل سؤال:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("time_"):
        context.user_data['quiz_time'] = data.split("_")[1]
        await query.edit_message_text("✅ تم ضبط الإعدادات! جاري تجهيز المسابقة...", reply_markup=get_main_menu())

    elif data == "back_to_main":
        await query.edit_message_text("لوحة التحكم الرئيسية:", reply_markup=get_main_menu())

    elif data == "close_menu":
        await query.message.delete()

# --- 3. معالج النصوص ---
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
        await update.message.reply_text(f"تم إضافة قسم {text} بنجاح!")

# --- تشغيل البوت ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
    
