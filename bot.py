from pyrogram import Client, filters
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image
import io
import numpy as np
import os

API_ID = "1474940"
API_HASH = "779e8d2b32ef76d0b7a11fb5f132a6b6"
BOT_TOKEN = "7543714729:AAHLRF3GyvJ9OJwhF2jaV5xDlmYgj1-4JfI"
UPLOAD_CHANNEL_ID = -1002184464315  # Channel to upload original media
WATERMARK_CHANNEL_ID = -1002494998139  # Channel to upload watermarked media
WATERMARK_LOGO_PATH = 'justforwardme1775345.png'  # Path to your watermark logo

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def prepare_logo():
    with Image.open(WATERMARK_LOGO_PATH).convert("RGBA") as logo:
        datas = logo.getdata()
        new_data = [
            (255, 255, 255, 0) if item[0] < 50 and item[1] < 50 and item[2] < 50 else item
            for item in datas
        ]
        logo.putdata(new_data)
        return logo

def add_watermark_to_image(image_bytes):
    with Image.open(io.BytesIO(image_bytes)).convert("RGBA") as img:
        logo = prepare_logo()
        logo = logo.resize((int(logo.width * 0.3), int(logo.height * 0.3)))
        logo_width, logo_height = logo.size
        img_width, img_height = img.size
        x = img_width - logo_width - 30
        y = img_height - logo_height - 30
        img.paste(logo, (x, y), logo)
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return output

def add_watermark_to_video(video_path):
    clip = VideoFileClip(video_path)
    logo = prepare_logo()
    logo = logo.resize((int(logo.width * 0.3), int(logo.height * 0.3)))
    logo_np = np.array(logo)
    logo_clip = ImageClip(logo_np).set_duration(clip.duration).set_pos(('left', 'center'))
    watermarked_clip = CompositeVideoClip([clip, logo_clip])
    output_path = 'watermarked_video.mp4'
    watermarked_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
    return output_path

@app.on_message(filters.channel)
async def handle_media(client, message):
    watermarked_video_path = None
    try:
        if message.chat.id == UPLOAD_CHANNEL_ID:
            if message.photo:
                photo = await message.download()
                with open(photo, 'rb') as f:
                    watermarked_image = add_watermark_to_image(f.read())
                # Send the watermarked image to the watermark channel
                await client.send_photo(chat_id=WATERMARK_CHANNEL_ID, photo=watermarked_image)
                os.remove(photo)
                
            elif message.video:
                video_file = await message.download()
                watermarked_video_path = add_watermark_to_video(video_file)
                # Send the watermarked video to the watermark channel
                with open(watermarked_video_path, 'rb') as f:
                    await client.send_video(chat_id=WATERMARK_CHANNEL_ID, video=f)
                os.remove(video_file)
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        if os.path.exists(video_file):
            os.remove(video_file)
        if watermarked_video_path and os.path.exists(watermarked_video_path):
            os.remove(watermarked_video_path)
        await message.delete()

app.run()
