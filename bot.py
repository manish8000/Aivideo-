import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client

BOT_TOKEN = os.getenv("BOT_TOKEN")
VOICE_SAMPLE = "my_voice.mp3"

# Koyeb Health Check पास करने के लिए
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is Running Healthy!")

def run_web():
    server = HTTPServer(('0.0.0.0', 8000), HealthCheckHandler)
    server.serve_forever()

# टेलीग्राम बॉट लॉजिक
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("भेजिए कैरेक्टर की फोटो और डायलॉग!")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.photo or not msg.caption:
        await msg.reply_text("कृपया फोटो के साथ डायलॉग (caption) भेजें!")
        return

    status = await msg.reply_text("1/3: आवाज तैयार हो रही है...")
    photo_file = await msg.photo[-1].get_file()
    img_path = "input_char.jpg"
    await photo_file.download_to_drive(img_path)

    try:
        tts_client = Client("mrfakename/E2-F5-TTS")
        tts_res = tts_client.predict(
            ref_audio_input=VOICE_SAMPLE,
            ref_text_input="mera sample audio",
            gen_text_input=msg.caption,
            model="F5-TTS",
            api_name="/basic_tts"
        )
        audio_path = tts_res[0]

        await status.edit_text("2/3: वीडियो रेंडर हो रहा है...")
        anim_client = Client("vinthony/SadTalker")
        video_res = anim_client.predict(
            source_image=img_path,
            driven_audio=audio_path,
            api_name="/predict"
        )
        video_path = video_res['video']

        await status.edit_text("3/3: भेजा जा रहा है...")
        await msg.reply_video(video=open(video_path, 'rb'))

    except Exception as e:
        await msg.reply_text(f"एरर: {str(e)}")

if __name__ == "__main__":
    # पोर्ट 8000 को बैकग्राउंड में शुरू करना
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()

    # टेलीग्राम बॉट शुरू करना
    if BOT_TOKEN:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), process_video))
        app.run_polling()
        
