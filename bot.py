import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client, handle_file
import edge_tts

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Koyeb Health Check Handler
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is Running Healthy!")

def run_web():
    server = HTTPServer(('0.0.0.0', 8000), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "फोटो भेजिए और कैप्शन में डायलॉग लिखें:\n\n"
        "Girl: अरे बत्तख भाई, तुम्हारा चश्मा तो बहुत मस्त है!\n"
        "Duck: क्वैक क्वैक! मैं बहुत कूल हूँ!"
    )

async def generate_speech(text, voice_role):
    # Girl के लिए क्यूट हिंदी आवाज (Swara), Duck के लिए थोड़ी तेज पिच वाली फनी आवाज
    if voice_role == "girl":
        voice = "hi-IN-SwaraNeural"
        pitch = "+15Hz"
        rate = "+5%"
    else:
        voice = "hi-IN-MadhurNeural"
        pitch = "+35Hz"
        rate = "+15%"
        
    output_path = f"{voice_role}_audio.mp3"
    communicate = edge_tts.Communicate(text, voice, pitch=pitch, rate=rate)
    await communicate.save(output_path)
    return output_path

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.photo or not msg.caption:
        await msg.reply_text("कृपया फोटो और कैप्शन दोनों भेजें!")
        return

    caption = msg.caption.strip()
    girl_line = ""
    duck_line = ""

    for line in caption.split("\n"):
        if line.lower().startswith("girl:"):
            girl_line = line.split(":", 1)[1].strip()
        elif line.lower().startswith("duck:"):
            duck_line = line.split(":", 1)[1].strip()

    if not girl_line and not duck_line:
        # अगर सिर्फ सादा टेक्स्ट भेजा हो तो उसे Girl का डायलॉग मान लेंगे
        girl_line = caption

    status = await msg.reply_text("1/3: आवाज तैयार हो रही है...")
    photo_file = await msg.photo[-1].get_file()
    img_path = "input_char.jpg"
    await photo_file.download_to_drive(img_path)

    try:
        # 1. फ्री और फास्ट वॉइस जेनरेशन (कोई HuggingFace एरर नहीं)
        if girl_line:
            audio_path = await generate_speech(girl_line, "girl")
        else:
            audio_path = await generate_speech(duck_line, "duck")

        await status.edit_text("2/3: वीडियो रेंडर हो रहा है (SadTalker)...")

        # 2. लिप-सिंक
        anim_client = Client("vinthony/SadTalker")
        video_res = anim_client.predict(
            source_image=handle_file(img_path),
            driven_audio=handle_file(audio_path),
            fn_index=0
        )
        video_path = video_res['video'] if isinstance(video_res, dict) else video_res

        await status.edit_text("3/3: वीडियो भेजा जा रहा है...")
        await msg.reply_video(video=open(video_path, 'rb'))

    except Exception as e:
        await msg.reply_text(f"एरर: {str(e)}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()

    if BOT_TOKEN:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), process_video))
        app.run_polling()
        
