import os
import time
import base64
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# API Keys
TELEGRAM_BOT_TOKEN = "8815666314:AAHPEMUcIaaTJMn-Q9RMEZLEZ58951D7Kyk"
DID_API_KEY = os.getenv("DID_API_KEY", "").strip()

# Koyeb Health Check Handler
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is healthy!")

def run_http_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "नमस्ते! मुझे एक फोटो भेजें और कैप्शन में वह टेक्स्ट लिखें जो आप बुलवाना चाहते हैं।"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.caption
    if not user_text:
        await update.message.reply_text("कृपया फोटो के साथ कैप्शन में डायलॉग भी लिखें!")
        return

    status_msg = await update.message.reply_text("फोटो प्रोसेस हो रही है...")
    file_path = f"{update.message.chat_id}_input.jpg"

    try:
        photo_file = await update.message.photo[-1].get_file()
        await photo_file.download_to_drive(file_path)

        with open(file_path, "rb") as f:
            upload_res = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}).json()
        
        if "data" not in upload_res or "url" not in upload_res["data"]:
            await status_msg.edit_text("इमेज सर्वर डाउन है, कृपया थोड़ी देर बाद प्रयास करें।")
            return

        img_url = upload_res["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")

        if ":" in DID_API_KEY:
            auth_header = "Basic " + base64.b64encode(DID_API_KEY.encode()).decode()
        else:
            auth_header = f"Basic {DID_API_KEY}"

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": auth_header
        }
        
        payload = {
            "source_url": img_url,
            "script": {
                "type": "text",
                "input": user_text,
                "provider": {
                    "type": "microsoft",
                    "voice_id": "hi-IN-MadhurNeural"
                }
            },
            "config": {
                "fluent": True,
                "pad_audio": 0.0
            }
        }

        create_res = requests.post("https://api.d-id.com/talks", json=payload, headers=headers).json()
        talk_id = create_res.get("id")

        if not talk_id:
            err_detail = create_res.get("description") or create_res.get("message") or str(create_res)
            await status_msg.edit_text(f"D-ID एरर: {err_detail}")
            return

        await status_msg.edit_text("AI लिप-सिंक तैयार कर रहा है (20-30 सेकंड)...")
        
        result_url = None
        for _ in range(40):
            await asyncio.sleep(3)
            check_res = requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers).json()
            if check_res.get("status") == "done":
                result_url = check_res.get("result_url")
                break
            elif check_res.get("status") == "error":
                await status_msg.edit_text("वीडियो जनरेट नहीं हो सका। कृपया सामने से ली गई साफ फोटो भेजें।")
                return

        if result_url:
            await update.message.reply_video(video=result_url, caption=f"🗣️: {user_text}")
            await status_msg.delete()
        else:
            await status_msg.edit_text("टाइमआउट: रेंडरिंग में बहुत ज्यादा समय लगा।")

    except Exception as e:
        await update.message.reply_text(f"सिस्टम एरर: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def main():
    threading.Thread(target=run_http_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("बॉट चालू हो गया है...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # बॉट को चालू रखने के लिए अनिश्चित काल तक प्रतीक्षा
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
    
