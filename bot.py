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

# --- المعالجات ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = None # تصفير الحالة عند البدء
    welcome_text = (
        f"👋 **أهلاً بك يا {update.effective_user.first_name}!**\n\n"
        "أرسل كلمة (**تحكم**) للإدارة أو (**مسابقة**) للبدء."
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode='Markdown')

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, update.effective_user.id
    
    if 'temp_setup' not in context.user_data or context.user_data['temp_setup'] is None:
        context.user_data['temp_setup'] = {'num_questions': 20, 'q_time': 30, 'timing_mode': 'السرعة', 'comp_type': 'خاصة', 'ans_type': 'مباشرة', 'selected_cats': []}

    try:
        if data == "gui_view_cats":
            context.user_data['state'] = None
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"manage_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="gui_add_cat")])
            await query.edit_message_text("📂 أقسامك الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("manage_cat_"):
            cat_id = int(data.split("_")[2])
            context.user_data['current_cat_id'] = cat_id
            keyboard = [[InlineKeyboardButton("➕ إضافة سؤال", callback_data="gui_add_q")], [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]
            await query.edit_message_text(f"⚙️ إدارة القسم:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "gui_add_cat":
            context.user_data['state'] = 'WAIT_CAT_NAME'
            await query.edit_message_text("📝 أرسل اسم القسم الجديد:")

        elif data == "gui_add_q":
            context.user_data['state'] = 'WAIT_Q_TEXT' # تأكدنا أنها user_data وليس user_id
            await query.edit_message_text("❓ أرسل نص السؤال الآن:")

        elif data == "setup_quiz":
            context.user_data['temp_setup']['selected_cats'] = []
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            keyboard = [[InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"tgl_cat_{c['id']}")] for c in res.data]
            keyboard.append([InlineKeyboardButton("✅ الخطوة التالية", callback_data="go_to_settings")])
            await query.edit_message_text("🏆 اختر الأقسام للمسابقة:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("tgl_cat_"):
            cat_id = int(data.split("_")[2])
            selected = context.user_data['temp_setup']['selected_cats']
            if cat_id in selected: selected.remove(cat_id)
            else: selected.append(cat_id)
            
            res = supabase.table("categories").select("*").eq("created_by", user_id).execute()
            kb = [[InlineKeyboardButton(f"{'✅' if c['id'] in selected else '📁'} {c['name']}", callback_data=f"tgl_cat_{c['id']}")] for c in res.data]
            kb.append([InlineKeyboardButton("✅ الخطوة التالية", callback_data="go_to_settings")])
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

        elif data == "go_to_settings":
            await query.edit_message_text("⚙️ إعدادات المسابقة:", reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

        elif data.startswith("set_num_"):
            context.user_data['temp_setup']['num_questions'] = int(data.split("_")[2])
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

        elif data.startswith("set_time_"):
            # إصلاح زر الوقت (استخدام الجزء الثالث بدلاً من الرابع)
            context.user_data['temp_setup']['q_time'] = int(data.split("_")[2])
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(context.user_data['temp_setup']))

        elif data == "save_quiz_final":
            context.user_data['state'] = 'WAIT_QUIZ_NAME'
            await query.edit_message_text("📝 أرسل اسماً للمسابقة الآن:")

    except Exception as e: logging.error(f"Error: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, user_id = update.message.text.strip(), update.effective_user.id
    state = context.user_data.get('state')

    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text, "created_by": user_id}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم إضافة القسم '{text}'.")
    
    elif state == 'WAIT_Q_TEXT':
        context.user_data['t_q'] = text
        context.user_data['state'] = 'WAIT_Q_ANS'
        await update.message.reply_text("✅ أرسل الإجابة الآن:")
        
    elif state == 'WAIT_Q_ANS':
        supabase.table("questions").insert({"category_id": context.user_data['current_cat_id'], "question_content": context.user_data['t_q'], "correct_answer": text, "created_by": user_id}).execute()
        context.user_data['state'] = None
        await update.message.reply_text("🚀 تم حفظ السؤال!")

    elif state == 'WAIT_QUIZ_NAME':
        s = context.user_data['temp_setup']
        r = supabase.table("quiz_settings").insert({
            "user_id": user_id, "num_questions": s['num_questions'], "q_time": s['q_time'],
            "timing_mode": s['timing_mode'], "answer_type": s['ans_type'], 
            "competition_type": s['comp_type'], "selected_categories": s['selected_cats']
        }).execute()
        supabase.table("active_quizzes").insert({"quiz_name": text, "settings_id": r.data[0]['id'], "created_by": user_id}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم حفظ المسابقة '{text}'.")

    elif text == "تحكم":
        context.user_data['state'] = None
        await update.message.reply_text("⚙️ لوحة التحكم:", reply_markup=get_main_menu())

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__": main()
    
