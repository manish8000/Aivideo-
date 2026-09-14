import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client

BOT_TOKEN = os.getenv("BOT_TOKEN")
VOICE_SAMPLE = "my_voice.mp3"  # आपकी आवाज की फाइल

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("भेजिए कैरेक्टर की फोटो और कैप्शन में वो डायलॉग जो बुलवाना है!")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.photo or not msg.caption:
        await msg.reply_text("कृपया फोटो के साथ डायलॉग (caption) लिखकर भेजें!")
        return

    status = await msg.reply_text("1/3: आवाज क्लोन हो रही है...")
    
    # 1. फोटो डाउनलोड
    photo_file = await msg.photo[-1].get_file()
    img_path = "input_char.jpg"
    await photo_file.download_to_drive(img_path)
    text_prompt = msg.caption

    try:
        # 2. फ्री वॉइस क्लोन (F5-TTS HuggingFace API)
        tts_client = Client("mrfakename/E2-F5-TTS")
        tts_res = tts_client.predict(
            ref_audio_input=VOICE_SAMPLE,
            ref_text_input="mera sample audio",
            gen_text_input=text_prompt,
            model="F5-TTS",
            api_name="/basic_tts"
        )
        audio_path = tts_res[0]

        await status.edit_text("2/3: कैरेक्टर का लिप-सिंक वीडियो बन रहा है...")

        # 3. फ्री लिप-सिंक (SadTalker Space)
        anim_client = Client("vinthony/SadTalker")
        video_res = anim_client.predict(
            source_image=img_path,
            driven_audio=audio_path,
            api_name="/predict"
        )
        video_path = video_res['video']

        await status.edit_text("3/3: वीडियो तैयार है, भेज रहा हूँ...")
        await msg.reply_video(video=open(video_path, 'rb'))

    except Exception as e:
        await msg.reply_text(f"एरर आया: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), process_video))
    app.run_polling()
  
