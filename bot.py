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

    status = await msg.reply_text("1/3: आवाज़ तैयार हो रही है...")
    photo_file = await msg.photo[-1].get_file()
    img_path = "input_char.jpg"
    await photo_file.download_to_drive(img_path)

    try:
        # F5-TTS का प्राइमरी और बैकअप स्पेस
        try:
            tts_client = Client("SWivid/F5-TTS")
        except Exception:
            tts_client = Client("hf-audio/F5-TTS")

        active_audio = None

        # 1. बच्ची की आवाज
        if girl_line and os.path.exists(GIRL_VOICE):
            res1 = tts_client.predict(
                ref_audio_orig=handle_file(GIRL_VOICE),
                ref_text="sample audio",
                gen_text=girl_line,
                remove_silence=False,
                api_name="/basic_tts"
            )
            active_audio = res1[0]

        # 2. बत्तख की आवाज (अगर बच्ची की लाइन नहीं है तो बत्तख का ऑडियो)
        if not active_audio and duck_line and os.path.exists(DUCK_VOICE):
            res2 = tts_client.predict(
                ref_audio_orig=handle_file(DUCK_VOICE),
                ref_text="sample audio",
                gen_text=duck_line,
                remove_silence=False,
                api_name="/basic_tts"
            )
            active_audio = res2[0]

        await status.edit_text("2/3: वीडियो रेंडर हो रहा है...")

        # लिप-सिंक स्पेस
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
        await msg.reply_text(f"एरर आया: {str(e)}\n\n(HuggingFace स्पेस बिजी हो सकता है, 1-2 मिनट बाद दोबारा कोशिश करें)")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()

    if BOT_TOKEN:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), process_video))
        app.run_polling()
        
