import os
import asyncio
import time
from pyrogram import Client, filters, errors
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, FloodWait

# الإعدادات
API_ID = int(os.environ.get("API_ID", "12345"))
API_HASH = os.environ.get("API_HASH", "your_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

# بوت التحكم (Bot API)
bot = Client("ControlBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# متغيرات مؤقتة للجلسة
user_sessions = {} 

# دالة شريط التقدم (Progress Bar)
async def progress(current, total, message, start_time, action):
    now = time.time()
    diff = now - start_time
    if round(diff % 4) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        time_to_completion = round((total - current) / speed) if speed > 0 else 0
        
        progress_str = "[{0}{1}]".format(
            '●' * int(percentage / 10),
            '○' * (10 - int(percentage / 10))
        )
        
        tmp = f"{action}...\n\n{progress_str} {percentage:.2f}%\n" \
              f"المنجز: {current} / {total} بابت\n" \
              f"السرعة: {speed:.2f} B/s\n" \
              f"الوقت المتبقي: {time_to_completion} ثانية"
        
        try:
            await message.edit_text(tmp)
        except:
            pass

@bot.on_message(filters.command("start"))
async def start(client, message):
    welcome = f"مرحباً بك.. أنا بوت البحث الشامل الخاص بالمطور **هيثم محمود الجمال**.\n\n" \
              f"لتفعيل البحث الشامل، أرسل رقم هاتفك مع رمز الدولة (مثال: +967770000000)"
    await message.reply_text(welcome)

@bot.on_message(filters.text & filters.private)
async def handle_logic(client, message):
    chat_id = message.chat.id
    text = message.text

    # المرحلة 1: استقبال رقم الهاتف
    if text.startswith("+") and chat_id not in user_sessions:
        user_sessions[chat_id] = {"phone": text, "client": Client(":memory:", API_ID, API_HASH)}
        await user_sessions[chat_id]["client"].connect()
        try:
            code_info = await user_sessions[chat_id]["client"].send_code(text)
            user_sessions[chat_id]["hash"] = code_info.phone_code_hash
            await message.reply_text("تم إرسال كود التحقق إلى حسابك، يرجى إرساله هنا:")
        except Exception as e:
            await message.reply_text(f"خطأ: {e}")
        return

    # المرحلة 2: استقبال كود التحقق وتوليد الجلسة
    if chat_id in user_sessions and "hash" in user_sessions[chat_id] and "user_client" not in user_sessions[chat_id]:
        try:
            user_client = user_sessions[chat_id]["client"]
            await user_client.sign_in(user_sessions[chat_id]["phone"], user_sessions[chat_id]["hash"], text)
            
            # حفظ الجلسة في المتغير
            session_str = await user_client.export_session_string()
            user_sessions[chat_id]["user_client"] = user_client
            await message.reply_text(f"✅ تم تسجيل الدخول بنجاح!\nكود الجلسة الخاص بك (احفظه):\n`{session_str}`\n\nالآن أرسل اسم أي ملف للبحث عنه عالمياً.")
        except Exception as e:
            await message.reply_text(f"فشل التحقق: {e}")
        return

    # المرحلة 3: البحث الشامل (Global Search)
    if chat_id in user_sessions and "user_client" in user_sessions[chat_id]:
        query = text
        user_app = user_sessions[chat_id]["user_client"]
        waiting = await message.reply_text(f"جاري البحث عن **{query}** في تليجرام كامل... 🔍")
        
        count = 0
        async for msg in user_app.search_global(query, limit=15):
            if msg.document or msg.video or msg.audio:
                count += 1
                # جلب رابط الرسالة الأصلي
                link = f"https://t.me/c/{str(msg.chat.id)[4:]}/{msg.id}" if msg.chat.username is None else msg.link
                
                start_time = time.time()
                # إرسال الملف مع شريط التقدم
                file_msg = await message.reply_text(f"جاري جلب الملف رقم {count}...")
                
                try:
                    await msg.copy(
                        chat_id=message.chat.id,
                        caption=f"✅ تم العثور على الملف\n🔗 رابط المصدر: {link}\n\nبواسطة: هيثم الجمال",
                        progress=progress,
                        progress_args=(file_msg, start_time, "يتم الآن النقل")
                    )
                    await file_msg.delete()
                except Exception as e:
                    await file_msg.edit_text(f"تعذر إرسال هذا الملف: {e}")

        if count == 0:
            await waiting.edit_text("لم يتم العثور على نتائج.")
        else:
            await waiting.delete()

print("البوت يعمل الآن يا هيثم...")
bot.run()
