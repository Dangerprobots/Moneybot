from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image, ImageDraw, ImageFont
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your provided API credentials
api_id = "1474940"
api_hash = "779e8d2b32ef76d0b7a11fb5f132a6b6"
bot_token = "7543714729:AAHLRF3GyvJ9OJwhF2jaV5xDlmYgj1-4JfI"

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Initialize a dictionary to store group IDs
group_ids = {
    'source_group_id': None,
    'destination_group_id': None
}

# Load stored group IDs from a file if it exists
try:
    with open("group_ids.json", "r") as f:
        group_ids.update(json.load(f))
except FileNotFoundError:
    pass

@app.on_message(filters.private & filters.text)
async def handle_pm(client, message: Message):
    bot_owner_id = 6248131995  # Replace with your user ID

    if message.from_user.id != bot_owner_id:
        await message.reply("You are not authorized to use this bot.")
        return

    text = message.text.strip()
    logger.info(f"Received PM: {text}")

    if text.startswith("/set_source"):
        parts = text.split()
        if len(parts) == 2:
            _, group_id = parts
            try:
                group_ids['source_group_id'] = int(group_id)
                save_group_ids()
                await message.reply(f"Source group ID set to {group_id}")
            except ValueError:
                await message.reply("Invalid group ID format. It should be a number.")
        else:
            await message.reply("Usage: /set_source <group_id>")

    elif text.startswith("/set_destination"):
        parts = text.split()
        if len(parts) == 2:
            _, group_id = parts
            try:
                group_ids['destination_group_id'] = int(group_id)
                save_group_ids()
                await message.reply(f"Destination group ID set to {group_id}")
            except ValueError:
                await message.reply("Invalid group ID format. It should be a number.")
        else:
            await message.reply("Usage: /set_destination <group_id>")

    elif text == "/get_ids":
        source_id = group_ids.get('source_group_id', 'Not set')
        destination_id = group_ids.get('destination_group_id', 'Not set')
        response = f"Source Group ID: {source_id}\nDestination Group ID: {destination_id}"
        await message.reply(response)

    elif text == "/save_ids":
        save_group_ids()
        await message.reply("Group IDs saved to file.")

    elif text == "/load_ids":
        try:
            with open("group_ids.json", "r") as f:
                group_ids.update(json.load(f))
            await message.reply("Group IDs loaded from file.")
        except FileNotFoundError:
            await message.reply("No saved file found.")

def save_group_ids():
    with open("group_ids.json", "w") as f:
        json.dump(group_ids, f)

@app.on_message(filters.chat(lambda c: c.id == group_ids.get('source_group_id')) & filters.media)
async def handle_media(client, message: Message):
    if not group_ids['source_group_id'] or not group_ids['destination_group_id']:
        logger.warning("Group IDs are not set properly.")
        return

    media = message.photo or message.video or message.document
    if media:
        file_id = media.file_id
        try:
            # Download media
            downloaded_media = await app.download_media(file_id)
            logger.info(f"Downloaded media: {downloaded_media}")

            # Add watermark
            watermarked_media_path = add_watermark(downloaded_media)
            logger.info(f"Watermarked media saved at: {watermarked_media_path}")

            # Send media to the destination group
            await app.send_document(group_ids['destination_group_id'], watermarked_media_path)
            logger.info("Media sent to destination group.")

            # Delete the original message
            await app.delete_messages(group_ids['source_group_id'], message.message_id)
            logger.info("Original message deleted.")

        except Exception as e:
            logger.error(f"Error handling media: {e}")

def add_watermark(media_path):
    if media_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            with Image.open(media_path) as img:
                # Create a drawing context
                draw = ImageDraw.Draw(img)
                # Define watermark text and font
                watermark_text = "Your Watermark"
                font = ImageFont.load_default()
                text_width, text_height = draw.textsize(watermark_text, font)
                # Position watermark in bottom-right corner
                width, height = img.size
                x = width - text_width - 10
                y = height - text_height - 10
                # Add text to image
                draw.text((x, y), watermark_text, font=font)
                # Save watermarked image
                watermarked_path = "watermarked_" + os.path.basename(media_path)
                img.save(watermarked_path)
                return watermarked_path
        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
            return media_path  # Return original path if there's an error
    else:
        # For simplicity, this example does not handle video watermarking
        return media_path  # Return the original path if not an image

app.run()
