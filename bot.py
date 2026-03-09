import asyncio
import os
import json
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.types import ChatJoinRequest

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))

MAX_PER_HOUR = 5

bot = Bot(token=TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"accepted": 0, "last_reset": datetime.now().isoformat(), "queue": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

def reset_if_needed():
    global data
    now = datetime.now()
    last_reset = datetime.fromisoformat(data["last_reset"])
    if now - last_reset >= timedelta(hours=1):
        data["accepted"] = 0
        data["last_reset"] = now.isoformat()
        save_data(data)

async def log(message):
    if LOG_CHANNEL:
        await bot.send_message(LOG_CHANNEL, message)

async def has_avatar(user_id):
    photos = await bot.get_user_profile_photos(user_id)
    return photos.total_count > 0

@dp.chat_join_request()
async def handle_request(request: ChatJoinRequest):
    global data
    reset_if_needed()
    user = request.from_user

    if user.is_bot or not user.username:
        await request.decline()
        await log(f"❌ отклонён {user.full_name}")
        return

    if not await has_avatar(user.id):
        await request.decline()
        await log(f"❌ без аватарки @{user.username}")
        return

    if data["accepted"] < MAX_PER_HOUR:
        await request.approve()
        data["accepted"] += 1
        save_data(data)
        await log(f"✅ принят @{user.username}")
    else:
        data["queue"].append(user.id)
        save_data(data)
        await log(f"⏳ очередь @{user.username}")

async def process_queue():
    global data
    while True:
        reset_if_needed()
        while data["queue"] and data["accepted"] < MAX_PER_HOUR:
            user_id = data["queue"].pop(0)
            try:
                await bot.approve_chat_join_request(CHANNEL_ID, user_id)
                data["accepted"] += 1
                save_data(data)
            except:
                pass
        await asyncio.sleep(60)

async def main():
    asyncio.create_task(process_queue())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())