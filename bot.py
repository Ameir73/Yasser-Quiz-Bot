import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- إعدادات ياسر الشخصية ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 1. القوالب الرسومية للقوائم ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), 
         InlineKeyboardButton("📅 جلسة سابقة", callback_data="old_sessions")],
        [InlineKeyboardButton("🛒 سوق", callback_data="market"),
         InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_setup_quiz_menu():
    keyboard = [
        [InlineKeyboardButton("أقسام الأعضاء", callback_data="members_cats"),
         InlineKeyboardButton("أقسام البوت", callback_data="bot_cats")],
        [InlineKeyboardButton("الأقسام المختارة", callback_data="selected_cats"),
         InlineKeyboardButton("أقسامك الخاصة", callback_data="gui_view_cats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 2. معالج الأزرار التفاعلية ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    message_id = query.message.message_id
    context.user_data['last_msg_id'] = message_id

    # العودة للقائمة الرئيسية
    if data == "back_to_main":
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=get_main_menu())

    # واجهة تهيئة المسابقة
    elif data == "setup_quiz":
        text = "أهلاً بك! قم بتهيئة المسابقة عن طريق اختيار أحد الخيارات التالية: 🎉"
        await query.edit_message_text(text, reply_markup=get_setup_quiz_menu())

    # واجهة "أقسامك الخاصة" (دين، عامه، إلخ)
    elif data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = []
        temp_row = []
        for c in res.data:
            temp_row.append(InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}"))
            if len(temp_row) == 2:
                keyboard.append(temp_row)
                temp_row = []
        if temp_row: keyboard.append(temp_row)
        
        keyboard.append([InlineKeyboardButton("➕ لإضافة قسم", callback_data="gui_add_cat")])
        keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
        
        text = "┏━━━━━━━━━━━━┓\n       أقسامك الخاصة       \n┗━━━━━━━━━━━━┛\n\nمن هنا تستطيع التعامل مع أقسامك الخاصة."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بدء إضافة قسم جديد
    elif data == "gui_add_cat":
        context.user_data['state'] = 'WAIT_CAT_NAME'
        await query.edit_message_text("📝 ارسل الآن اسم القسم الجديد:")

    # إدارة قسم محدد
    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        keyboard = [
            [InlineKeyboardButton("➕ إضافة سؤال", callback_data=f"add_q_{cat_id}")],
            [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"del_cat_{cat_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(f"📁 إدارة القسم (ID: {cat_id})", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("del_cat_"):
        cat_id = data.split("_")[2]
        supabase.table("categories").delete().eq("id", cat_id).execute()
        await query.edit_message_text("🗑️ تم حذف القسم بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]))

    elif data == "close_menu":
        await query.delete_message()

# --- 3. معالج النصوص (تحكم) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if update.effective_user.id != OWNER_ID: return
    
    state = context.user_data.get('state')
    last_msg_id = context.user_data.get('last_msg_id')
    chat_id = update.effective_chat.id

    if text in ["لوحة التحكم", "تحكم"]:
        await update.message.delete()
        msg = await update.message.reply_text("⚙️ لوحة التحكم الشخصية:", reply_markup=get_main_menu())
        context.user_data['last_msg_id'] = msg.message_id
        return

    # منطق حفظ القسم الجديد
    if state == 'WAIT_CAT_NAME':
        await update.message.delete()
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        await context.bot.edit_message_text(chat_id=chat_id, message_id=last_msg_id, text=f"✅ تم إنشاء القسم '{text}' بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="gui_view_cats")]]))

# --- 4. التشغيل الرئيسي ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("أهلاً ياسر، ارسل 'تحكم'")))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
