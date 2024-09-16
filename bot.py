import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image, ImageDraw, ImageFont
import io
import os

# Replace these with your values
API_ID = '5282591'
API_HASH = 'd416fe4e323d0e2b4616fef68a8ddd63'
BOT_TOKEN = '7543714729:AAHLRF3GyvJ9OJwhF2jaV5xDlmYgj1-4JfI'
OWNER_ID = 6248131995 # Replace with the actual user ID of the bot owner

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize groups as None
source_group = None
target_group = None

# Define watermark text
WATERMARK_TEXT = "Sample Watermark"

async def add_watermark(image: Image.Image, text: str) -> Image.Image:
    width, height = image.size
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()  # Use a default font or load a TTF font
    text_width, text_height = draw.textsize(text, font=font)
    x = width - text_width - 10
    y = height - text_height - 10
    draw.text((x, y), text, font=font, fill="white")
    return image

@app.on_message(filters.private & filters.user(OWNER_ID))
async def handle_owner_commands(client: Client, message: Message):
    global source_group, target_group

    if message.text.startswith("/setsource"):
        source_group = message.text.split(" ", 1)[1]
        await message.reply(f"Source group set to: {source_group}")

    elif message.text.startswith("/settarget"):
        target_group = message.text.split(" ", 1)[1]
        await message.reply(f"Target group set to: {target_group}")

    elif message.text == "/getgroups":
        response = f"Source Group: {source_group}\nTarget Group: {target_group}"
        await message.reply(response)

@app.on_message(filters.group(source_group) & filters.media)
async def handle_media(client: Client, message: Message):
    if not target_group:
        await message.reply("Target group is not set. Please set it using the /settarget command in PM.")
        return
    
    # Download the media file
    file_path = await client.download_media(message)
    
    # Prepare inline keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Upload to Target Group", callback_data="upload_media")]
    ])
    
    # Store file path in the message context
    await message.reply("Click the button below to upload this media to the target group:", reply_markup=keyboard, reply_to_message_id=message.message_id, reply_to_message=file_path)

@app.on_callback_query(filters.regex("upload_media"))
async def upload_media_callback(client: Client, callback_query):
    message = callback_query.message
    if not target_group:
        await callback_query.message.reply("Target group is not set. Please set it using the /settarget command in PM.")
        return

    # Retrieve file path from message context
    file_path = message.reply_to_message.reply_to_message
    if not file_path:
        await callback_query.message.reply("No media file found. Please try again.")
        return

    # Open the image file and add a watermark
    with Image.open(file_path) as img:
        watermarked_img = await add_watermark(img, WATERMARK_TEXT)
        buffer = io.BytesIO()
        watermarked_img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Upload the watermarked image to the target group
        await client.send_photo(target_group, buffer)
        
        # Inform user
        await callback_query.message.reply("Media uploaded to the target group.")

if __name__ == "__main__":
    app.run()
