import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات التي زودتني بها يا ياسر ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
DEVELOPER_CHAT = "https://t.me/Ya_79k"
OWNER_ID = 7988144062

# ربط قاعدة البيانات
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 1. الأوامر الأساسية ورسالة الترحيب ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 أهلاً بك في بوت المسابقات المتطور!\n\n"
        "🔸 اكتب كلمة **تحكم** لعرض قائمة الإدارة.\n"
        "🔸 أو اكتب **+مسابقة** لتشغيلها في القروب.\n\n"
        "للتواصل مع المطور، اضغط على الزر أدناه."
    )
    keyboard = [[InlineKeyboardButton("👨‍💻 مطور البوت", url=DEVELOPER_CHAT)]]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def main_control_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "تحكم":
        user_id = update.effective_user.id
        # التحقق من أن المستخدم هو المطور أو مشرف
        user_status = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        if user_id != OWNER_ID and user_status.status not in ['administrator', 'creator']:
            return

        msg = "⚙️ قم بالتحكم في البوت عن طريق الأزرار في الأسفل."
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قسم أسئلة", callback_data="gui_add_cat")],
            [InlineKeyboardButton("📚 أسئلة الاختبار", callback_data="gui_view_cats")],
            [InlineKeyboardButton("👨‍💻 مطور البوت", url=DEVELOPER_CHAT)]
        ]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# --- 2. نظام معالجة الأزرار الشفافة ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # واجهة إضافة قسم
    if data == "gui_add_cat":
        msg = "من هنا تستطيع التعامل مع أقسامك الخاصة.\n\n➕ لإضافة قسم\n\n🔙 للرجوع"
        keyboard = [[InlineKeyboardButton("➕ لإضافة قسم", callback_data="req_cat_name"),
                     InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "req_cat_name":
        await query.message.reply_text("ارسل اسم القسم الجديد:")
        context.user_data['state'] = 'WAIT_CAT_NAME'

    # عرض أقسام الاختبار (ليستة)
    elif data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        cats = res.data
        if not cats:
            await query.edit_message_text("❌ لا توجد أقسام حالياً.", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")]]))
            return
        
        keyboard = [[InlineKeyboardButton(c['name'], callback_data=f"manage_cat_{c['id']}")] for c in cats]
        keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
        await query.edit_message_text("📌 اختر القسم المطلوب إدارته:", reply_markup=InlineKeyboardMarkup(keyboard))

    # واجهة إدارة قسم محدد
    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        res = supabase.table("categories").select("name").eq("id", cat_id).single().execute()
        cat_name = res.data['name']
        
        msg = f"📌 أنت الآن في قسم [{cat_name}]\n🔢 عدد أسئلتك الحالية: جاري التحميل...\n\nاختر من الخدمات التالية:"
        keyboard = [
            [InlineKeyboardButton("📝 تغيير اسم القسم", callback_data=f"ren_cat_{cat_id}"),
             InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"del_cat_{cat_id}")],
            [InlineKeyboardButton("➕ إضافة سؤال", callback_data=f"add_q_{cat_id}")],
            [InlineKeyboardButton("📄 عرض الأسئلة", callback_data=f"list_q_{cat_id}"),
             InlineKeyboardButton("🔙 للرجوع", callback_data="gui_view_cats")]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# --- 3. تشغيل البوت ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Text(["تحكم", "+مسابقة"]), main_control_panel))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("✅ البوت يعمل الآن يا ياسر على المعرف @Ya_79kbot")
    app.run_polling()

if __name__ == "__main__":
    main()
  
