from os import getenv
import asyncio

from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from dotenv import load_dotenv

TEXTS = {
    "ru": {
        "start": "Привет! 👋\nЯ помогу с информацией по лофтам в Валенсии.\n\nДоступные команды:\n/price\n/location\n/faq",
        "price": "Цены зависят от месяца.\n\nАпрель: от 70€\nИюнь: от 110€\n\nНапишите даты, и я подскажу точнее.",
        "location": "📍 Как добраться:\n\nИз аэропорта: метро линии 3 или 5\nИз центра: метро или автобус\n\nЕсли вы на машине, подскажу парковку.",
        "faq": "Частые вопросы:\n\n✔ Есть ли горячая вода зимой? Да\n✔ Шумно ли ночью? Район спокойный\n✔ Есть ли WiFi? Да"
    },
    "es": {
        "start": "¡Hola! 👋\nTe ayudaré con información sobre los lofts en Valencia.\n\nComandos:\n/price\n/location\n/faq",
        "price": "Los precios dependen del mes.\n\nAbril: desde 70€\nJunio: desde 110€",
        "location": "📍 Cómo llegar:\n\nDesde el aeropuerto: metro líneas 3 o 5\nDesde el centro: metro o autobús",
        "faq": "Preguntas frecuentes:\n\n✔ ¿Hay agua caliente? Sí\n✔ ¿Es ruidoso? No\n✔ ¿Hay WiFi? Sí"
    }
}

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not found")

DEFAULT_LANG = "ru"

dp = Dispatcher()
router = Router()
dp.include_router(router)


from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
from os import getenv
import asyncio

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

dp = Dispatcher()
router = Router()
dp.include_router(router)


@router.message(Command("start"))
async def start(message):
    await message.answer(TEXTS[DEFAULT_LANG]["start"])


@router.message(Command("price"))
async def price(message):
    await message.answer(TEXTS[DEFAULT_LANG]["price"])


@router.message(Command("location"))
async def location(message):
    await message.answer(TEXTS[DEFAULT_LANG]["location"])


@router.message(Command("faq"))
async def faq(message):
    await message.answer(TEXTS[DEFAULT_LANG]["faq"])


@router.message()
async def fallback(message: Message):
    await message.answer(
        "Я пока не всё понимаю 🙂\n"
        "Попробуйте команды: /price, /location, /faq"
    )


async def main():
    bot = Bot(token=TOKEN)
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


async def main():
    bot = Bot(token=TOKEN)

    print("Bot started at:", datetime.now().strftime("%H:%M:%S"))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
    