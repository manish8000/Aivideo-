import base64

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.caption
    if not user_text:
        await update.message.reply_text("कृपया फोटो के साथ कैप्शन में डायलॉग भी लिखें!")
        return

    status_msg = await update.message.reply_text("फोटो प्रोसेस हो रही है...")

    try:
        photo_file = await update.message.photo[-1].get_file()
        file_path = f"{update.message.chat_id}_input.jpg"
        await photo_file.download_to_drive(file_path)

        # फाइल अपलोड
        with open(file_path, "rb") as f:
            upload_res = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}).json()
        
        if "data" not in upload_res or "url" not in upload_res["data"]:
            await status_msg.edit_text("इमेज अपलोड सर्वर डाउन है, कृपया 1 मिनट बाद कोशिश करें।")
            return

        img_url = upload_res["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")

        # API Key फॉर्मेटिंग (ऑटो-बेस64 हैंडलिंग)
        api_key = os.getenv("DID_API_KEY", "").strip()
        if ":" in api_key:
            auth_header = "Basic " + base64.b64encode(api_key.encode()).decode()
        else:
            auth_header = f"Basic {api_key}"

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
            # अगर D-ID एरर दे तो यूज़र को साफ मैसेज दिखे
            err_detail = create_res.get("description") or create_res.get("message") or str(create_res)
            await status_msg.edit_text(f"D-ID एरर: {err_detail}")
            return

        await status_msg.edit_text("AI लिप-सिंक तैयार कर रहा है (लगभग 20-30 सेकंड)...")
        
        result_url = None
        for _ in range(40):
            time.sleep(3)
            check_res = requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers).json()
            if check_res.get("status") == "done":
                result_url = check_res.get("result_url")
                break
            elif check_res.get("status") == "error":
                await status_msg.edit_text("वीडियो जनरेट नहीं हो सका। कृपया साफ चेहरे वाली फोटो यूज़ करें।")
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
            
