import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات الثابتة ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062 

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- الدوال المساعدة للوحات التحكم ---

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(settings):
    keyboard = [
        [InlineKeyboardButton(f"عدد الأسئلة الحالي: {settings['num_questions']}", callback_data="none")],
        [InlineKeyboardButton(f"✅ {n}" if settings['num_questions'] == n else str(n), callback_data=f"set_num_{n}") for n in [20, 25, 30, 35, 40, 45]],
        [
            InlineKeyboardButton(f"🚀 السرعة" if settings['timing_mode'] == 'السرعة' else "🕒 الوقت", callback_data="toggle_timing"),
            InlineKeyboardButton(f"المنافسة: {settings['comp_type']}", callback_data="toggle_comp")
        ],
        [
            InlineKeyboardButton(f"● مباشرة" if settings['ans_type'] == 'مباشرة' else "○ مباشرة", callback_data="ans_direct"),
            InlineKeyboardButton(f"● خيارات" if settings['ans_type'] == 'خيارات' else "○ خيارات", callback_data="ans_opt"),
            InlineKeyboardButton(f"● الكل" if settings['ans_type'] == 'الكل' else "○ الكل", callback_data="ans_all")
        ],
        [InlineKeyboardButton("حفظ المسابقة وتسميتها ✅", callback_data="save_quiz_final")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz")]
    ]
    return InlineKeyboardMarkup(keyboard)

# 1. رسالة الترحيب
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_link = "https://t.me/Ya_79k"
    welcome_text = (
        "👋 **أهلاً بك في بوت المسابقات المطور!**\n\n"
        "📖 **كيفية التشغيل:**\n"
        "• ارسل كلمة (**تحكم**) لإدارة أقسامك بخصوصية.\n\n"
        f"👑 **المطور:** [ياسر]({telegram_link})"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode='Markdown')

# --- دالة حفظ السؤال ---
async def save_question(update_or_query, context, alt_ans):
    cat_id = context.user_data.get('cur_cat')
    user_id = update_or_query.from_user.id if hasattr(update_or_query, 'from_user') else update_or_query.effective_user.id
    try:
        supabase.table("questions").insert({
            "category_id": int(cat_id), "question_content": context.user_data['q_txt'], 
            "correct_answer": context.user_data['a1'], "alt_answer": alt_ans, "created_by": user_id
        }).execute()
        context.user_data['state'] = None
        text = "🎉 تم حفظ السؤال بنجاح!"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للقسم", callback_data=f"manage_cat_{cat_id}")]])
        if hasattr(update_or_query, 'edit_message_text'): await update_or_query.edit_message_text(text, reply_markup=reply_markup)
        else: await update_or_query.effective_chat.send_message(text, reply_markup=reply_markup)
    except Exception as e: logging.error(f"Save Error: {e}")

# 2. معالج الأزرار 
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    if 'temp_setup' not in context.user_data:
        context.user_data['temp_setup'] = {'num_questions': 20, 'timing_mode': 'الوقت', 'comp_type': 'خاصة', 'ans_type': 'مباشرة', 'selected_cats': []}

    try:
        if data.startswith("conf_del_"):
            cat_id = data.split("_")[2]
            keyboard = [[InlineKeyboardButton("✅ نعم، احذف", callback_data=f"execute_del_{cat_id}"), InlineKeyboardButton("❌ لا، تراجع", callback_data=f"manage_cat_{cat_id}")]]
            await query.edit_message_text("⚠️ هل أنت متأكد من حذف القسم نهائياً؟", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        elif data.startswith("execute_del_"):
            cat_id = data.split("_")[2]
            supabase.table("categories").delete().eq("id", cat_id).execute()
            await query.edit_message_text("✅ تم حذف القسم بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="gui_view_cats")]]))
            return

        elif data.startswith("edit_n_"):
            cat_id = data.split("_")[2]
            context.user_data.update({'state': 'WAIT_NEW_NAME', 'cur_cat': cat_id})
            await query.edit_message_text("📝 ارسل الاسم الجديد للقسم:")
            return

        elif data.startswith("vq_"):
            cat_id = data.split("_")[1]
            questions = supabase.table("questions").select("*").eq("category_id", cat_id).execute()
            txt = "📑 قائمة الأسئلة:\n\n" if questions.data else "⚠️ لا توجد أسئلة."
            for i, q in enumerate(questions.data, 1):
                txt += f"{i}- {q['question_content']}\n✅ {q['correct_answer']}\n---\n"
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data=f"manage_cat_{cat_id}")]]))
            return

        elif data.startswith("add_q_"):
            cat_id = data.split("_")[2]
            context.user_data.update({'state': 'WAIT_Q', 'cur_cat': cat_id})
            await query.edit_message_text("📝 ارسل نص السؤال:")
            return

        if data == "setup_quiz":
            keyboard = [
                [InlineKeyboardButton("أقسام الأعضاء", callback_data="quiz_members"), InlineKeyboardButton("أقسام البوت", callback_data="quiz_bot")],
                [InlineKeyboardButton("الأقسام المختارة", callback_data="quiz_selected"), InlineKeyboardButton("أقسامك الخاصة", callback_data="gui_view_cats")],
                [InlineKeyboardButton("⚙️ الإعدادات الفنية", callback_data="go_to_settings")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
            ]
            await query.edit_message_text("🎉 قم بتهيئة المسابقة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "go_to_settings":
            await query.edit_message_text("⚙️ اضبط إعدادات المسابقة:", reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

        elif data.startswith("set_num_"):
            context.user_data['temp_setup']['num_questions'] = int(data.split("_")[2])
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

        elif data == "save_quiz_final":
            context.user_data['state'] = 'WAIT_QUIZ_NAME'
            await query.edit_message_text("📝 ممتاز! الآن ارسل (اسم المسابقة) لاعتمادها:")

        elif data == "gui_view_cats":
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
            keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
            await query.edit_message_text("📂 أقسامك الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "gui_add_cat":
            context.user_data['state'] = 'WAIT_CAT_NAME'
            await query.edit_message_text("📝 ارسل اسم القسم الجديد:")

        elif data.startswith("manage_cat_"):
            cat_id = data.split("_")[2]
            cat_res = supabase.table("categories").select("*").eq("id", cat_id).single().execute()
            q_res = supabase.table("questions").select("*", count="exact").eq("category_id", cat_id).execute()
            count = q_res.count if q_res.count is not None else 0
            text = f"📌 إدارة قسم: {cat_res.data['name']}\n🔢 عدد الأسئلة: {count}"
            keyboard = [
                [InlineKeyboardButton("🗑️ حذف القسم", callback_data=f"conf_del_{cat_id}"), InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"edit_n_{cat_id}")],
                [InlineKeyboardButton("➕ سؤال مباشر", callback_data=f"add_q_{cat_id}"), InlineKeyboardButton("📝 عرض الأسئلة", callback_data=f"vq_{cat_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "back_to_main": await query.edit_message_text("⚙️ الرئيسية:", reply_markup=get_main_menu())
        elif data == "ask_alt_no": await save_question(query, context, None)
        elif data == "ask_alt_yes":
            context.user_data['state'] = 'WAIT_A2'
            await query.edit_message_text("📝 ارسل الإجابة البديلة:")

    except Exception as e: logging.error(f"Callback Error: {e}")

# 3. معالج النصوص
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    state = context.user_data.get('state')

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        return

    # إدارة الحالات 
    if state == 'WAIT_NEW_NAME':
        cat_id = context.user_data['cur_cat']
        supabase.table("categories").update({"name": text}).eq("id", cat_id).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم تغيير الاسم لـ {text}!")
    
    elif state == 'WAIT_QUIZ_NAME':
        s = context.user_data['temp_setup']
        res_set = supabase.table("quiz_settings").insert({
            "user_id": user_id, "num_questions": s['num_questions'], "timing_mode": s['timing_mode'],
            "answer_type": s['ans_type'], "competition_type": s['comp_type']
        }).execute()
        s_id = res_set.data[0]['id']
        supabase.table("active_quizzes").insert({"quiz_name": text, "settings_id": s_id, "created_by": user_id}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم حفظ المسابقة باسم '{text}' بنجاح!")

    elif state == 'WAIT_CAT_NAME':
        # [الإصلاح]: حفظ القسم ثم الرجوع خطوة للخلف فوراً
        supabase.table("categories").insert({"name": text, "created_by": user_id}).execute()
        context.user_data['state'] = None
        
        # جلب القائمة المحدثة لعرضها مجدداً (الرجوع للخلف خطوة)
        res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
        keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
        keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
        
        await update.message.reply_text(f"✅ تم إضافة القسم '{text}' بنجاح! إليك قائمتك المحدثة:", 
                                       reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == 'WAIT_Q':
        context.user_data.update({'q_txt': text, 'state': 'WAIT_A1'})
        await update.message.reply_text("ارسل الإجابة الأولى:")

    elif state == 'WAIT_A1':
        context.user_data.update({'a1': text, 'state': None})
        keyboard = [[InlineKeyboardButton("✅ نعم", callback_data="ask_alt_yes"), InlineKeyboardButton("❌ لا", callback_data="ask_alt_no")]]
        await update.message.reply_text("هل تريد إضافة إجابة بديلة؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == 'WAIT_A2': await save_question(update, context, text)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
    
