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
        "price": "Цены зависят от месяца. \n\nМай: от 80€\nИюнь: от 110€\nИюль: от 130€",
        "location": "Метро 3 или 5 из аэропорта",
        "faq": "WiFi есть, вода есть, тихо",
        "fallback": "Не совсем понял 🤔\nПопробуйте написать про цену, дорогу или удобства."
    },
    "es": {
        "start": "¡Hola! 👋\nInformación sobre lofts en Valencia.\n\nComandos:\n/price\n/location\n/faq",
        "price": "Los precios dependen del mes.\n\nMayo: desde 80€\nJunio: desde 110€\nJulio: desde 130€",
        "location": "Metro líneas 3 o 5",
        "faq": "WiFi sí, agua sí, tranquilo",
        "fallback": "No entendí 🤔\nEscribe sobre precio, ubicación o comodidades."
    },
    "en": {
        "start": "Hello! 👋\nI can help you with lofts in Valencia.\n\nCommands:\n/price\n/location\n/faq",
        "price": "Prices depend on the month.\n\nMay: from 80€\nJune: from 110€\nJuly: from 130€",
        "location": "📍 How to get there:\n\nFrom airport: metro lines 3 or 5\nFrom city center: metro or bus\n\nIf you have a car, I’ll suggest parking.",
        "faq": "FAQ:\n\n✔ Hot water in winter? Yes\n✔ Noisy at night? Quiet area\n✔ WiFi? Yes",
        "fallback": "I didn’t understand 🤔\nTry asking about price, location or amenities."    }
}

PRICES = {
    "may": 80,
    "june": 110,
    "july": 130
}

user_state = {}

MONTH_NAMES = {
    "ru": {
        "may": "мае",
        "june": "июне",
        "july": "июле"
    },
    "es": {
        "may": "mayo",
        "june": "junio",
        "july": "julio"
    },
    "en": {
        "may": "May",
        "june": "June",
        "july": "July"
    }
}

import re

def detect_month(text: str):
    text = text.lower()

    if any(w in text for w in ["май", "мая", "mayo", "may"]):
        return "may"

    if any(w in text for w in ["июн", "июня", "junio", "june"]):
        return "june"

    if any(w in text for w in ["июл", "июля", "julio", "july"]):
        return "july"

    return None


def detect_nights(text: str):
    match = re.search(r"\d+", text)
    if match:
        return int(match.group())
    return None

def detect_range(text: str):
    import re

    text = text.lower()

    # ищем 2 числа
    numbers = re.findall(r"\d{1,2}", text)

    if len(numbers) >= 2:
        start = int(numbers[0])
        end = int(numbers[1])

        if end > start:
            return end - start

    return None

async def start_booking(message, lang, nights, month_name, total):
    user_id = message.from_user.id

    user_state[user_id] = {
        "step": "people",
        "nights": nights,
        "month": month_name,
        "total": total,
        "lang": lang
    }

    if lang == "ru":
        await message.answer(
            f"На этот период стоимость примерно {total}€ за 1 человека.\n\n"
            f"Сколько будет человек?"
        )

    elif lang == "es":
        await message.answer(
            f"Para este período el precio es aproximadamente {total}€ por persona.\n\n"
            f"¿Cuántas personas?"
        )

    else:
        await message.answer(
            f"For this period the price is about {total}€ per person.\n\n"
            f"How many people?"
        )


# --- CONFIG ---
load_dotenv()
TOKEN = getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not found")

ADMIN_ID = int(getenv("ADMIN_ID"))

DEFAULT_LANG = "es"
def detect_lang(text: str):
    text = text.lower()

    # испанский
    if any(word in text for word in ["precio", "mayo", "junio", "julio", "hola", "metro"]):
        return "es"

    # английский
    if any(word in text for word in ["price", "may", "june", "july", "hello", "how"]):
        return "en"

    # русский (расширили формы)
    if any(word in text for word in [
        "цена",
        "май", "мая",
        "июнь", "июня",
        "июль", "июля",
        "привет",
        "метро"
    ]):
        return "ru"

    return DEFAULT_LANG


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
    lang = detect_lang(message.text or "")
    bot = message.bot

    user_id = message.from_user.id

    if user_id in user_state:
        state = user_state[user_id]
        lang = state["lang"]

        # шаг 1 — количество людей
        if state["step"] == "people":
            try:
                people = int(message.text)
            except:
                if lang == "ru":
                    await message.answer("Введите число, например 2")
                elif lang == "es":
                    await message.answer("Ingrese un número, por ejemplo 2")
                else:
                    await message.answer("Enter a number, for example 2")
                return

            state["people"] = people

            # пересчёт суммы
            total = state["total"] * people
            state["total"] = total

            state["step"] = "parking"

            if lang == "ru":
                await message.answer(f"Итого {total}€.\nНужна парковка? (да/нет)")
            elif lang == "es":
                await message.answer(f"Total {total}€.\n¿Necesita parking? (sí/no)")
            else:
                await message.answer(f"Total {total}€.\nDo you need parking? (yes/no)")

            return

        # шаг 2 — парковка
        if state["step"] == "parking":
            state["parking"] = message.text
            state["step"] = "contact"

            if lang == "ru":
                await message.answer("Оставьте ваш телефон или WhatsApp")
            elif lang == "es":
                await message.answer("Deje su teléfono o WhatsApp")
            else:
                await message.answer("Leave your phone or WhatsApp")
            return

        # шаг 3 — контакт
        if state["step"] == "contact":
            state["contact"] = message.text

            lang_names = {
                "ru": "ruso",
                "es": "español",
                "en": "inglés"
            }

            lang_label = lang_names.get(state["lang"], "unknown")

            parking_raw = state["parking"].lower()

            if parking_raw in ["да", "yes", "sí", "si"]:
                parking = "sí"
            elif parking_raw in ["нет", "no"]:
                parking = "no"
            else:
                parking = parking_raw
            
            text = (
                f"📥 NUEVA RESERVA\n\n"
                f"Idioma: {lang_label}\n\n"
                f"📅 Mes: {state['month']}\n"
                f"🌙 Noches: {state['nights']}\n"
                f"💶 Total: {state['total']}€\n"
                f"👥 Personas: {state['people']}\n"
                f"🚗 Parking: {parking}\n"
                f"📞 Contacto: {state['contact']}"
            )   

            await bot.send_message(ADMIN_ID, text)

            lang = state["lang"]

            if lang == "ru":
                await message.answer("Спасибо! Мы свяжемся с вами 👍")
            elif lang == "es":
                await message.answer("¡Gracias! Nos pondremos en contacto 👍")
            else:
                await message.answer("Thanks! We will contact you 👍")

            del user_state[user_id]
            return

    month = detect_month(text)
    nights = detect_nights(text)
    range_nights = detect_range(text)

    if month and range_nights:
        price_per_night = PRICES.get(month)
        total = price_per_night * range_nights
        month_name = MONTH_NAMES[lang][month]

        await start_booking(message, lang, range_nights, month_name, total)
        return
    
    if month and nights:
        price_per_night = PRICES.get(month)
        total = price_per_night * nights
        month_name = MONTH_NAMES[lang][month]

        await start_booking(message, lang, nights, month_name, total)
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
    lang = detect_lang(message.text or "")
    await message.answer(TEXTS[lang]["fallback"])
    


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