import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client, handle_file
import edge_tts

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")  # HuggingFace फ्री टोकन (401 ब्लॉक बायपास करने के लिए)

# Koyeb Health Check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot Healthy!")

def run_web():
    server = HTTPServer(('0.0.0.0', 8000), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "फोटो भेजिए और कैप्शन में सिर्फ डायलॉग लिखें:\n\n"
        "Girl: अरे बत्तख भाई, चश्मा कैसा लगा?\n"
        "Duck: क्वैक क्वैक! बहुत बढ़िया लगा!"
    )

async def generate_speech(text, role):
    output_path = f"{role}_audio.mp3"
    if role == "duck":
        comm = edge_tts.Communicate(text, "hi-IN-MadhurNeural", pitch="+35Hz", rate="+10%")
    else:
        comm = edge_tts.Communicate(text, "hi-IN-SwaraNeural", pitch="+15Hz", rate="+5%")
    await comm.save(output_path)
    return output_path

def render_lip_sync(image_path, audio_path):
    # एक्टिव और वेरिफाइड स्पेस लिस्ट
    working_spaces = [
        "akhaliq/SadTalker",
        "camenduru/SadTalker"
    ]
    
    last_err = ""
    for space in working_spaces:
        try:
            client = Client(space, hf_token=HF_TOKEN) if HF_TOKEN else Client(space)
            res = client.predict(
                source_image=handle_file(image_path),
                driven_audio=handle_file(audio_path),
                fn_index=0
            )
            return res['video'] if isinstance(res, dict) else res
        except Exception as e:
            last_err = str(e)
            continue

    raise Exception(f"सर्वर रिस्पांस: {last_err}")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.photo or not msg.caption:
        await msg.reply_text("कृपया फोटो के साथ डायलॉग (caption) भेजें!")
        return

    caption = msg.caption.strip()
    girl_line = ""
    duck_line = ""

    for line in caption.split("\n"):
        clean_line = line.strip()
        if clean_line.lower().startswith("girl:"):
            girl_line = clean_line.split(":", 1)[1].strip()
        elif clean_line.lower().startswith("duck:"):
            duck_line = clean_line.split(":", 1)[1].strip()

    if not girl_line and not duck_line:
        girl_line = caption

    status = await msg.reply_text("1/3: आवाज तैयार हो रही है...")
    photo_file = await msg.photo[-1].get_file()
    img_path = "input_char.jpg"
    await photo_file.download_to_drive(img_path)

    try:
        # आवाज तैयार
        if girl_line:
            audio_path = await generate_speech(girl_line, "girl")
        else:
            audio_path = await generate_speech(duck_line, "duck")

        await status.edit_text("2/3: वीडियो रेंडर हो रहा है (SadTalker)...")

        # ऑथेंटिकेटेड वीडियो रेंडर
        loop = asyncio.get_event_loop()
        video_path = await loop.run_in_executor(None, render_lip_sync, img_path, audio_path)

        await status.edit_text("3/3: वीडियो भेजा जा रहा है...")
        await msg.reply_video(video=open(video_path, 'rb'))
        await status.delete()

    except Exception as e:
        await status.edit_text(f"एरर: {str(e)}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()

    if BOT_TOKEN:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), process_video))
        app.run_polling()
        
