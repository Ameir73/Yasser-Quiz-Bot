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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "أهلاً بك يا ياسر في لوحة التحكم المتطورة @Ya_79k"
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu())

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    try:
        if data == "gui_view_cats":
            # محاولة جلب الأقسام (تجاوز خطأ العمود غير الموجود)
            try:
                res = supabase.table("categories").select("*").execute()
                keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
            except:
                keyboard = []
            
            keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
            keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
            await query.edit_message_text("قائمة الأقسام المتاحة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("manage_cat_"):
            cat_id = data.split("_")[2]
            cat_res = supabase.table("categories").select("*").eq("id", cat_id).single().execute()
            keyboard = [
                [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"conf_del_{cat_id}"), InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"edit_n_{cat_id}")],
                [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("📝 عرض الأسئلة", callback_data=f"vq_{cat_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
            ]
            await query.edit_message_text(f"إدارة قسم: {cat_res.data['name']}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "gui_add_cat":
            context.user_data['state'] = 'WAIT_CAT_NAME'
            await query.edit_message_text("📝 ارسل اسم القسم الجديد:")

        elif data == "back_to_main":
            await query.edit_message_text("القائمة الرئيسية:", reply_markup=get_main_menu())

    except Exception as e:
        logging.error(f"Error in buttons: {e}")
        await query.message.reply_text(f"⚠️ حدث خطأ تقني: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    state = context.user_data.get('state')
    
    if text == "تحكم":
        await update.message.reply_text("لوحة التحكم الخاصة بك:", reply_markup=get_main_menu())
        return

    if state == 'WAIT_CAT_NAME':
        # الحفظ بدون عمود created_by لتجنب الأخطاء مؤقتاً
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم إضافة قسم {text} بنجاح!")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
            
