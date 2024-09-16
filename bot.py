from pyrogram import Client, filters
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip
import io
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace these with your actual values
api_id = "1474940"
api_hash = "779e8d2b32ef76d0b7a11fb5f132a6b6"
bot_token = "7543714729:AAHLRF3GyvJ9OJwhF2jaV5xDlmYgj1-4JfI"

# Initialize the bot
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Store group IDs in memory
group_ids = {
    "source": None,
    "target": None
}

# Set the bot owner ID
bot_owner_id = 6248131995

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

def add_watermark_image(input_image_path, output_image_path, watermark_text):
    """
    Add a watermark to an image.
    """
    with Image.open(input_image_path) as im:
        watermark = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark, "RGBA")
        
        # Add watermark text
        font = ImageFont.load_default()
        text_bbox = draw.textbbox((0, 0), watermark_text, font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        position = (im.size[0] - text_width - 10, im.size[1] - text_height - 10)
        draw.text(position, watermark_text, fill=(255, 255, 255, 128), font=font)
        
        watermarked = Image.alpha_composite(im.convert("RGBA"), watermark)
        # Convert to RGB before saving as JPEG
        watermarked.convert("RGB").save(output_image_path, "JPEG")

def add_watermark_video(input_video_path, output_video_path, watermark_text):
    """
    Add a watermark to a video.
    """
    def watermark_frame(frame):
        """Add watermark to each frame of the video."""
        img = Image.fromarray(frame)
        watermark = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark, "RGBA")
        
        # Add watermark text
        font = ImageFont.load_default()
        text_bbox = draw.textbbox((0, 0), watermark_text, font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        position = (img.size[0] - text_width - 10, img.size[1] - text_height - 10)
        draw.text(position, watermark_text, fill=(255, 255, 255, 128), font=font)
        
        img = Image.alpha_composite(img.convert("RGBA"), watermark)
        return img.convert("RGB")
    
    clip = VideoFileClip(input_video_path)
    watermarked_clip = clip.fl_image(watermark_frame)
    watermarked_clip.write_videofile(output_video_path, codec='libx264')

@app.on_message(filters.group)
async def handle_media(client, message):
    """
    Handle media messages in the source group, adding watermark and forwarding to the target group.
    """
    if group_ids["source"] and group_ids["target"]:
        if message.chat.id == group_ids["source"] and message.media:
            try:
                # Download the media file
                downloaded_file = await client.download_media(message, file_name="downloaded_media")
                
                if message.photo:  # Handle images
                    output_file = "watermarked_image.jpg"
                    add_watermark_image(downloaded_file, output_file, "Watermark Text")
                    await client.send_photo(group_ids["target"], photo=output_file)
                
                elif message.video:  # Handle videos
                    output_file = "watermarked_video.mp4"
                    add_watermark_video(downloaded_file, output_file, "Watermark Text")
                    await client.send_video(group_ids["target"], video=output_file)
                
                # Optionally, delete the media from the source group
                await client.delete_messages(group_ids["source"], message_ids=message.message_id)
                
                # Clean up local files
                os.remove(downloaded_file)
                os.remove(output_file)

                logger.info(f"Media message {message.id} processed and forwarded.")
            except Exception as e:
                logger.error(f"An error occurred: {e}")

# Start the bot
app.run()
