Import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- إعدادات ياسر ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 1. القائمة الرئيسية ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_add_cat"), 
         InlineKeyboardButton("📅 جلسة سابقة", callback_data="old_sessions")],
        [InlineKeyboardButton("🛒 سوق", callback_data="market"),
         InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")], # تغيير الـ callback هنا
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 2. واجهة تهيئة المسابقة (التي طلبتها في الصورة) ---
def get_setup_quiz_menu():
    keyboard = [
        [InlineKeyboardButton("أقسام الأعضاء", callback_data="members_cats"),
         InlineKeyboardButton("أقسام البوت", callback_data="bot_cats")],
        [InlineKeyboardButton("الأقسام المختارة", callback_data="selected_cats"),
         InlineKeyboardButton("أقسامك الخاصة", callback_data="gui_view_cats")], # زر أقسامك الخاصة يفتح الأقسام الحالية
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 3. معالج الأزرار ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # فتح واجهة تهيئة المسابقة الجديدة
    if data == "setup_quiz":
        text = "أهلاً بك! قم بتهيئة المسابقة عن طريق اختيار أحد الخيارات التالية: 🎉"
        await query.edit_message_text(text, reply_markup=get_setup_quiz_menu())

    # عرض الأقسام الخاصة (عند الضغط على أقسامك الخاصة)
    elif data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz")]) # يرجع لواجهة التهيئة
        await query.edit_message_text("📂 **أقسامك الخاصة**\n\nمن هنا تستطيع التعامل مع أقسامك.", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_to_main":
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=get_main_menu())

    # (بقية العمليات السابقة مثل الحذف والإضافة تبقى كما هي في الكود السابق)
    # ... [بقية معالجات manage_cat و del_cat و add_q] ...

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if update.effective_user.id != OWNER_ID: return
    if text == "لوحة التحكم" or text == "تحكم":
        await update.message.delete()
        await update.message.reply_text("⚙️ لوحة التحكم الشخصية:", reply_markup=get_main_menu())

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("أهلاً ياسر، ارسل 'تحكم'")))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
لنرجع هنا
