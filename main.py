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
    },
    "en": {
        "start": "Hello! 👋\nI can help you with lofts in Valencia.\n\nCommands:\n/price\n/location\n/faq",
        "price": "Prices depend on the month.\n\nApril: from 70€ per night\nJune: from 110€ per night\n\nSend your dates and I’ll уточнить.",
        "location": "📍 How to get there:\n\nFrom airport: metro lines 3 or 5\nFrom city center: metro or bus\n\nIf you have a car, I’ll suggest parking.",
        "faq": "FAQ:\n\n✔ Hot water in winter? Yes\n✔ Noisy at night? Quiet area\n✔ WiFi? Yes"
    }
}

PRICES = {
    "april": 70,
    "june": 110
}

MONTH_NAMES = {
    "ru": {
        "april": "апреле",
        "june": "июне"
    },
    "es": {
        "april": "abril",
        "june": "junio"
    },
    "en": {
        "april": "April",
        "june": "June"
    }
}

import re

def detect_month(text: str):
    text = text.lower()

    if any(w in text for w in ["апрел", "abril", "april"]):
        return "april"

    if any(w in text for w in ["июн", "junio", "june"]):
        return "june"

    return None


def detect_nights(text: str):
    match = re.search(r"\d+", text)
    if match:
        return int(match.group())
    return None



# --- CONFIG ---
load_dotenv()
TOKEN = getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not found")

DEFAULT_LANG = "ru"
def detect_lang(text: str):
    text = text.lower()

    if any(word in text for word in ["precio", "abril", "junio", "hola", "metro"]):
        return "es"

    if any(word in text for word in ["price", "april", "june", "hello", "how"]):
        return "en"

    return "ru"


# --- ROUTER ---
dp = Dispatcher()
router = Router()
dp.include_router(router)


# --- HANDLERS ---
@router.message(Command("start"))
async def start(message: Message):
    lang = detect_lang(message.text or "")
    await message.answer(TEXTS[lang]["start"])


@router.message(Command("price"))
async def price(message: Message):
    lang = detect_lang(message.text or "")
    await message.answer(TEXTS[lang]["price"])


@router.message(Command("location"))
async def location(message: Message):
    lang = detect_lang(message.text or "")
    await message.answer(TEXTS[lang]["location"])


@router.message(Command("faq"))
async def faq(message: Message):
    lang = detect_lang(message.text or "")
    await message.answer(TEXTS[lang]["faq"])


@router.message()
async def handle_text(message: Message):
    text = message.text.lower()
    lang = detect_lang(text)
    month = detect_month(text)
    nights = detect_nights(text)

    if month and nights:
        price_per_night = PRICES.get(month)
        total = price_per_night * nights
        month_name = MONTH_NAMES[lang][month]

        if lang == "ru":
            await message.answer(f"{nights} ночи в {month_name} будут стоить примерно {total}€")
        elif lang == "es":
            await message.answer(f"{nights} noches en {month_name} costarán aproximadamente {total}€")
        else:
            await message.answer(f"{nights} nights in {month_name} will cost about {total}€")

        return

    # приветствие
    if any(word in text for word in ["привет", "здрав", "hello", "hi", "hola"]):
        await message.answer(TEXTS[lang]["start"])
        return
    
    # цена
    if "цена" in text or "сто" in text or "апрел" in text or "июн" in text:
        await message.answer(TEXTS[lang]["price"])
        return

    if "precio" in text or "abril" in text or "junio" in text:
        await message.answer(TEXTS["es"]["price"])
        return

    # как добраться
    if "как добраться" in text or "аэропорт" in text or "метро" in text:
        await message.answer(TEXTS[lang]["location"])
        return

    if "como llegar" in text or "aeropuerto" in text or "metro" in text:
        await message.answer(TEXTS["es"]["location"])
        return

    # вопросы
    if "горяч" in text or "шум" in text or "wifi" in text:
        await message.answer(TEXTS[lang]["faq"])
        return

    if "wifi" in text or "ruido" in text or "agua" in text:
        await message.answer(TEXTS["es"]["faq"])
        return

    # если не поняли
    await message.answer(
        "Не совсем понял 🤔\nПопробуйте написать про цену, дорогу или удобства."
    )


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