import logging
import json
import os
import subprocess
import time
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from PIL import Image, ImageDraw, ImageFont

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your bot token and owner ID
TOKEN = 'YOUR_BOT_TOKEN'
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
        "🎉 Welcome to the Media Watermark Bot! 🎉\n\n"
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
                await retry_request(lambda: file.download_to_drive('temp.jpg'))

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
                    x = img.width - textwidth - 10
                    y = img.height - textheight - 10
                    draw.text((x, y), text, font=font, fill=(255, 255, 255, 128))
                    img.save('watermarked_temp.jpg', format='JPEG')

                await retry_request(lambda: context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id))
                logger.info(f"Deleted original message in group {source_group_id}")

                with open('watermarked_temp.jpg', 'rb') as f:
                    await retry_request(lambda: context.bot.send_photo(chat_id=target_group_id, photo=InputFile(f, 'watermarked_temp.jpg'), caption=caption, reply_markup=keyboard))
                    logger.info(f"Sent watermarked photo to group {target_group_id}")

            elif update.message.video:
                logger.info(f"Processing video from group {source_group_id}")
                file = await retry_request(lambda: context.bot.get_file(update.message.video.file_id))
                if file is None:
                    return
                await retry_request(lambda: file.download_to_drive('temp.mp4'))

                # Get the video duration
                duration_command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 'temp.mp4']
                duration = float(subprocess.check_output(duration_command).strip())

                # Calculate the start time to extract the center 7 seconds
                start_time = max((duration - 7) / 2, 0)

                # Create a command to extract the center 7 seconds
                extract_command = [
                    'ffmpeg', '-i', 'temp.mp4', '-ss', str(start_time), '-t', '7',
                    '-c', 'copy', '-y', 'temp_center.mp4'
                ]
                subprocess.run(extract_command, check=True)

                watermark_text = "Watermark"
                ffmpeg_command = [
                    'ffmpeg', '-i', 'temp_center.mp4',
                    '-vf', f"drawtext=text='{watermark_text}':x=10:y=H-th-10:fontsize=24:fontcolor=white@0.5",
                    '-codec:a', 'copy', '-y', 'watermarked_temp.mp4'
                ]
                subprocess.run(ffmpeg_command, check=True)

                await retry_request(lambda: context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id))
                logger.info(f"Deleted original message in group {source_group_id}")

                with open('watermarked_temp.mp4', 'rb') as f:
                    await retry_request(lambda: context.bot.send_video(chat_id=target_group_id, video=InputFile(f, 'watermarked_temp.mp4'), caption=caption, reply_markup=keyboard))
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
