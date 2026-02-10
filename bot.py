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
        [InlineKeyboardButton(f"📊 عدد الأسئلة الحالي: {settings['num_questions']}", callback_data="none")],
        [InlineKeyboardButton(f"✅ {n}" if settings['num_questions'] == n else str(n), callback_data=f"set_num_{n}") for n in [20, 25, 30, 35, 40, 45]],
        [
            InlineKeyboardButton(f"🚀 السرعة" if settings['timing_mode'] == 'السرعة' else "🕒 الوقت", callback_data="toggle_timing"),
            InlineKeyboardButton(f"المنافسة: {settings['comp_type']}", callback_data="toggle_comp")
        ],
        [
            InlineKeyboardButton(f"● مباشرة" if settings['ans_type'] == 'مباشرة' else "○ مباشرة", callback_data="ans_direct"),
            InlineKeyboardButton(f"● خيارات" if settings['ans_type'] == 'خيارات' else "○ خيارات", callback_data="ans_opt")
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

# 2. معالج الأزرار المطور (مع فصل الحفظ والرجوع)
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    if 'temp_setup' not in context.user_data:
        context.user_data['temp_setup'] = {'num_questions': 20, 'timing_mode': 'الوقت', 'comp_type': 'خاصة', 'ans_type': 'مباشرة', 'selected_cats': []}

    try:
        # --- نظام تهيئة المسابقة ---
        if data == "setup_quiz":
            keyboard = [
                [InlineKeyboardButton("👥 أقسام الأعضاء", callback_data="quiz_select_flow"), InlineKeyboardButton("🤖 أقسام البوت", callback_data="quiz_bot")],
                [InlineKeyboardButton("⭐ أقسامك الخاصة", callback_data="quiz_select_flow")], 
                [InlineKeyboardButton("⚙️ الإعدادات الفنية", callback_data="go_to_settings")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
            ]
            await query.edit_message_text("🏆 **تهيئة المسابقة:**\nاختر الأقسام التي تود تفعيلها ثم اضبط الإعدادات:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        elif data == "quiz_select_flow":
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            selected = context.user_data['temp_setup']['selected_cats']
            keyboard = []
            for c in res.data:
                mark = "✅" if c['id'] in selected else "📁"
                keyboard.append([InlineKeyboardButton(f"{mark} {c['name']}", callback_data=f"tgl_cat_{c['id']}")])
            
            # [الإصلاح]: فصل زر الحفظ عن الرجوع
            keyboard.append([
                InlineKeyboardButton("✅ حفظ ومتابعة", callback_data="go_to_settings"),
                InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz")
            ])
            await query.edit_message_text("📂 اختر الأقسام للمسابقة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("tgl_cat_"):
            cat_id = int(data.split("_")[2])
            selected = context.user_data['temp_setup']['selected_cats']
            if cat_id in selected: selected.remove(cat_id)
            else: selected.append(cat_id)
            
            # تحديث الواجهة للبقاء في نفس القائمة حتى الضغط على حفظ
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            keyboard = []
            for c in res.data:
                mark = "✅" if c['id'] in selected else "📁"
                keyboard.append([InlineKeyboardButton(f"{mark} {c['name']}", callback_data=f"tgl_cat_{c['id']}")])
            keyboard.append([
                InlineKeyboardButton("✅ حفظ ومتابعة", callback_data="go_to_settings"),
                InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz")
            ])
            await query.edit_message_text("📂 اختر الأقسام للمسابقة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "go_to_settings":
            # هذه هي الشاشة المماثلة للصورة الثالثة
            await query.edit_message_text("⚙️ الإعدادات الفنية للمسابقة:", reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

        # --- باقي أوامر الإعدادات الفنية ---
        elif data == "toggle_timing":
            s = context.user_data['temp_setup']
            s['timing_mode'] = "السرعة" if s['timing_mode'] == "الوقت" else "الوقت"
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(s))

        elif data == "ans_direct":
            context.user_data['temp_setup']['ans_type'] = "مباشرة"
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

        elif data == "ans_opt":
            context.user_data['temp_setup']['ans_type'] = "خيارات"
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

        elif data.startswith("set_num_"):
            context.user_data['temp_setup']['num_questions'] = int(data.split("_")[2])
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

        # --- أوامر الإدارة العامة والأسئلة ---
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
        elif data == "save_quiz_final":
            context.user_data['state'] = 'WAIT_QUIZ_NAME'
            await query.edit_message_text("📝 ممتاز! الآن ارسل (اسم المسابقة) لاعتمادها:")
            
        elif data.startswith("conf_del_"):
            cat_id = data.split("_")[2]
            keyboard = [[InlineKeyboardButton("✅ نعم، احذف", callback_data=f"execute_del_{cat_id}"), InlineKeyboardButton("❌ لا، تراجع", callback_data=f"manage_cat_{cat_id}")]]
            await query.edit_message_text("⚠️ هل أنت متأكد من حذف القسم نهائياً؟", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("execute_del_"):
            cat_id = data.split("_")[2]
            supabase.table("categories").delete().eq("id", cat_id).execute()
            await query.edit_message_text("✅ تم حذف القسم بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="gui_view_cats")]]))

    except Exception as e: logging.error(f"Callback Error: {e}")

# 3. معالج النصوص
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, user_id = update.message.text.strip(), update.effective_user.id
    state = context.user_data.get('state')

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        return

    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text, "created_by": user_id}).execute()
        context.user_data['state'] = None
        res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
        keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
        keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
        await update.message.reply_text(f"✅ تم إضافة القسم '{text}' بنجاح!", reply_markup=InlineKeyboardMarkup(keyboard))

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

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
        
