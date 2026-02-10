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

# --- الدوال المساعدة للواجهات ---

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 إضافة مخصصة", callback_data="gui_view_cats"), InlineKeyboardButton("📅 جلسة سابقة", callback_data="dev")],
        [InlineKeyboardButton("🛒 سوق", callback_data="dev"), InlineKeyboardButton("🏆 تهيئة مسابقة", callback_data="setup_quiz")],
        [InlineKeyboardButton("📊 لوحة الصدارة", callback_data="leaderboard"), InlineKeyboardButton("🛑 إغلاق", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(settings):
    # خيارات الوقت المتاحة
    time_labels = {20: "20 ثانية", 30: "30 ثانية", 60: "دقيقة"}
    
    keyboard = [
        [InlineKeyboardButton(f"📊 الأسئلة: {settings['num_questions']}", callback_data="none"),
         InlineKeyboardButton(f"⏳ الوقت: {time_labels.get(settings['q_time'], '30 ثانية')}", callback_data="none")],
        
        [InlineKeyboardButton(f"✅ {n}" if settings['num_questions'] == n else str(n), callback_data=f"set_num_{n}") for n in [20, 30, 40, 50]],
        
        [InlineKeyboardButton(f"⏱️ {time_labels[t]}" if settings['q_time'] == t else time_labels[t], callback_data=f"set_time_{t}") for t in [20, 30, 60]],
        
        [InlineKeyboardButton(f"🚀 نمط: {settings['timing_mode']}", callback_data="toggle_timing"),
         InlineKeyboardButton(f"👥 المنافسة: {settings['comp_type']}", callback_data="toggle_comp")],
        
        [InlineKeyboardButton("✅ مباشرة" if settings['ans_type'] == 'مباشرة' else "مباشرة", callback_data="ans_direct"),
         InlineKeyboardButton("✅ خيارات" if settings['ans_type'] == 'خيارات' else "خيارات", callback_data="ans_opt")],
        
        [InlineKeyboardButton("💾 حفظ المسابقة الآن ✅", callback_data="save_quiz_final")],
        [InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="quiz_select_flow")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_question_interface(q_num, total, cat, mode, q_id, owner, text, q_time):
    # التنسيق الجديد بناءً على الصورة 9
    return (
        f"🎓 **الـمنـظـم:** {owner} ☁️\n"
        f"┏━━━━━━━━━━━━━━┓\n"
        f"  📌 **سؤال:** « {q_num} » من « {total} » 📍\n"
        f"  📁 **قسم:** {cat} 📂\n"
        f"  🎯 **النقاط:** 1 🎯\n"
        f"  🚀 **سرعة:** {mode} 🚀\n"
        f"  ⏳ **المهلة:** {q_time} ثانية ⏳\n"
        f"  🆔 **الآيدي:** {q_id} 🆔\n"
        f"┗━━━━━━━━━━━━━━┛\n\n"
        f"❓ **السؤال:**\n**{text}**"
    )

# --- نظام النقاط والتايب ---

async def update_stats(user_id, user_name, chat_id, chat_title, is_general):
    try:
        u_res = supabase.table("user_stats").select("*").eq("user_id", user_id).execute()
        if u_res.data:
            supabase.table("user_stats").update({"total_points": u_res.data[0]['total_points'] + 1, "name": user_name}).eq("user_id", user_id).execute()
        else:
            supabase.table("user_stats").insert({"user_id": user_id, "name": user_name, "total_points": 1}).execute()
        
        if is_general:
            g_res = supabase.table("group_stats").select("*").eq("chat_id", chat_id).execute()
            if g_res.data:
                supabase.table("group_stats").update({"total_points": g_res.data[0]['total_points'] + 1, "title": chat_title}).eq("chat_id", chat_id).execute()
            else:
                supabase.table("group_stats").insert({"chat_id": chat_id, "title": chat_title, "total_points": 1}).execute()
    except: pass

# --- المعالجات ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_link = "https://t.me/Ya_79k"
    welcome_text = (
        f"👋 **أهلاً بك يا {update.effective_user.first_name} في بوت المسابقات المطور!**\n\n"
        "📖 **كيفية التشغيل:**\n"
        "• أرسل كلمة (**تحكم**) لإدارة أقسامك وإضافة أسئلتك بخصوصية.\n"
        "• بعد إضافة الأسئلة، يمكنك تهيئة مسابقة وحفظها.\n\n"
        f"👑 **المطور:** [ياسر]({telegram_link})"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode='Markdown', disable_web_page_preview=True)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # استجابة فورية
    data, user_id = query.data, update.effective_user.id
    
    # تهيئة أولية لبيانات الإعدادات
    if 'temp_setup' not in context.user_data or context.user_data['temp_setup'] is None:
        context.user_data['temp_setup'] = {'num_questions': 20, 'q_time': 30, 'timing_mode': 'السرعة', 'comp_type': 'خاصة', 'ans_type': 'مباشرة', 'selected_cats': []}

    try:
        # إدارة الأقسام
        if data == "gui_view_cats":
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
            keyboard.append([InlineKeyboardButton("🔙 للرجوع", callback_data="back_to_main")])
            await query.edit_message_text("📂 أقسامك الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("manage_cat_"):
            cat_id = int(data.split("_")[2])
            context.user_data['current_cat_id'] = cat_id
            keyboard = [
                [InlineKeyboardButton("➕ إضافة سؤال", callback_data="gui_add_q"), InlineKeyboardButton("🗑️ حذف القسم", callback_data="dev")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]
            ]
            await query.edit_message_text(f"⚙️ إدارة القسم:\nأضف أسئلتك الآن لهذا القسم.", reply_markup=InlineKeyboardMarkup(keyboard))

        # --- تصفير البيانات عند البدء بمسابقة جديدة ---
        elif data == "setup_quiz":
            context.user_data['temp_setup'] = {'num_questions': 20, 'q_time': 30, 'timing_mode': 'السرعة', 'comp_type': 'خاصة', 'ans_type': 'مباشرة', 'selected_cats': []}
            keyboard = [[InlineKeyboardButton("⭐ أقسامك الخاصة", callback_data="quiz_select_flow")], 
                        [InlineKeyboardButton("⚙️ الإعدادات الفنية", callback_data="go_to_settings")],
                        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
            await query.edit_message_text("🏆 **تهيئة مسابقة جديدة (بيانات فارغة):**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        elif data == "quiz_select_flow":
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            selected = context.user_data['temp_setup']['selected_cats']
            keyboard = []
            for c in res.data:
                mark = "✅" if c['id'] in selected else "📁"
                keyboard.append([InlineKeyboardButton(f"{mark} {c['name']}", callback_data=f"tgl_cat_{c['id']}")])
            keyboard.append([InlineKeyboardButton("✅ حفظ ومتابعة", callback_data="go_to_settings")])
            await query.edit_message_text("📂 اختر الأقسام لهذه المسابقة فقط:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("tgl_cat_"):
            cat_id = int(data.split("_")[2])
            selected = context.user_data['temp_setup']['selected_cats']
            if cat_id in selected: selected.remove(cat_id)
            else: selected.append(cat_id)
            # تحديث الأزرار فقط لسرعة استجابة صاروخية
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            kb = []
            for c in res.data:
                mark = "✅" if c['id'] in selected else "📁"
                kb.append([InlineKeyboardButton(f"{mark} {c['name']}", callback_data=f"tgl_cat_{c['id']}")])
            kb.append([InlineKeyboardButton("✅ حفظ ومتابعة", callback_data="go_to_settings")])
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

        elif data == "go_to_settings":
            await query.edit_message_text("⚙️ **إعدادات المسابقة:**", reply_markup=get_settings_keyboard(context.user_data['temp_setup']), parse_mode='Markdown')

        elif data.startswith("set_num_") or data.startswith("set_time_") or data in ["toggle_timing", "toggle_comp", "ans_direct", "ans_opt"]:
            s = context.user_data['temp_setup']
            if "set_num_" in data: s['num_questions'] = int(data.split("_")[2])
            elif "set_time_" in data: s['q_time'] = int(data.split("_")[3])
            elif data == "toggle_timing": s['timing_mode'] = "الوقت" if s['timing_mode'] == "السرعة" else "السرعة"
            elif data == "toggle_comp": s['comp_type'] = "عامة" if s['comp_type'] == "خاصة" else "خاصة"
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(s))

        elif data == "save_quiz_final":
            context.user_data['state'] = 'WAIT_QUIZ_NAME'
            await query.edit_message_text("📝 **تسمية المسابقة:**\nأرسل اسماً لاعتماده:")

        elif data.startswith("run_quiz_"):
            qid = int(data.split("_")[2])
            qz = supabase.table("active_quizzes").select("*, quiz_settings(*)").eq("id", qid).single().execute().data
            cats = qz['quiz_settings']['selected_categories']
            qs = supabase.table("questions").select("*, categories(name)").in_("category_id", cats).limit(qz['quiz_settings']['num_questions']).execute().data
            if not qs:
                await query.message.reply_text("❌ لا توجد أسئلة في الأقسام المختارة.")
                return
            random.shuffle(qs)
            # إضافة q_time للعبة النشطة
            context.chat_data['active_game'] = {
                'questions': qs, 'current_idx': 0, 'scores': {}, 
                'settings': qz['quiz_settings'], 'owner': update.effective_user.first_name, 
                'answered': False, 'q_time': qz['quiz_settings'].get('q_time', 30)
            }
            await run_next_question(query.message.chat_id, context)

    except Exception as e: logging.error(f"Error: {e}")

async def run_next_question(chat_id, context):
    game = context.chat_data['active_game']
    if game['current_idx'] >= len(game['questions']):
        res = "🏆 **النتائج النهائية للمسابقة:**\n" + "\n".join([f"👤 {n} ⇇ {s}" for n, s in sorted(game['scores'].items(), key=lambda x: x[1], reverse=True)])
        await context.bot.send_message(chat_id, res)
        del context.chat_data['active_game']
        return
    
    q = game['questions'][game['current_idx']]
    game['answered'] = False
    ui = get_question_interface(game['current_idx']+1, len(game['questions']), q['categories']['name'], game['settings']['timing_mode'], q['id'], game['owner'], q['question_content'], game['q_time'])
    await context.bot.send_message(chat_id, ui, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, user_id = update.message.text.strip(), update.effective_user.id
    state = context.user_data.get('state')

    if 'active_game' in context.chat_data:
        game = context.chat_data['active_game']
        if text == game['questions'][game['current_idx']]['correct_answer'] and not game['answered']:
            game['answered'] = True
            name = update.effective_user.first_name
            game['scores'][name] = game['scores'].get(name, 0) + 1
            await update_stats(user_id, name, update.effective_chat.id, update.effective_chat.title, game['settings']['competition_type'] == 'عامة')
            await update.message.reply_text(f"✅ إجابة صحيحة يا {name}!")
            game['current_idx'] += 1
            await asyncio.sleep(2)
            await run_next_question(update.effective_chat.id, context)
        return

    if text == "تحكم":
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())
    elif text in ["مسابقة", "/مسابقة"]:
        res = supabase.table("active_quizzes").select("*").eq("created_by", user_id).execute()
        if res.data:
            kb = [[InlineKeyboardButton(f"🔹 {q['quiz_name']}", callback_data=f"run_quiz_{q['id']}")] for q in res.data]
            await update.message.reply_text("✨ اختر مسابقة للتشغيل:", reply_markup=InlineKeyboardMarkup(kb))

    elif state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text, "created_by": user_id}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم إضافة القسم '{text}'.")
    
    elif state == 'WAIT_Q_TEXT':
        context.user_data['t_q'] = text
        context.user_data['state'] = 'WAIT_Q_ANS'
        await update.message.reply_text("✅ تمام، الآن أرسل الإجابة الصحيحة:")
        
    elif state == 'WAIT_Q_ANS':
        supabase.table("questions").insert({"category_id": context.user_data['current_cat_id'], "question_content": context.user_data['t_q'], "correct_answer": text, "created_by": user_id}).execute()
        context.user_data['state'] = None
        await update.message.reply_text("🚀 تم حفظ السؤال بنجاح!")

    elif state == 'WAIT_QUIZ_NAME':
        s = context.user_data['temp_setup']
        r = supabase.table("quiz_settings").insert({
            "user_id": user_id, "num_questions": s['num_questions'], 
            "timing_mode": s['timing_mode'], "answer_type": s['ans_type'], 
            "competition_type": s['comp_type'], "selected_categories": s['selected_cats'],
            "q_time": s['q_time'] # حفظ وقت السؤال
        }).execute()
        supabase.table("active_quizzes").insert({"quiz_name": text, "settings_id": r.data[0]['id'], "created_by": user_id}).execute()
        context.user_data['state'] = None
        # تصفير بعد الحفظ
        context.user_data['temp_setup'] = None
        await update.message.reply_text(f"✅ تم حفظ مسابقة '{text}' بنجاح! ارسل 'مسابقة' للبدء.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
    
