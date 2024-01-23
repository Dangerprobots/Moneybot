from pyrogram import Client, filters
#from pyrogram.errors import BadRequest
import asyncio
from pyrogram import *
from pyrogram.types import *
import time

API_ID = 5282591
API_HASH = "d416fe4e323d0e2b4616fef68a8ddd63"
SESSION= "AQBQmx8AIXG1XQQx559hEBwO5VnHexcBdOZhqzgxFkC6lBnXvYa4V9tQuGkvzjna1MKwLUIl7tlC4HAEz_AHGwdoXZ0deHbu36eYUwVV2xuQy6bqukBKOCqS9c5ewFi74hWxrjiCR2jJo9rluQnhXlw60x9x6q30SZuqChUIOpjnK1yAdqrUNtFxszXNbCqytLLsfHGbjrJhCPNJUszPKyMbl4v-BLdCOtM9CrqZWbD6sakY02-hCSakF7WH1kbbpej1OUHufO2juIvQivt6aXSwXM-_EzjHkIcotRYjNIXDh0BZHQfZZ7_pnHOrvx49ad_A5ATQqPnSj5HvCyhR1vttnl6ukAAAAABBI27eAA"
TIME = 5
LOG = -1002025718840
GROUPS= -1002120547379

User = Client(
    name="user-account",
    session_string=SESSION,
    api_id=API_ID,
    api_hash=API_HASH,
    workers=300
)


@User.search_message(filters.chat(GROUPS) | filters.photo | filters.video | filters.document,limit=20)
async def delete(user,message):
    try:
        await asyncio.sleep(3)
        await message.forward(LOG)
        await asyncio.sleep(TIME)
        await message.delete()
    except Exception as e:
        print(e)


User.run()
