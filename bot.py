import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import boto3
import tempfile
from pymongo import MongoClient

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPACES_KEY = os.getenv("SPACES_KEY")
SPACES_SECRET = os.getenv("SPACES_SECRET")
SPACES_REGION = os.getenv("SPACES_REGION")
SPACES_BUCKET = os.getenv("SPACES_BUCKET")
SPACES_ENDPOINT = os.getenv("SPACES_ENDPOINT")
MONGO_STR = os.getenv("MONGO_STR")

# MongoDB setup
client = MongoClient(MONGO_STR)
db = client["telegram_db"]
collection = db["lax_itsm"]

# S3/Spaces client setup
s3 = boto3.client(
    "s3",
    region_name=SPACES_REGION,
    endpoint_url=SPACES_ENDPOINT,
    aws_access_key_id=SPACES_KEY,
    aws_secret_access_key=SPACES_SECRET,
)

async def handle_image_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.channel_post
    print("📥 Handler triggered...")

    if not message or not message.photo:
        print("⚠️ No image in message.")
        return

    try:
        # Get best quality photo
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{message.chat.id}_{photo.file_unique_id}_{timestamp}.jpg"

        # Save to temp file and upload to Spaces
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            await file.download_to_drive(temp_file.name)
            s3.upload_file(temp_file.name, SPACES_BUCKET, filename)
            image_url = f"{SPACES_ENDPOINT}/{SPACES_BUCKET}/{filename}"
            print(f"✅ Uploaded to S3: {image_url}")

        # Save metadata to MongoDB
        doc = {
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "caption": message.caption or "",
            "image_url": image_url,
            "timestamp": message.date,
        }
        collection.insert_one(doc)
        print(f"📦 Saved to MongoDB: {doc}")

        # Reply with confirmation
        reply_text = f"✅ Image uploaded and saved!\nURL: {image_url}"
        if message.caption:
            reply_text += f"\n📝 Caption: {message.caption}"
        await message.reply_text(reply_text)

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        await message.reply_text("❌ Failed to upload or save data.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_image_upload))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
