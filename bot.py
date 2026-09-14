import os
import io
import requests
from PIL import Image
from rembg import remove
import replicate

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! फोटो भेजें, मैं पारदर्शी कार्टून PNG बना दूंगा।")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("प्रोसेसिंग शुरू हो रही है...")
    try:
        photo_file = await update.message.photo[-1].get_file()
        input_path = "input.jpg"
        await photo_file.download_to_drive(input_path)

        await status_msg.edit_text("कार्टून स्टाइल बनाया जा रहा है...")
        with open(input_path, "rb") as img:
            output = replicate.run(
                "fofr/face-to-sticker:76298fc8dabb42534570d988e5625bde3f12603ac1a8123d4ac1739fb5c8b5df",
                input={"image": img, "steps": 20, "prompt": "cartoon vector sticker"}
            )

        img_url = output[0] if isinstance(output, list) else output
        res = requests.get(img_url)
        cartoon = Image.open(io.BytesIO(res.content))

        await status_msg.edit_text("बैकग्राउंड हटाया जा रहा है...")
        output_png = remove(cartoon)
        out_path = "sticker.png"
        output_png.save(out_path, format="PNG")

        with open(out_path, "rb") as f:
            await update.message.reply_document(document=f, filename="cartoon.png")

        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(out_path): os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"त्रुटि: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
            
