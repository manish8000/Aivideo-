import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_audioclips

BOT_TOKEN = os.getenv("BOT_TOKEN")

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
        "फोटो भेजिए और कैप्शन में डायलॉग लिखें:\n\n"
        "Girl: अरे बत्तख भाई, चश्मा कैसा लगा?\n"
        "Duck: क्वैक क्वैक! बहुत बढ़िया लगा!"
    )

async def generate_speech(text, role):
    path = f"{role}_temp.mp3"
    if role == "duck":
        comm = edge_tts.Communicate(text, "hi-IN-MadhurNeural", pitch="+35Hz", rate="+10%")
    else:
        comm = edge_tts.Communicate(text, "hi-IN-SwaraNeural", pitch="+15Hz", rate="+5%")
    await comm.save(path)
    return path

def build_animated_video(img_path, audio_paths, output_path="final_video.mp4"):
    # दोनों ऑडियो को जोड़ना
    clips = [AudioFileClip(p) for p in audio_paths if os.path.exists(p)]
    if not clips:
        raise Exception("ऑडियो तैयार नहीं हो सका")
    
    final_audio = concatenate_audioclips(clips)
    duration = final_audio.duration

    # इमेज पर स्मूथ कार्टून ज़ूम/मोशन लगाना
    clip = ImageClip(img_path).set_duration(duration)
    clip = clip.resize(lambda t: 1 + 0.04 * (t / duration))  # स्लो डायनामिक ज़ूम
    clip = clip.set_audio(final_audio)

    clip.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        logger=None
    )
    return output_path

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.photo or not msg.caption:
        await msg.reply_text("कृपया फोटो के साथ डायलॉग भेजें!")
        return

    caption = msg.caption.strip()
    girl_line = ""
    duck_line = ""

    for line in caption.split("\n"):
        clean = line.strip()
        if clean.lower().startswith("girl:"):
            girl_line = clean.split(":", 1)[1].strip()
        elif clean.lower().startswith("duck:"):
            duck_line = clean.split(":", 1)[1].strip()

    if not girl_line and not duck_line:
        girl_line = caption

    status = await msg.reply_text("1/2: आवाज़ें तैयार हो रही हैं...")
    photo_file = await msg.photo[-1].get_file()
    img_path = "input_char.jpg"
    await photo_file.download_to_drive(img_path)

    audio_files = []
    try:
        if girl_line:
            a1 = await generate_speech(girl_line, "girl")
            audio_files.append(a1)
        if duck_line:
            a2 = await generate_speech(duck_line, "duck")
            audio_files.append(a2)

        await status.edit_text("2/2: वीडियो बन रहा है...")

        loop = asyncio.get_event_loop()
        video_path = await loop.run_in_executor(None, build_animated_video, img_path, audio_files)

        await update.message.reply_video(
            video=open(video_path, 'rb'),
            caption="🎬 आपका कार्टून वीडियो तैयार है!"
        )
        await status.delete()

    except Exception as e:
        await status.edit_text(f"एरर आया: {str(e)}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()

    if BOT_TOKEN:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), process_video))
        app.run_polling()
        
