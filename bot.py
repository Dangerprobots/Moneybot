from pyrogram import Client, filters
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace these with your actual values
api_id = "1474940"       # Obtain from https://my.telegram.org/
api_hash = "779e8d2b32ef76d0b7a11fb5f132a6b6"   # Obtain from https://my.telegram.org/
bot_token = "7543714729:AAHLRF3GyvJ9OJwhF2jaV5xDlmYgj1-4JfI" # Obtain from BotFather

# Initialize the bot
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Store group IDs in memory
group_ids = {
    "source": None,
    "target": None
}

# Set the bot owner ID
bot_owner_id = 6248131995  # Replace with your Telegram user ID

@app.on_message(filters.private & filters.user(bot_owner_id))
async def handle_pm(client, message):
    """
    Handle private messages from the bot owner to set source and target group IDs.
    """
    global group_ids

    text = message.text
    if text.startswith("/setsource"):
        try:
            group_ids["source"] = int(text.split()[1])
            await message.reply_text(f"Source group ID set to: {group_ids['source']}")
            logger.info(f"Source group ID updated to {group_ids['source']}")
        except IndexError:
            await message.reply_text("Please provide a group ID after the command.")
        except ValueError:
            await message.reply_text("Invalid group ID format. Please provide a numeric ID.")
    
    elif text.startswith("/settarget"):
        try:
            group_ids["target"] = int(text.split()[1])
            await message.reply_text(f"Target group ID set to: {group_ids['target']}")
            logger.info(f"Target group ID updated to {group_ids['target']}")
        except IndexError:
            await message.reply_text("Please provide a group ID after the command.")
        except ValueError:
            await message.reply_text("Invalid group ID format. Please provide a numeric ID.")

@app.on_message(filters.group)
async def handle_media(client, message):
    """
    Handle media messages in the source group, forwarding them to the target group
    and optionally deleting them from the source group.
    """
    if group_ids["source"] and group_ids["target"]:
        if message.chat.id == group_ids["source"] and message.media:
            try:
                # Ensure the message has the required attributes
                if message.id:  # Use message.id which should be available
                    # Forward media to target group
                    await client.forward_messages(
                        chat_id=group_ids["target"],
                        from_chat_id=group_ids["source"],
                        message_ids=message.id  # Use message.id
                    )
                    
                    # Optionally, delete the media from the source group
                    await client.delete_messages(
                        chat_id=group_ids["source"],
                        message_ids=message.id  # Use message.id
                    )

                    # Notify in the target group (optional)
                    await client.send_message(
                        group_ids["target"],
                        "Media has been forwarded and source message deleted."
                    )
                    logger.info(f"Media message {message.id} forwarded and deleted.")
                else:
                    logger.error("The message object does not have 'id'.")
            except Exception as e:
                logger.error(f"An error occurred: {e}")

# Start the bot
app.run()
