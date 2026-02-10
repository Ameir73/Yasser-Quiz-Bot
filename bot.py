import logging
import asyncio
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- الإعدادات الثابتة ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062 

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- الدوال المساعدة للوحات التحكم والجماليات ---

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("📊 لوحة الصدارة", callback_data="leaderboard"), InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(settings):
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
        [InlineKeyboardButton("💾 حفظ المسابقة الآن ✅", callback_data="save_quiz_final")],
        [InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="quiz_select_flow")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quiz_intro_text(quiz_name, settings, owner_name, cat_names):
    cats = "\n".join([f"    📍 {name}" for name in cat_names])
    return (
        f"💠 **مـسـابـقـة: {quiz_name}** 💠\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 **المنظم:** {owner_name}\n"
        f"⚖️ **المنافسة:** {settings['competition_type']}\n"
        f"🚀 **النمط:** {settings['timing_mode']}\n"
        f"🔢 **الأسئلة:** {settings['num_questions']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📂 **الأقسام المشاركة:**\n{cats}\n"
        f"━━━━━━━━━━━━━━\n"
        f"⏳ *تستعد المسابقة للانطلاق...*"
    )

def get_question_interface(q_num, total, cat, mode, q_id, owner, text):
    return (
        f"🎓 **الـمنـظـم:** {owner}\n"
        f"┏━━━━━━━━━━━━━━┓\n"
        f"  📌 **سؤال:** « {q_num} » من « {total} »\n"
        f"  📁 **قسم:** {cat}\n"
        f"  🚀 **سرعة:** {mode}\n"
        f"  🆔 **الآيدي:** {q_id}\n"
        f"┗━━━━━━━━━━━━━━┛\n\n"
        f"❓ **السؤال:**\n**{text}**"
    )

# --- نظام النقاط والتايب العالمي ---

async def update_stats(user_id, user_name, chat_id, chat_title, is_general):
    try:
        # تحديث نقاط العضو دائماً
        u_res = supabase.table("user_stats").select("*").eq("user_id", user_id).execute()
        if u_res.data:
            supabase.table("user_stats").update({"total_points": u_res.data[0]['total_points'] + 1, "name": user_name}).eq("user_id", user_id).execute()
        else:
            supabase.table("user_stats").insert({"user_id": user_id, "name": user_name, "total_points": 1}).execute()
        
        # إذا كانت المنافسة عامة نحدث المجموعات
        if is_general:
            g_res = supabase.table("group_stats").select("*").eq("chat_id", chat_id).execute()
            if g_res.data:
                supabase.table("group_stats").update({"total_points": g_res.data[0]['total_points'] + 1, "title": chat_title}).eq("chat_id", chat_id).execute()
            else:
                supabase.table("group_stats").insert({"chat_id": chat_id, "title": chat_title, "total_points": 1}).execute()
    except Exception as e: logging.error(f"Stats Error: {e}")

