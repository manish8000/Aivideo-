import os
import io
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from PIL import Image
from rembg import remove
import replicate

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# आपके API Tokens
TELEGRAM_BOT_TOKEN = "8815666314:AAHPEMUcIaaTJMn-Q9RMEZLEZ58951D7Kyk"
REPLICATE_API_TOKEN = "r8_GkR524X53eXjj3CUj7oWtlGdF5WxZMu3Q3Dk8"

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

# Koyeb Web Service के Health Check को 200 OK देने के लिए डमी HTTP सर्वर
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is healthy and running!")

def run_http_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! मुझे अपनी एक साफ फोटो भेजें, मैं उसका पारदर्शी कार्टून PNG बना दूंगा।")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("फोटो मिल गई! कार्टून प्रोसेस किया जा रहा है...")
    try:
        photo_file = await update.message.photo[-1].get_file()
        input_path = "input.jpg"
        await photo_file.download_to_drive(input_path)

        await status_msg.edit_text("AI कार्टून स्टाइल तैयार कर रहा है...")
        with open(input_path, "rb") as img:
            output = replicate.run(
                "fofr/face-to-sticker:76298fc8dabb42534570d988e5625bde3f12603ac1a8123d4ac1739fb5c8b5df",
                input={"image": img, "steps": 20, "prompt": "cartoon vector sticker, clean edges"}
            )

        img_url = output[0] if isinstance(output, list) else output
        res = requests.get(img_url)
        cartoon = Image.open(io.BytesIO(res.content))

        await status_msg.edit_text("बैकग्राउंड हटाया जा रहा है (PNG बन रहा है)...")
        output_png = remove(cartoon)
        out_path = "sticker.png"
        output_png.save(out_path, format="PNG")

        with open(out_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="cartoon.png",
                caption="ये रहा आपका कस्टमाइज्ड कार्टून PNG!"
            )

        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(out_path):
            os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"त्रुटि आई: {e}")

def main():
    # Koyeb Port 8000 हेल्थ चेक को संतुष्ट करने के लिए बैकग्राउंड थ्रेड
    threading.Thread(target=run_http_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("बॉट सफलतापूर्वक चालू हो गया है!")
    app.run_polling()

if __name__ == "__main__":
    main()
    
