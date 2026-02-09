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
    telegram_link = "https://t.me/Ya_79k"
    welcome_text = (
        "👋 **أهلاً بك في بوت المسابقات المطور!**\n\n"
        "📖 **كيفية التشغيل:**\n"
        "• ارسل كلمة (**تحكم**) لفتح لوحة الإدارة.\n\n"
        "👑 **المطور:** [ياسر]({telegram_link})"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode='Markdown', disable_web_page_preview=False)

# --- معالج الأزرار ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    try:
        if data == "gui_view_cats":
            res = supabase.table("categories").select("*").execute()
            keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
            keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
            await query.edit_message_text("📂 الأقسام المتاحة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("manage_cat_"):
            cat_id = data.split("_")[2]
            cat_res = supabase.table("categories").select("name").eq("id", cat_id).single().execute()
            
            # --- 1. تحديث عداد الأسئلة ---
            q_res = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
            count = q_res.count if q_res.count is not None else 0
            
            text = f"📌 إدارة قسم: {cat_res.data['name']}\n🔢 عدد الأسئلة: {count}"
            keyboard = [
                [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"conf_del_{cat_id}"), InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"edit_n_{cat_id}")],
                [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("📝 عرض الأسئلة", callback_data=f"vq_{cat_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("vq_"): # --- 2. تفعيل عرض الأسئلة ---
            cat_id = data.split("_")[1]
            questions = supabase.table("questions").select("*").eq("category_id", cat_id).execute()
            
            if not questions.data:
                txt = "⚠️ القسم لا يحتوي على أسئلة."
            else:
                txt = "📑 قائمة الأسئلة:\n\n"
                for i, q in enumerate(questions.data, 1):
                    txt += f"{i}- {q['question_content']}\n✅ ج1: {q['correct_answer']}"
                    if q.get('alt_answer'): txt += f" | ج2: {q['alt_answer']}"
                    txt += "\n----------------\n"
            
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للقسم", callback_data=f"manage_cat_{cat_id}")]]))

        elif data == "gui_add_cat":
            context.user_data['state'] = 'WAIT_CAT_NAME'
            await query.edit_message_text("📝 ارسل اسم القسم الجديد:")

        elif data.startswith("add_q_"):
            cat_id = data.split("_")[2]
            context.user_data.update({'state': 'WAIT_Q', 'cur_cat': cat_id})
            await query.edit_message_text("📝 ارسل نص السؤال:")

        elif data.startswith("edit_n_"):
            cat_id = data.split("_")[2]
            context.user_data.update({'state': 'WAIT_NEW_NAME', 'cur_cat': cat_id})
            await query.edit_message_text("📝 ارسل الاسم الجديد:")

        elif data == "ask_alt_yes":
            context.user_data['state'] = 'WAIT_A2'
            await query.edit_message_text("📝 ارسل الإجابة الثانية:")

        elif data == "ask_alt_no":
            await save_question(update, context, None)

        elif data.startswith("conf_del_"):
            cat_id = data.split("_")[2]
            keyboard = [[InlineKeyboardButton("✅ نعم", callback_data=f"execute_del_{cat_id}"), InlineKeyboardButton("❌ لا", callback_data=f"manage_cat_{cat_id}")]]
            await query.edit_message_text("⚠️ هل تريد الحذف؟", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("execute_del_"):
            cat_id = data.split("_")[2]
            supabase.table("categories").delete().eq("id", cat_id).execute()
            await query.edit_message_text("✅ تم حذف القسم.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="gui_view_cats")]]))

        elif data == "back_to_main":
            await query.edit_message_text("⚙️ الرئيسية:", reply_markup=get_main_menu())

    except Exception as e:
        logging.error(f"Error: {e}")

# --- معالج النصوص ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    state = context.user_data.get('state')
    try: await update.message.delete()
    except: pass

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        return

    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(f"{c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
        await update.message.reply_text(f"✅ تم إضافة {text}!\n📂 الأقسام المتاحة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == 'WAIT_NEW_NAME':
        cat_id = context.user_data['cur_cat']
        supabase.table("categories").update({"name": text}).eq("id", cat_id).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم تغيير الاسم إلى: {text}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للقسم", callback_data=f"manage_cat_{cat_id}")]]))

    elif state == 'WAIT_Q':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_A1'})
        await update.message.reply_text("ارسل الإجابة الأولى:")

    elif state == 'WAIT_A1':
        context.user_data.update({'a1': text, 'state': None})
        keyboard = [[InlineKeyboardButton("✅ نعم", callback_data="ask_alt_yes"), InlineKeyboardButton("❌ لا", callback_data="ask_alt_no")]]
        await update.message.reply_text("إضافة إجابة ثانية؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == 'WAIT_A2':
        await save_question(update, context, text)

async def save_question(update, context, alt_ans):
    cat_id = context.user_data['cur_cat']
    supabase.table("questions").insert({
        "category_id": int(cat_id), 
        "question_content": context.user_data['q_txt'], 
        "correct_answer": context.user_data['a1'], 
        "alt_answer": alt_ans
    }).execute()
    context.user_data['state'] = None
    await update.effective_chat.send_message("🎉 تم الحفظ!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للقسم", callback_data=f"manage_cat_{cat_id}")]]))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
            
