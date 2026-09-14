import os
import io
import requests
from PIL import Image
from rembg import remove
import replicate

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# अपनी API Keys यहाँ डालें
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
REPLICATE_API_TOKEN = "YOUR_REPLICATE_API_TOKEN"

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! मुझे अपनी एक साफ फोटो भेजिए, मैं उसका कार्टून PNG बनाकर दूंगा।")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("फोटो मिल गई! कार्टून बनाने की प्रक्रिया शुरू हो रही है...")

    try:
        # 1. Telegram से फोटो डाउनलोड करना
        photo_file = await update.message.photo[-1].get_file()
        input_image_path = "user_photo.jpg"
        await photo_file.download_to_drive(input_image_path)

        await status_msg.edit_text("चेहरे को कार्टून में बदला जा रहा है (AI Processing)...")

        # 2. Replicate API (Face-to-Sticker मॉडल) को फोटो भेजना
        with open(input_image_path, "rb") as image_data:
            output = replicate.run(
                "fofr/face-to-sticker:76298fc8dabb42534570d988e5625bde3f12603ac1a8123d4ac1739fb5c8b5df",
                input={
                    "image": image_data,
                    "steps": 20,
                    "prompt": "cartoon character, sharp vector illustration, clean lines",
                    "negative_prompt": "ugly, blurry, low quality, distorted"
                }
            )

        # AI आउटपुट URL से इमेज डाउनलोड करना
        generated_image_url = output[0] if isinstance(output, list) else output
        response = requests.get(generated_image_url)
        cartoon_image = Image.open(io.BytesIO(response.content))

        await status_msg.edit_text("बैकग्राउंड हटाया जा रहा है (Transparent PNG)...")

        # 3. बैकग्राउंड हटाकर पारदर्शी PNG बनाना
        output_png = remove(cartoon_image)
        output_path = "final_sticker.png"
        output_png.save(output_path, format="PNG")

        await status_msg.edit_text("PNG तैयार है, भेजी जा रही है...")

        # 4. यूजर को बिना कंप्रेस किए डॉक्यूमेंट के रूप में भेजना
        with open(output_path, "rb") as final_file:
            await update.message.reply_document(
                document=final_file,
                filename="cartoon_custom.png",
                caption="ये रहा आपका कार्टून PNG!"
            )

        # अस्थायी फाइलें हटाना
        if os.path.exists(input_image_path):
            os.remove(input_image_path)
        if os.path.exists(output_path):
            os.remove(output_path)

    except Exception as e:
        await update.message.reply_text(f"त्रुटि आई: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("बॉट शुरू हो गया है...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