# --- معالجات الأحداث ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_link = "https://t.me/Ya_79k"
    welcome_text = (
        "👋 **أهلاً بك في بوت المسابقات المطور!**\n\n"
        "📖 **كيفية التشغيل:**\n"
        "• ارسل كلمة (**تحكم**) لإدارة أقسامك بخصوصية.\n\n"
        f"👑 **المطور:** [ياسر]({telegram_link})"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode='Markdown')

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, update.effective_user.id
    
    if 'temp_setup' not in context.user_data:
        context.user_data['temp_setup'] = {'num_questions': 20, 'timing_mode': 'السرعة', 'comp_type': 'خاصة', 'ans_type': 'مباشرة', 'selected_cats': []}

    try:
        if data == "setup_quiz":
            keyboard = [[InlineKeyboardButton("⭐ أقسامك الخاصة", callback_data="quiz_select_flow")], 
                        [InlineKeyboardButton("⚙️ الإعدادات الفنية", callback_data="go_to_settings")],
                        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
            await query.edit_message_text("🏆 **تهيئة المسابقة:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        elif data == "quiz_select_flow":
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            selected = context.user_data['temp_setup']['selected_cats']
            keyboard = [[InlineKeyboardButton(f"{'✅' if c['id'] in selected else '📁'} {c['name']}", callback_data=f"tgl_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("✅ حفظ ومتابعة", callback_data="go_to_settings"), InlineKeyboardButton("🔙 رجوع", callback_data="setup_quiz")])
            await query.edit_message_text("📂 اختر الأقسام للمسابقة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("tgl_cat_"):
            cat_id = int(data.split("_")[2])
            selected = context.user_data['temp_setup']['selected_cats']
            if cat_id in selected: selected.remove(cat_id)
            else: selected.append(cat_id)
            await callback_handler(update, context) # تحديث ديناميكي

        elif data == "go_to_settings":
            await query.edit_message_text("⚙️ **إعدادات المسابقة:**", reply_markup=get_settings_keyboard(context.user_data['temp_setup']), parse_mode='Markdown')

        elif data.startswith("set_num_") or data in ["toggle_timing", "toggle_comp", "ans_direct", "ans_opt"]:
            s = context.user_data['temp_setup']
            if "set_num_" in data: s['num_questions'] = int(data.split("_")[2])
            elif data == "toggle_timing": s['timing_mode'] = "الوقت" if s['timing_mode'] == "السرعة" else "السرعة"
            elif data == "toggle_comp": s['comp_type'] = "عامة" if s['comp_type'] == "خاصة" else "خاصة"
            elif data == "ans_direct": s['ans_type'] = "مباشرة"
            elif data == "ans_opt": s['ans_type'] = "خيارات"
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(s))

        elif data == "save_quiz_final":
            context.user_data['state'] = 'WAIT_QUIZ_NAME'
            await query.edit_message_text("📝 **تسمية المسابقة:**\nارسل اسماً لاعتماده:", parse_mode='Markdown')

        elif data == "leaderboard":
            users = supabase.table("user_stats").select("*").order("total_points", desc=True).limit(5).execute()
            text = "📊 **أذكياء البوت (أفراد):**\n" + "\n".join([f"🥇 {u['name']} ⇇ {u['total_points']}" for u in users.data])
            await query.edit_message_text(text, reply_markup=get_main_menu())

        elif data == "back_to_main":
            await query.edit_message_text("⚙️ الرئيسية:", reply_markup=get_main_menu())

        # --- تشغيل المسابقة ---
        elif data.startswith("run_quiz_"):
            quiz_id = int(data.split("_")[2])
            quiz_data = supabase.table("active_quizzes").select("*, quiz_settings(*)").eq("id", quiz_id).single().execute().data
            settings = quiz_data['quiz_settings']
            cat_ids = settings['selected_categories']
            
            # جلب الأسماء للأقسام
            cats_res = supabase.table("categories").select("name").in_("id", cat_ids).execute()
            cat_names = [c['name'] for c in cats_res.data]
            
            # إرسال واجهة الانطلاق
            intro = get_quiz_intro_text(quiz_data['quiz_name'], settings, update.effective_user.first_name, cat_names)
            await query.edit_message_text(intro, parse_mode='Markdown')
            await asyncio.sleep(3)
            
            # جلب الأسئلة
            qs = supabase.table("questions").select("*, categories(name)").in_("category_id", cat_ids).limit(settings['num_questions']).execute().data
            random.shuffle(qs)
            
            context.chat_data['active_game'] = {
                'questions': qs, 'current_idx': 0, 'scores': {}, 
                'settings': settings, 'owner': update.effective_user.first_name, 'answered': False
            }
            await run_next_question(query.message.chat_id, context)

    except Exception as e: logging.error(f"Callback Error: {e}")

async def run_next_question(chat_id, context):
    game = context.chat_data['active_game']
    if game['current_idx'] >= len(game['questions']):
        # عرض النتائج النهائية
        sorted_s = sorted(game['scores'].items(), key=lambda x: x[1], reverse=True)
        title = "🏆 النتائج النهائية للمسابقة"
        res_txt = f"{title}\n━━━━━━━━━━━━━━\n" + "\n".join([f"👤 {n} ⇇ {s} نقطة" for n, s in sorted_s])
        await context.bot.send_message(chat_id, res_txt)
        del context.chat_data['active_game']
        return

    q = game['questions'][game['current_idx']]
    game['answered'] = False
    ui = get_question_interface(game['current_idx']+1, len(game['questions']), q['categories']['name'], game['settings']['timing_mode'], q['id'], game['owner'], q['question_content'])
    await context.bot.send_message(chat_id, ui, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, user_id = update.message.text.strip(), update.effective_user.id
    state = context.user_data.get('state')

    # تصحيح الإجابات أثناء اللعب
    if 'active_game' in context.chat_data:
        game = context.chat_data['active_game']
        correct = game['questions'][game['current_idx']]['correct_answer']
        if text == correct and not game['answered']:
            game['answered'] = True
            user_name = update.effective_user.first_name
            game['scores'][user_name] = game['scores'].get(user_name, 0) + 1
            await update_stats(user_id, user_name, update.effective_chat.id, update.effective_chat.title, game['settings']['competition_type'] == 'عامة')
            await update.message.reply_text(f"✅ إجابة صحيحة يا {user_name}!")
            game['current_idx'] += 1
            await asyncio.sleep(2)
            await run_next_question(update.effective_chat.id, context)
        return

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
        return

    if text in ["مسابقة", "/مسابقة"]:
        res = supabase.table("active_quizzes").select("*").eq("created_by", user_id).execute()
        if res.data:
            keyboard = [[InlineKeyboardButton(f"🔹 {q['quiz_name']}", callback_data=f"run_quiz_{q['id']}")] for q in res.data]
            await update.message.reply_text("✨ **اختر مسابقة لتشغيلها:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    if state == 'WAIT_QUIZ_NAME':
        s = context.user_data['temp_setup']
        res_set = supabase.table("quiz_settings").insert({
            "user_id": user_id, "num_questions": s['num_questions'], "timing_mode": s['timing_mode'],
            "answer_type": s['ans_type'], "competition_type": s['comp_type'], "selected_categories": s['selected_cats']
        }).execute()
        supabase.table("active_quizzes").insert({"quiz_name": text, "settings_id": res_set.data[0]['id'], "created_by": user_id}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم حفظ المسابقة '{text}' بنجاح!\nارسل 'مسابقة' للتشغيل.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
