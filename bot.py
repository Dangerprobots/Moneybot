import logging
import json
import os
import subprocess
import time
from io import BytesIO
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from PIL import Image, ImageDraw, ImageFont

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your bot token and owner ID
TOKEN = '7543714729:AAHLRF3GyvJ9OJwhF2jaV5xDlmYgj1-4JfI'
OWNER_ID = 6248131995  # Replace with your Telegram user ID
CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from a file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'source_group_id': None, 'target_group_id': None, 'update_channel_username': None}

def save_config(config):
    """Save configuration to a file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

async def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_message = (
        "🎬 Welcome to the Media Watermark Bot! 🎬\n\n"
        "This bot processes media from a specified group, "
        "adds a watermark, and forwards it to another group.\n\n"
        "As the bot owner, you can set the source and target group IDs "
        "as well as the update channel username.\n\n"
        "Use the following commands to configure the bot:\n"
        "/set_source_group_id <group_id> - Set the source group ID\n"
        "/set_target_group_id <group_id> - Set the target group ID\n"
        "/set_update_channel_username <username> - Set the update channel username"
    )
    await update.message.reply_text(welcome_message)

async def set_source_group_id(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if context.args:
        try:
            group_id = int(context.args[0])
            config = load_config()
            config['source_group_id'] = group_id
            save_config(config)
            await update.message.reply_text(f'Source group ID set to {group_id}.')
        except ValueError:
            await update.message.reply_text('Invalid group ID format.')
    else:
        await update.message.reply_text('Usage: /set_source_group_id <group_id>')

async def set_target_group_id(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if context.args:
        try:
            group_id = int(context.args[0])
            config = load_config()
            config['target_group_id'] = group_id
            save_config(config)
            await update.message.reply_text(f'Target group ID set to {group_id}.')
        except ValueError:
            await update.message.reply_text('Invalid group ID format.')
    else:
        await update.message.reply_text('Usage: /set_target_group_id <group_id>')

async def set_update_channel_username(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if context.args:
        username = context.args[0].lstrip('@')
        config = load_config()
        config['update_channel_username'] = username
        save_config(config)
        await update.message.reply_text(f'Update channel username set to @{username}.')
    else:
        await update.message.reply_text('Usage: /set_update_channel_username <username>')

def retry_request(func, retries=3, delay=5):
    for _ in range(retries):
        try:
            return func()
        except Exception as e:
            logger.error(f"Error during request: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
    logger.error("Max retries reached. Operation failed.")
    return None

async def handle_media(update: Update, context: CallbackContext) -> None:
    try:
        config = load_config()
        source_group_id = config.get('source_group_id')
        target_group_id = config.get('target_group_id')
        update_channel_username = config.get('update_channel_username')

        if source_group_id is None or target_group_id is None or update_channel_username is None:
            await update.message.reply_text('Source, target group ID, or update channel username is not set.')
            return

        if update.message.chat_id == source_group_id:
            caption = "Check out the updated media!"
            button = InlineKeyboardButton(text="Subscribe for Updates", url=f"https://t.me/{update_channel_username}")
            keyboard = InlineKeyboardMarkup([[button]])

            if update.message.photo:
                logger.info(f"Processing photo from group {source_group_id}")
                file = await retry_request(lambda: context.bot.get_file(update.message.photo[-1].file_id))
                if file is None:
                    return
                image_bytes = await file.download_as_bytearray()

                # Process image in-memory
                with Image.open(BytesIO(image_bytes)) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    draw = ImageDraw.Draw(img)
                    text = "Watermark"
                    try:
                        font = ImageFont.truetype("arial.ttf", 36)
                    except IOError:
                        font = ImageFont.load_default()
                    textwidth, textheight = draw.textsize(text, font)
                    x = img.width - textwidth - 10
                    y = img.height - textheight - 10
                    draw.text((x, y), text, font=font, fill=(255, 255, 255, 128))

                    # Save to a BytesIO object (in-memory)
                    img_bytes = BytesIO()
                    img.save(img_bytes, format='JPEG')
                    img_bytes.seek(0)  # Rewind to the beginning of the BytesIO stream

                await retry_request(lambda: context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id))
                logger.info(f"Deleted original message in group {source_group_id}")

                # Send watermarked photo
                await retry_request(lambda: context.bot.send_photo(chat_id=target_group_id, photo=InputFile(img_bytes, 'watermarked_temp.jpg'), caption=caption, reply_markup=keyboard))
                logger.info(f"Sent watermarked photo to group {target_group_id}")

            elif update.message.video:
                logger.info(f"Processing video from group {source_group_id}")
                file = await retry_request(lambda: context.bot.get_file(update.message.video.file_id))
                if file is None:
                    return
                video_bytes = await file.download_as_bytearray()

                # Compress video in-memory
                input_video = BytesIO(video_bytes)
                input_video.seek(0)  # Rewind

                # Create a command to process the video in memory
                compress_command = [
                    'ffmpeg', '-i', 'pipe:0', '-vcodec', 'libx264', '-crf', '28', '-preset', 'fast', '-y', 'pipe:1'
                ]

                # Run ffmpeg with subprocess to process the video in-memory
                process = subprocess.Popen(compress_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                compressed_video, stderr = process.communicate(input=input_video.read())

                if process.returncode != 0:
                    logger.error(f"Error compressing video: {stderr.decode()}")
                    return

                # Prepare video for watermarking
                input_video = BytesIO(compressed_video)
                input_video.seek(0)

                # Extract a 7-second segment from the center
                duration_command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 'pipe:0']
                duration = float(subprocess.check_output(duration_command, input=input_video.read()).strip())

                start_time = max((duration - 7) / 2, 0)
                extract_command = [
                    'ffmpeg', '-i', 'pipe:0', '-ss', str(start_time), '-t', '7',
                    '-c', 'copy', '-y', 'pipe:1'
                ]
                process = subprocess.Popen(extract_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                extracted_video, stderr = process.communicate(input=input_video.read())

                if process.returncode != 0:
                    logger.error(f"Error extracting video segment: {stderr.decode()}")
                    return

                # Watermark the extracted video
                ffmpeg_command = [
                    'ffmpeg', '-i', 'pipe:0', '-vf', "drawtext=text='Watermark':x=10:y=H-th-10:fontsize=24:fontcolor=white@0.5", '-codec:a', 'copy', '-y', 'pipe:1'
                ]
                process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                watermarked_video, stderr = process.communicate(input=extracted_video)

                if process.returncode != 0:
                    logger.error(f"Error watermarking video: {stderr.decode()}")
                    return

                # Send watermarked video
                await retry_request(lambda: context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id))
                logger.info(f"Deleted original message in group {source_group_id}")

                video_input = BytesIO(watermarked_video)
                video_input.seek(0)

                await retry_request(lambda: context.bot.send_video(chat_id=target_group_id, video=InputFile(video_input, 'watermarked_temp.mp4'), caption=caption, reply_markup=keyboard))
                logger.info(f"Sent watermarked video to group {target_group_id}")

    except Exception as e:
        logger.error(f"Failed to handle media: {e}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('set_source_group_id', set_source_group_id))
    application.add_handler(CommandHandler('set_target_group_id', set_target_group_id))
    application.add_handler(CommandHandler('set_update_channel_username', set_update_channel_username))
    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.GROUPS, handle_media))
    application.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.GROUPS, handle_media))

    application.run_polling()

if __name__ == '__main__':
    main()
