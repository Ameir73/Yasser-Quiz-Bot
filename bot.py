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
    # واجهة الإعدادات الفنية المحدثة (تحديث ديناميكي كما في الصورة 1)
    keyboard = [
        [InlineKeyboardButton(f"📊 عدد الأسئلة الحالي: {settings['num_questions']}", callback_data="none")],
        [InlineKeyboardButton(f"✅ {n}" if settings['num_questions'] == n else str(n), callback_data=f"set_num_{n}") for n in [20, 30, 40, 50]],
        [
            InlineKeyboardButton(f"🚀 نمط: {settings['timing_mode']}", callback_data="toggle_timing"),
            InlineKeyboardButton(f"المنافسة: {settings['comp_type']}", callback_data="toggle_comp")
        ],
        [
            InlineKeyboardButton("✅ مباشرة" if settings['ans_type'] == 'مباشرة' else "مباشرة", callback_data="ans_direct"),
            InlineKeyboardButton("✅ خيارات" if settings['ans_type'] == 'خيارات' else "خيارات", callback_data="ans_opt")
        ],
        [InlineKeyboardButton("💾 حفظ المسابقة الآن", callback_data="save_quiz_final")],
        [InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="quiz_select_flow")]
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

# 2. معالج الأزرار المطور
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    if 'temp_setup' not in context.user_data:
        context.user_data['temp_setup'] = {'num_questions': 20, 'timing_mode': 'السرعة', 'comp_type': 'خاصة', 'ans_type': 'مباشرة', 'selected_cats': []}

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
            
            # تحديث الواجهة فوراً للبقاء في القائمة
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            keyboard = [[InlineKeyboardButton(f"{'✅' if c['id'] in selected else '📁'} {c['name']}", callback_data=f"tgl_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("✅ حفظ ومتابعة", callback_data="go_to_settings"), InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz")])
            await query.edit_message_text("📂 اختر الأقسام للمسابقة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "go_to_settings":
            await query.edit_message_text("⚙️ **إعدادات المسابقة:**\nاضبط الخصائص الفنية لمسابقتك:", reply_markup=get_settings_keyboard(context.user_data['temp_setup']), parse_mode='Markdown')

        # --- تحديث الإعدادات ديناميكياً (الصورة 1) ---
        elif data.startswith("set_num_") or data == "toggle_timing" or data.startswith("ans_") or data == "toggle_comp":
            s = context.user_data['temp_setup']
            if "set_num_" in data: s['num_questions'] = int(data.split("_")[2])
            elif data == "toggle_timing": s['timing_mode'] = "الوقت" if s['timing_mode'] == "السرعة" else "السرعة"
            elif data == "ans_direct": s['ans_type'] = "مباشرة"
            elif data == "ans_opt": s['ans_type'] = "خيارات"
            elif data == "toggle_comp": s['comp_type'] = "عامة" if s['comp_type'] == "خاصة" else "خاصة"
            
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(s))

        # --- أوامر الإدارة العامة ---
        elif data == "gui_view_cats":
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
            keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
            await query.edit_message_text("📂 أقسامك الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "gui_add_cat":
            context.user_data['state'] = 'WAIT_CAT_NAME'
            await query.edit_message_text("📝 ارسل اسم القسم الجديد:")

        elif data == "back_to_main": await query.edit_message_text("⚙️ الرئيسية:", reply_markup=get_main_menu())
        
        elif data == "save_quiz_final":
            context.user_data['state'] = 'WAIT_QUIZ_NAME'
            await query.edit_message_text("📝 **تسمية المسابقة:**\nارسل اسماً لهذه المسابقة لاعتمادها (مثلاً: مسابقة الأسبوع):", parse_mode='Markdown')

    except Exception as e: logging.error(f"Callback Error: {e}")

# 3. معالج النصوص
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, user_id = update.message.text.strip(), update.effective_user.id
    state = context.user_data.get('state')

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        return

    # تشغيل المسابقة عند كتابة "مسابقة" (الصورة 3)
    if text == "مسابقة" or text == "/مسابقة":
        res = supabase.table("active_quizzes").select("*").eq("created_by", user_id).execute()
        if not res.data:
            await update.message.reply_text("⚠️ لا توجد مسابقات محفوظة لديك.")
            return
        keyboard = [[InlineKeyboardButton(f"🔹 {q['quiz_name']}", callback_data=f"run_quiz_{q['id']}")] for q in res.data]
        await update.message.reply_text("✨ **اختر مسابقة لتشغيلها:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text, "created_by": user_id}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم إضافة القسم '{text}' بنجاح!")

    elif state == 'WAIT_QUIZ_NAME':
        s = context.user_data['temp_setup']
        # حفظ الإعدادات وربطها بالمسابقة (الصورة 2)
        res_set = supabase.table("quiz_settings").insert({
            "user_id": user_id, "num_questions": s['num_questions'], "timing_mode": s['timing_mode'],
            "answer_type": s['ans_type'], "competition_type": s['comp_type']
        }).execute()
        s_id = res_set.data[0]['id']
        supabase.table("active_quizzes").insert({"quiz_name": text, "settings_id": s_id, "created_by": user_id}).execute()
        
        context.user_data['state'] = None
        instruction_text = (
            f"✅ **تم حفظ المسابقة '{text}' بنجاح!**\n\n"
            "يمكنك الآن بدء المسابقة في أي قروب عبر كتابة:\n"
            "👉 `مسابقة`"
        )
        await update.message.reply_text(instruction_text, reply_markup=get_main_menu(), parse_mode='Markdown')

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
            
