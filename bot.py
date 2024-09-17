from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from PIL import Image
import json
import os

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
        except ValueError:
            await update.message.reply_text('Invalid group ID format.')
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
        except ValueError:
            await update.message.reply_text('Invalid group ID format.')
    else:
        await update.message.reply_text('Usage: /set_target_group_id <group_id>')

async def handle_media(update: Update, context: CallbackContext) -> None:
    config = load_config()
    source_group_id = config.get('source_group_id')
    target_group_id = config.get('target_group_id')

    if source_group_id is None or target_group_id is None:
        await update.message.reply_text('Source or target group ID is not set. Use /set_source_group_id and /set_target_group_id to configure.')
        return

    if update.message.chat_id == source_group_id and update.message.photo:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        await file.download_to_drive('temp.jpg')

        # Open the image and add a watermark
        with Image.open('temp.jpg') as img:
            watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
            img.paste(watermark, (0, 0), watermark)
            img.save('watermarked_temp.jpg')

        # Delete the original media
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)

        # Send the watermarked media to another group
        with open('watermarked_temp.jpg', 'rb') as f:
            await context.bot.send_photo(chat_id=target_group_id, photo=InputFile(f, 'watermarked_temp.jpg'))

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('set_source_group_id', set_source_group_id))
    application.add_handler(CommandHandler('set_target_group_id', set_target_group_id))
    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.GROUPS, handle_media))

    application.run_polling()

if __name__ == '__main__':
    main()
