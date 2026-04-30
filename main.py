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
async def start(message: Message):
    text = (
        "Привет! 👋\n\n"
        "Я помогу с информацией по лофтам в Валенсии.\n\n"
        "Доступные команды:\n"
        "/price - узнать цены\n"
        "/location - как добраться\n"
        "/faq - частые вопросы"
    )
    await message.answer(text)


@router.message(Command("price"))
async def price(message: Message):
    await message.answer(
        "Цены зависят от месяца.\n\n"
        "Апрель: от 70€ за ночь\n"
        "Июнь: от 110€ за ночь\n\n"
        "Напишите даты, и я подскажу точнее."
    )


@router.message(Command("location"))
async def location(message: Message):
    await message.answer(
        "📍 Как добраться:\n\n"
        "Из аэропорта: метро линии 3 или 5\n"
        "Из центра: удобно на метро или автобусе\n\n"
        "Если вы на машине — подскажу парковку."
    )


@router.message(Command("faq"))
async def faq(message: Message):
    await message.answer(
        "Частые вопросы:\n\n"
        "✔ Есть ли горячая вода зимой? — Да, всегда\n"
        "✔ Шумно ли ночью? — Район спокойный\n"
        "✔ Есть ли Wi-Fi? — Да\n"
    )


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
    