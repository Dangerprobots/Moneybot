import logging
import json
import os
import subprocess
import time
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.helpers import Request
from PIL import Image, ImageDraw, ImageFont

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your bot token
TOKEN = '7543714729:AAHLRF3GyvJ9OJwhF2jaV5xDlmYgj1-4JfI'
CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from a file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'source_group_id': None, 'target_group_id': None}

def save_config(config):
    """Save configuration to a file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Bot is running! Use /set_source_group_id and /set_target_group_id to set group IDs.')

async def set_source_group_id(update: Update, context: CallbackContext) -> None:
    if context.args:
        try:
            group_id = int(context.args[0])
            config = load_config()
            config['source_group_id'] = group_id
            save_config(config)
            await update.message.reply_text(f'Source group ID set to {group_id}.')
            logger.info(f"Source group ID set to {group_id}")
        except ValueError:
            await update.message.reply_text('Invalid group ID format.')
            logger.error("Invalid group ID format")
    else:
        await update.message.reply_text('Usage: /set_source_group_id <group_id>')

async def set_target_group_id(update: Update, context: CallbackContext) -> None:
    if context.args:
        try:
            group_id = int(context.args[0])
            config = load_config()
            config['target_group_id'] = group_id
            save_config(config)
            await update.message.reply_text(f'Target group ID set to {group_id}.')
            logger.info(f"Target group ID set to {group_id}")
        except ValueError:
            await update.message.reply_text('Invalid group ID format.')
            logger.error("Invalid group ID format")
    else:
        await update.message.reply_text('Usage: /set_target_group_id <group_id>')

def retry_request(func, retries=3, delay=5):
    for _ in range(retries):
        try:
            return func()
        except Exception as e:
            logger.error(f"Error during request: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
    raise Exception("Max retries reached.")

async def handle_media(update: Update, context: CallbackContext) -> None:
    try:
        config = load_config()
        source_group_id = config.get('source_group_id')
        target_group_id = config.get('target_group_id')

        if source_group_id is None or target_group_id is None:
            await update.message.reply_text('Source or target group ID is not set. Use /set_source_group_id and /set_target_group_id to configure.')
            return

        if update.message.chat_id == source_group_id:
            if update.message.photo:
                logger.info(f"Processing photo from group {source_group_id}")
                file = await retry_request(lambda: context.bot.get_file(update.message.photo[-1].file_id))
                await retry_request(lambda: file.download_to_drive('temp.jpg'))

                # Process the image
                with Image.open('temp.jpg') as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    draw = ImageDraw.Draw(img)
                    text = "Watermark"
                    try:
                        font = ImageFont.truetype("arial.ttf", 36)
                    except IOError:
                        font = ImageFont.load_default()
                    
                    textwidth, textheight = draw.textsize(text, font)
                    width, height = img.size
                    x = width - textwidth - 10
                    y = height - textheight - 10
                    draw.text((x, y), text, font=font, fill=(255, 255, 255, 128))
                    img.save('watermarked_temp.jpg', format='JPEG')

                # Delete the original media
                await retry_request(lambda: context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id))
                logger.info(f"Deleted original message in group {source_group_id}")

                # Send the watermarked media to another group
                with open('watermarked_temp.jpg', 'rb') as f:
                    await retry_request(lambda: context.bot.send_photo(chat_id=target_group_id, photo=InputFile(f, 'watermarked_temp.jpg')))
                    logger.info(f"Sent watermarked photo to group {target_group_id}")

            elif update.message.video:
                logger.info(f"Processing video from group {source_group_id}")
                file = await retry_request(lambda: context.bot.get_file(update.message.video.file_id))
                await retry_request(lambda: file.download_to_drive('temp.mp4'))

                # Add a watermark to the video using ffmpeg
                watermark_text = "Watermark"
                ffmpeg_command = [
                    'ffmpeg', '-i', 'temp.mp4', 
                    '-vf', f"drawtext=text='{watermark_text}':x=10:y=H-th-10:fontsize=24:fontcolor=white@0.5",
                    '-codec:a', 'copy', 'watermarked_temp.mp4'
                ]
                subprocess.run(ffmpeg_command, check=True)

                # Delete the original media
                await retry_request(lambda: context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id))
                logger.info(f"Deleted original message in group {source_group_id}")

                # Send the watermarked media to another group
                with open('watermarked_temp.mp4', 'rb') as f:
                    await retry_request(lambda: context.bot.send_video(chat_id=target_group_id, video=InputFile(f, 'watermarked_temp.mp4')))
                    logger.info(f"Sent watermarked video to group {target_group_id}")
    except Exception as e:
        logger.error(f"Failed to handle media: {e}")

def main() -> None:
    # Use Request object to configure timeout
    request = Request(con_pool_size=8, read_timeout=60, connect_timeout=60)
    
    application = Application.builder().token(TOKEN).request(request).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('set_source_group_id', set_source_group_id))
    application.add_handler(CommandHandler('set_target_group_id', set_target_group_id))
    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.GROUPS, handle_media))
    application.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.GROUPS, handle_media))

    application.run_polling()

if __name__ == '__main__':
    main()
