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

# --- 1. القائمة الرئيسية (كما في الفيديو) ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_add_cat"), 
         InlineKeyboardButton("📅 جلسة سابقة", callback_data="old_sessions")],
        [InlineKeyboardButton("🛒 سوق", callback_data="market"),
         InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="gui_view_cats")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 2. واجهة إدارة القسم (التصميم الاحترافي) ---
def get_manage_cat_menu(cat_id):
    keyboard = [
        [InlineKeyboardButton("✏️ تغيير اسم القسم", callback_data=f"rename_{cat_id}")],
        [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"del_cat_{cat_id}")],
        [InlineKeyboardButton("➕ مباشر سريع", callback_data=f"add_q_{cat_id}"),
         InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}")],
        [InlineKeyboardButton("➕ سؤال خيارات", callback_data=f"add_q_opt_{cat_id}")],
        [InlineKeyboardButton("✨ أبيات تنقيط", callback_data=f"poetry_{cat_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 3. المعالجات الأساسية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    text = f"مرحباً بك في بوت مسابقات كوين.\n\nتستطيع البدء بإرسال عبارة (لوحة التحكم)."
    msg = await update.message.reply_text(text, reply_markup=get_main_menu())
    context.user_data['last_msg_id'] = msg.message_id

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    message_id = query.message.message_id
    context.user_data['last_msg_id'] = message_id

    if data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        # عرض الأقسام كأزرار عريضة
        keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("🔙 الرجوع", callback_data="back_to_main")])
        await query.edit_message_text("📂 **أقسامك الخاصة**\n\nمن هنا تستطيع التعامل مع أقسامك.", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        # جلب عدد الأسئلة للقسم لظهوره في الواجهة
        q_count = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
        count = q_count.count if q_count.count else 0
        text = f"📌 أنت الآن في قسم (ID: {cat_id})\n🔢 عدد أسئلتك الحالية: {count}\n\nاختر من الخدمات التالية:"
        await query.edit_message_text(text, reply_markup=get_manage_cat_menu(cat_id))

    elif data.startswith("del_cat_"):
        cat_id = data.split("_")[2]
        supabase.table("categories").delete().eq("id", cat_id).execute()
        await query.edit_message_text("🗑️ تم حذف القسم بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]))

    elif data == "back_to_main":
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=get_main_menu())

    elif data == "close_menu":
        await query.delete_message()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if update.effective_user.id != OWNER_ID: return
    
    if text == "لوحة التحكم" or text == "تحكم":
        await update.message.delete()
        msg = await update.message.reply_text("⚙️ لوحة التحكم الشخصية:", reply_markup=get_main_menu())
        context.user_data['last_msg_id'] = msg.message_id

# --- تشغيل البوت ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
                
