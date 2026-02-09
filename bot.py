import logging
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from supabase import create_client, Client

# --- إعدادات ياسر ---
SUPABASE_URL = "https://snlcbtgzdxsacwjipggn.supabase.co"
SUPABASE_KEY = "sb_publishable_6ZSOF45eZxKKnreEKGgj5Q_sLbpmiLQ"
TELEGRAM_TOKEN = "7948017595:AAFw-ILthgp8F9IopGIqCXlwsqXBRDy4UPY"
OWNER_ID = 7988144062
DEVELOPER_CHAT = "https://t.me/Ya_79k"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- معالجة النصوص والتحكم المتطور ---
async def handle_text_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    state = context.user_data.get('state')

    # فتح التحكم لياسر فقط
    if text == "تحكم" and user_id == OWNER_ID:
        context.user_data.clear()
        keyboard = [[InlineKeyboardButton("➕ إضافة قسم", callback_data="gui_add_cat"),
                     InlineKeyboardButton("📚 إدارة الأقسام", callback_data="gui_view_cats")]]
        await update.message.reply_text("⚙️ لوحة التحكم الرئيسية:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # 1. إضافة قسم
    if state == 'WAIT_CAT_NAME':
        supabase.table("categories").insert({"name": text}).execute()
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم إضافة قسم: {text}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]))

    # 2. إضافة سؤال وجواب (نظام ياسر الذكي)
    elif state and state.startswith('WAIT_Q_TEXT_'):
        cat_id = state.split('_')[3]
        context.user_data['temp_q'] = text
        context.user_data['state'] = f'WAIT_Q_ANS_{cat_id}'
        await update.message.reply_text(f"✅ السؤال: {text}\n\nارسل الآن **الإجابة الصحيحة**:")

    elif state and state.startswith('WAIT_Q_ANS_'):
        cat_id = state.split('_')[3]
        if 'temp_ans' not in context.user_data: context.user_data['temp_ans'] = []
        context.user_data['temp_ans'].append(text)
        keyboard = [[InlineKeyboardButton("✅ نعم", callback_data=f"add_more_ans_{cat_id}"),
                     InlineKeyboardButton("❌ لا", callback_data=f"finish_q_{cat_id}")]]
        await update.message.reply_text(f"✅ أضفت: {text}\nهل تريد إضافة إجابة أخرى؟", reply_markup=InlineKeyboardMarkup(keyboard))

    # 3. تعديل السؤال/الجواب
    elif state and state.startswith('EDIT_STEP_'):
        mode, q_id, cat_id = state.split('_')[2], state.split('_')[3], state.split('_')[4]
        col = "question_content" if mode == "Q" else "correct_answer"
        supabase.table("questions").update({col: text}).eq("id", q_id).execute()
        context.user_data['state'] = None
        await update.message.reply_text("✅ تم التعديل!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مراجعة", callback_data=f"review_q_{q_id}_{cat_id}")]]))

# --- معالج الأزرار ولوحة الإحصائيات ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # اللوحة الخماسية بعد إضافة السؤال
    if data.startswith("finish_q_") or data.startswith("review_q_"):
        parts = data.split("_")
        if data.startswith("finish_q_"):
            cat_id = parts[2]
            q_text, ans_list = context.user_data.get('temp_q'), "|".join(context.user_data.get('temp_ans', []))
            res = supabase.table("questions").insert({"category_id": int(cat_id), "question_content": q_text, "correct_answer": ans_list, "timer": 20}).execute()
            q_id = res.data[0]['id']
        else:
            q_id, cat_id = parts[2], parts[3]
            res = supabase.table("questions").select("*").eq("id", q_id).single().execute()
            q_text, ans_list = res.data['question_content'], res.data['correct_answer']

        msg = f"📝 **مراجعة السؤال:**\n\n❓: {q_text}\n✅: {ans_list.replace('|', ' - ')}"
        keyboard = [
            [InlineKeyboardButton("1️⃣ تعديل السؤال", callback_data=f"edit_q_{q_id}_{cat_id}"),
             InlineKeyboardButton("2️⃣ تعديل الإجابة", callback_data=f"edit_a_{q_id}_{cat_id}")],
            [InlineKeyboardButton("3️⃣ حذف السؤال", callback_data=f"del_q_{q_id}_{cat_id}"),
             InlineKeyboardButton("4️⃣ إضافة سؤال جديد", callback_data=f"add_q_{cat_id}")],
            [InlineKeyboardButton("5️⃣ رجوع للقسم", callback_data=f"manage_cat_{cat_id}")]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data.startswith("add_more_ans_"):
        context.user_data['state'] = f"WAIT_Q_ANS_{data.split('_')[3]}"
        await query.message.reply_text("ارسل الإجابة الإضافية:")

    elif data.startswith("edit_q_") or data.startswith("edit_a_"):
        parts = data.split("_")
        context.user_data['state'] = f"EDIT_STEP_{parts[1].upper()}_{parts[2]}_{parts[3]}"
        await query.message.reply_text(f"ارسل النص الجديد:")

    elif data.startswith("manage_cat_"):
        cat_id = data.split("_")[2]
        keyboard = [[InlineKeyboardButton("➕ إضافة سؤال", callback_data=f"add_q_{cat_id}")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="gui_view_cats")]]
        await query.edit_message_text(f"📂 إدارة القسم", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "gui_view_cats":
        res = supabase.table("categories").select("*").execute()
        keyboard = [[InlineKeyboardButton(c['name'], callback_data=f"manage_cat_{c['id']}")] for c in res.data]
        keyboard.append([InlineKeyboardButton("🔙 الرئيسية", callback_data="back_to_main")])
        await query.edit_message_text("📌 اختر القسم:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_to_main":
        keyboard = [[InlineKeyboardButton("➕ إضافة قسم", callback_data="gui_add_cat"), [InlineKeyboardButton("📚 إدارة الأقسام", callback_data="gui_view_cats")]]]
        await query.edit_message_text("⚙️ لوحة التحكم الرئيسية", reply_markup=InlineKeyboardMarkup(keyboard))

# --- تشغيل البوت ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_logic))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 البوت مكتمل وشغال يا ياسر!")
    app.run_polling()

if __name__ == "__main__": main()
        
