import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# API Keys
TELEGRAM_BOT_TOKEN = "8815666314:AAHPEMUcIaaTJMn-Q9RMEZLEZ58951D7Kyk"
DID_API_KEY = os.getenv("DID_API_KEY")  # D-ID से मिली हुई API Key

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
        "नमस्ते! मुझे एक फोटो भेजें और कैप्शन में वह टेक्स्ट लिखें जो आप बुलवाना चाहते हैं।\n"
        "उदाहरण: फोटो अटैच करें और कैप्शन में लिखें 'Hello, how are you?'"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.caption
    if not user_text:
        await update.message.reply_text("कृपया फोटो के साथ कैप्शन में वह डायलॉग/टेक्स्ट भी लिखें जो बुलवाना है!")
        return

    status_msg = await update.message.reply_text("फोटो मिल गई! टॉकिंग एनिमेशन तैयार किया जा रहा है...")

    try:
        # 1. Telegram से फोटो डाउनलोड करें
        photo_file = await update.message.photo[-1].get_file()
        file_path = f"{update.message.chat_id}_input.jpg"
        await photo_file.download_to_drive(file_path)

        # 2. फोटो को पब्लिक URL पर अपलोड करें (D-ID को इमेज URL चाहिए होता है)
        with open(file_path, "rb") as f:
            upload_res = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}).json()
        
        # tmpfiles.org डायरेक्ट लिंक कन्वर्ट करना
        img_url = upload_res["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")

        # 3. D-ID API को टॉकिंग वीडियो जनरेट करने का टास्क दें
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Basic {DID_API_KEY}"
        }
        
        payload = {
            "source_url": img_url,
            "script": {
                "type": "text",
                "input": user_text,
                "provider": {
                    "type": "microsoft",
                    "voice_id": "hi-IN-MadhurNeural"  # हिंदी आवाज़
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
            await status_msg.edit_text(f"D-ID एरर: {create_res}")
            return

        # 4. वीडियो तैयार होने का इंतज़ार करें (Polling)
        await status_msg.edit_text("AI लिप-सिंक और मूवमेंट रेंडर कर रहा है...")
        result_url = None
        for _ in range(30):
            time.sleep(4)
            check_res = requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers).json()
            if check_res.get("status") == "done":
                result_url = check_res.get("result_url")
                break
            elif check_res.get("status") == "error":
                break

        # 5. यूज़र को वीडियो भेजें
        if result_url:
            await update.message.reply_video(
                video=result_url,
                caption=f"🗣️: {user_text}"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("वीडियो रेंडर नहीं हो सकी, कृपया दोबारा प्रयास करें।")

        # लोकल फाइल हटाएं
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await update.message.reply_text(f"त्रुटि आई: {e}")

def main():
    # Koyeb 8000 पोर्ट को जिंदा रखने के लिए
    threading.Thread(target=run_http_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("बॉट चालू हो गया है...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
