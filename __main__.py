#API_ID = 
#API_HASH = ""
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image, ImageDraw, ImageFont
import io

# Replace these with your values
API_ID = '5282591'
API_HASH = 'd416fe4e323d0e2b4616fef68a8ddd63'
BOT_TOKEN = '7543714729:AAHLRF3GyvJ9OJwhF2jaV5xDlmYgj1-4JfI'
OWNER_ID = 6248131995 # Replace with the actual user ID of the bot owner

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize channels as None
source_channel = None
target_channel = None

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
    global source_channel, target_channel

    if message.text.startswith("/setsource"):
        source_channel = message.text.split(" ", 1)[1]
        await message.reply(f"Source channel set to: {source_channel}")

    elif message.text.startswith("/settarget"):
        target_channel = message.text.split(" ", 1)[1]
        await message.reply(f"Target channel set to: {target_channel}")

    elif message.text == "/getchannels":
        response = f"Source Channel: {source_channel}\nTarget Channel: {target_channel}"
        await message.reply(response)

@app.on_message(filters.chat(source_channel) & filters.media)
async def handle_media(client: Client, message: Message):
    if not target_channel:
        await message.reply("Target channel is not set. Please set it using the /settarget command in PM.")
        return
    
    # Download the media file
    file = await client.download_media(message)
    
    # Prepare inline keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Upload to Target Channel", callback_data="upload_media")]
    ])
    
    # Send a message with the button
    await message.reply("Click the button below to upload this media to the target channel:", reply_markup=keyboard)

@app.on_callback_query(filters.regex("upload_media"))
async def upload_media_callback(client: Client, callback_query):
    message = callback_query.message
    if not target_channel:
        await callback_query.message.reply("Target channel is not set. Please set it using the /settarget command in PM.")
        return

    # Download the media file again (if needed)
    file = await client.download_media(message.reply_to_message)
    
    # Open the image file and add a watermark
    with Image.open(file) as img:
        watermarked_img = await add_watermark(img, WATERMARK_TEXT)
        buffer = io.BytesIO()
        watermarked_img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Upload the watermarked image to the target channel
        await client.send_photo(target_channel, buffer)
        
        # Inform user
        await callback_query.message.reply("Media uploaded to the target channel.")

if name == "main":
    app.run()
