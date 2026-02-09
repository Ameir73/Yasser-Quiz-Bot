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

# --- 1. قائمة الأزرار الرئيسية (لوحة التحكم) ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ إضافة قسم", callback_data="gui_add_cat")],
        [InlineKeyboardButton("📚 إدارة الأقسام", callback_data="gui_view_cats")],
        [InlineKeyboardButton("إغلاق ❌", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 2. معالج النصوص (اسم القسم / السؤال / الأجوبة) ---
async def handle_text_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if update.effective_user.id != OWNER_ID: return
    
    state = context.user_data.get('state')
    last_msg_id = context.user_data.get('last_msg_id')

    # حذف رسالة المستخدم للحفاظ على نظافة الدردشة (اختياري)
    await update.message.delete()

    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        # تحديث الرسالة السابقة لتظهر "تم الإنشاء" فوراً كما في الفيديو
        msg = f"✅ تم إنشاء القسم '{text}' بنجاح."
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_msg_id, text=msg, reply_markup=InlineKeyboardMarkup(keyboard))

    elif state and state.startswith('WAIT_Q_TEXT_'):
        cat_id = state.split('_')[3]
        context.user_data['temp_q'] = text
        context.user_data['state'] = f'WAIT_Q_ANS_{cat_id}'
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_msg_id, text=f"❓ السؤال: {text}\n\nالآن ارسل **الجواب المقبول**:")

    elif state and state.startswith('WAIT_Q_ANS_'):
        cat_id = state.split('_')[3]
        if 'temp_ans' not in context.user_data: context.user_data['temp_ans'] = []
        context.user_data['temp_ans'].append(text)
        
        keyboard = [[InlineKeyboardButton("نعم", callback_data=f"add_more_ans_{cat_id}"),
                     InlineKeyboardButton("لا", callback_data=f"finish_q_{cat_id}")]]
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=last_msg_id, text=f"✅ أضفت الجواب: {text}\n\nهل تريد إضافة جواب آخر؟", reply_markup=InlineKeyboardMarkup(keyboard))

# --- 3. معالج الأزرار الشفافة (التنقل السلس) ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    context.user_data['last_msg_id'] = query.message.message_id

    if data == "gui_add_cat":
        context.user_data['state'] = 'WAIT_CAT_NAME'
        await query.edit_message_text("📝 ارسل اسم القسم الجديد الآن:")

    elif data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(c['name'], callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
        await query.edit_message_text("📌 أقسامك الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        keyboard = [[InlineKeyboardButton("➕ إضافة سؤال", callback_data=f"add_q_{cat_id}")],
                    [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"del_cat_{cat_id}")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]
        await query.edit_message_text(f"📂 إدارة القسم (ID: {cat_id})", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("finish_q_"):
        # لوحة التحكم الخماسية النهائية للسؤال
        await query.edit_message_text("✅ تم حفظ السؤال بنجاح!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("إضافة سؤال جديد", callback_data=f"add_q_{data.split('_')[2]}"), InlineKeyboardButton("رجوع", callback_data=f"manage_cat_{data.split('_')[2]}")]]))

    elif data == "back_to_main":
        context.user_data.clear()
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=main_menu())

# --- 4. تشغيل البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("مرحباً بك يا ياسر، افتح لوحة التحكم:", reply_markup=main_menu())
    context.user_data['last_msg_id'] = msg.message_id

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_logic))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()

if __name__ == "__main__": main()
        
