from os import getenv
import asyncio

from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from dotenv import load_dotenv

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not found")

dp = Dispatcher()
router = Router()
dp.include_router(router)


@router.message()
async def hello(message):
    now = datetime.now().strftime("%H:%M:%S")

    print("-----")
    print("TIME:", now)
    print("TEXT:", message.text)
    print("FROM:", message.from_user.id)
    
    await message.answer("Hello")


async def main():
    bot = Bot(token=TOKEN)

    print("Bot started at:", datetime.now().strftime("%H:%M:%S"))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
    