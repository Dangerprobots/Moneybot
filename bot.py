from pyrogram import Client, filters

# Replace these with your actual values
api_id = "1474940"       # Obtain from https://my.telegram.org/
api_hash = "779e8d2b32ef76d0b7a11fb5f132a6b6"   # Obtain from https://my.telegram.org/
bot_token = "7543714729:AAHLRF3GyvJ9OJwhF2jaV5xDlmYgj1-4JfI" # Obtain from BotFather

# Initialize the bot
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Store the channel IDs in memory
channel_ids = {
    "source": None,
    "target": None
}

# Set the bot owner ID
bot_owner_id = 6248131995 # Replace with your Telegram user ID

@app.on_message(filters.private & filters.user(bot_owner_id))
async def handle_pm(client, message):
    global channel_ids

    # Check if the message is a command to set channel IDs
    if message.text.startswith("/setsource"):
        try:
            channel_ids["source"] = int(message.text.split()[1])
            await message.reply_text(f"Source channel ID set to: {channel_ids['source']}")
        except IndexError:
            await message.reply_text("Please provide a channel ID after the command.")
        except ValueError:
            await message.reply_text("Invalid channel ID format. Please provide a numeric ID.")

    elif message.text.startswith("/settarget"):
        try:
            channel_ids["target"] = int(message.text.split()[1])
            await message.reply_text(f"Target channel ID set to: {channel_ids['target']}")
        except IndexError:
            await message.reply_text("Please provide a channel ID after the command.")
        except ValueError:
            await message.reply_text("Invalid channel ID format. Please provide a numeric ID.")

@app.on_message(filters.group & filters.chat(lambda _, __, chat: chat.id == channel_ids["source"]))
async def handle_media(client, message):
    if channel_ids["source"] and channel_ids["target"]:
        if message.media:
            try:
                # Forward media to target channel
                await client.forward_messages(chat_id=channel_ids["target"], from_chat_id=channel_ids["source"], message_ids=message.message_id)
                
                # Optionally, delete the media from the source channel
                await client.delete_messages(chat_id=channel_ids["source"], message_ids=message.message_id)

                # Notify in the target channel (optional)
                await client.send_message(channel_ids["target"], "Media has been forwarded and source message deleted.")
            except Exception as e:
                print(f"An error occurred: {e}")

# Start the bot
app.run()
