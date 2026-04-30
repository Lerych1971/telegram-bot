from os import getenv
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from dotenv import load_dotenv


# --- TEXTS ---
TEXTS = {
    "ru": {
        "start": "Привет! 👋\nЯ помогу с информацией по лофтам в Валенсии.\n\nКоманды:\n/price\n/location\n/faq",
        "price": "Апрель: от 70€\nИюнь: от 110€",
        "location": "Метро 3 или 5 из аэропорта",
        "faq": "WiFi есть, вода есть, тихо"
    },
    "es": {
        "start": "¡Hola! 👋\nInformación sobre lofts en Valencia.\n\nComandos:\n/price\n/location\n/faq",
        "price": "Abril: desde 70€\nJunio: desde 110€",
        "location": "Metro líneas 3 o 5",
        "faq": "WiFi sí, agua sí, tranquilo"
    }
}


# --- CONFIG ---
load_dotenv()
TOKEN = getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not found")

DEFAULT_LANG = "es"


# --- ROUTER ---
dp = Dispatcher()
router = Router()
dp.include_router(router)


# --- HANDLERS ---
@router.message(Command("start"))
async def start(message: Message):
    await message.answer(TEXTS[DEFAULT_LANG]["start"])


@router.message(Command("price"))
async def price(message: Message):
    await message.answer(TEXTS[DEFAULT_LANG]["price"])


@router.message(Command("location"))
async def location(message: Message):
    await message.answer(TEXTS[DEFAULT_LANG]["location"])


@router.message(Command("faq"))
async def faq(message: Message):
    await message.answer(TEXTS[DEFAULT_LANG]["faq"])


@router.message()
async def fallback(message: Message):
    await message.answer("Use /start")


# --- MAIN ---
async def main():
    bot = Bot(token=TOKEN)

    print("Bot started at:", datetime.now().strftime("%H:%M:%S"))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())