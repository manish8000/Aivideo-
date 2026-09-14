import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client, handle_file

BOT_TOKEN = os.getenv("BOT_TOKEN")
GIRL_VOICE = "my_voice.mp3"
DUCK_VOICE = "duck_voice.mp3"

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
        "फोटो भेजिए और कैप्शन में इस फॉर्मेट में लिखें:\n\n"
        "Girl: अरे बत्तख भाई, चश्मा कैसा लगा?\n"
        "Duck: क्वैक क्वैक! बहुत बढ़िया लगा!"
    )

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.photo or not msg.caption:
        await msg.reply_text("कृपया फोटो और डायलॉग दोनों भेजें!")
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
        await msg.reply_text("कृपया 'Girl:' और 'Duck:' लिखकर डायलॉग भेजें।")
        return

    status = await msg.reply_text("1/3: दोनों की आवाज़ तैयार हो रही है...")
    photo_file = await msg.photo[-1].get_file()
    img_path = "input_char.jpg"
    await photo_file.download_to_drive(img_path)

    try:
        tts_client = Client("mrfakename/E2-F5-TTS")

        # 1. बच्ची की आवाज
        girl_audio = None
        if girl_line:
            res1 = tts_client.predict(
                ref_audio_input=handle_file(GIRL_VOICE),
                ref_text_input="mera sample audio",
                gen_text_input=girl_line,
                remove_silence=False,
                fn_index=0
            )
            girl_audio = res1[0]

        # 2. बत्तख की आवाज
        duck_audio = None
        if duck_line and os.path.exists(DUCK_VOICE):
            res2 = tts_client.predict(
                ref_audio_input=handle_file(DUCK_VOICE),
                ref_text_input="mera sample audio",
                gen_text_input=duck_line,
                remove_silence=False,
                fn_index=0
            )
            duck_audio = res2[0]

        await status.edit_text("2/3: लिप-सिंक वीडियो बन रहा है...")

        # जो भी ऑडियो तैयार हुआ, उससे SadTalker चलाएं
        active_audio = girl_audio if girl_audio else duck_audio
        anim_client = Client("vinthony/SadTalker")
        video_res = anim_client.predict(
            source_image=handle_file(img_path),
            driven_audio=handle_file(active_audio),
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
        
