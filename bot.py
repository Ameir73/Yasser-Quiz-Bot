import logging
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("📊 لوحة الصدارة", callback_data="leaderboard"), InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(settings):
    time_labels = {20: "20 ثانية", 30: "30 ثانية", 60: "دقيقة"}
    keyboard = [
        [InlineKeyboardButton(f"📊 الأسئلة: {settings['num_questions']}", callback_data="none"),
         InlineKeyboardButton(f"⏳ الوقت: {time_labels.get(settings['q_time'], '30 ثانية')}", callback_data="none")],
        [InlineKeyboardButton(f"✅ {n}" if settings['num_questions'] == n else str(n), callback_data=f"set_num_{n}") for n in [20, 30, 40, 50]],
        [InlineKeyboardButton(f"⏱️ {time_labels[t]}" if settings['q_time'] == t else time_labels[t], callback_data=f"set_time_{t}") for t in [20, 30, 60]],
        [InlineKeyboardButton(f"🚀 نمط: {settings['timing_mode']}", callback_data="toggle_timing"),
         InlineKeyboardButton(f"👥 المنافسة: {settings['comp_type']}", callback_data="toggle_comp")],
        [InlineKeyboardButton("💾 حفظ المسابقة الآن ✅", callback_data="save_quiz_final")],
        [InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="quiz_select_flow")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_question_interface(q_num, total, cat, mode, q_id, owner, text, q_time):
    return (
        f"🎓 **الـمنـظـم:** {owner} ☁️\n"
        f"┏━━━━━━━━━━━━━━┓\n"
        f"  📌 **سؤال:** « {q_num} » من « {total} » 📍\n"
        f"  📁 **قسم:** {cat} 📂\n"
        f"  🚀 **سرعة:** {mode} 🚀\n"
        f"  ⏳ **المهلة:** {q_time} ثانية ⏳\n"
        f"┗━━━━━━━━━━━━━━┛\n\n"
        f"❓ **السؤال:**\n**{text}**"
    )

# --- المعالجات ---

async def run_next_question(chat_id, context):
    game = context.chat_data['active_game']
    if game['current_idx'] >= len(game['questions']):
        res = "🏆 **النتائج النهائية:**\n" + "\n".join([f"👤 {n}: {s}" for n, s in game['scores'].items()])
        await context.bot.send_message(chat_id, res)
        del context.chat_data['active_game']
        return
    
    q = game['questions'][game['current_idx']]
    game['answered'] = False
    ui = get_question_interface(game['current_idx']+1, len(game['questions']), q['categories']['name'], game['settings']['timing_mode'], q['id'], game['owner'], q['question_content'], game['q_time'])
    await context.bot.send_message(chat_id, ui, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = None
    await update.message.reply_text("👋 أهلاً بك! ارسل (تحكم) للإدارة.", reply_markup=get_main_menu())

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, update.effective_user.id
    
    if 'temp_setup' not in context.user_data or context.user_data['temp_setup'] is None:
        context.user_data['temp_setup'] = {'num_questions': 20, 'q_time': 30, 'timing_mode': 'السرعة', 'comp_type': 'خاصة', 'ans_type': 'مباشرة', 'selected_cats': []}

    if data == "setup_quiz":
        res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
        keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"tgl_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("✅ الخطوة التالية", callback_data="go_to_settings")])
        await query.edit_message_text("🏆 اختر الأقسام:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("run_quiz_"):
        qid = int(data.split("_")[2])
        qz = supabase.table("active_quizzes").select("*, quiz_settings(*)").eq("id", qid).single().execute().data
        cats = qz['quiz_settings']['selected_categories']
        qs = supabase.table("questions").select("*, categories(name)").in_("category_id", cats).limit(qz['quiz_settings']['num_questions']).execute().data
        if not qs:
            await query.message.reply_text("❌ لا توجد أسئلة في الأقسام المختارة.")
            return
        random.shuffle(qs)
        context.chat_data['active_game'] = {'questions': qs, 'current_idx': 0, 'scores': {}, 'settings': qz['quiz_settings'], 'owner': update.effective_user.first_name, 'answered': False, 'q_time': qz['quiz_settings'].get('q_time', 30)}
        await run_next_question(query.message.chat_id, context)

    # ... (بقية الشروط: set_num, set_time, save_quiz_final تستمر كما هي)
    elif data.startswith("set_time_"):
        context.user_data['temp_setup']['q_time'] = int(data.split("_")[2])
        await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))
    elif data == "go_to_settings":
        await query.edit_message_text("⚙️ الإعدادات:", reply_markup=get_settings_keyboard(context.user_data['temp_setup']))
    elif data == "save_quiz_final":
        context.user_data['state'] = 'WAIT_QUIZ_NAME'
        await query.edit_message_text("📝 اسم المسابقة؟")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, user_id = update.message.text.strip(), update.effective_user.id
    
    if 'active_game' in context.chat_data:
        game = context.chat_data['active_game']
        if text == game['questions'][game['current_idx']]['correct_answer'] and not game['answered']:
            game['answered'] = True
            name = update.effective_user.first_name
            game['scores'][name] = game['scores'].get(name, 0) + 1
            await update.message.reply_text(f"✅ صح يا {name}!")
            game['current_idx'] += 1
            await asyncio.sleep(1)
            await run_next_question(update.effective_chat.id, context)
        return

    if text == "مسابقة":
        res = supabase.table("active_quizzes").select("*").eq("created_by", user_id).execute()
        if res.data:
            kb = [[InlineKeyboardButton(f"🔹 {q['quiz_name']}", callback_data=f"run_quiz_{q['id']}")] for q in res.data]
            await update.message.reply_text("✨ اختر لتشغيل المسابقة:", reply_markup=InlineKeyboardMarkup(kb))

    elif context.user_data.get('state') == 'WAIT_QUIZ_NAME':
        # (كود الحفظ هنا)
        pass

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
    
