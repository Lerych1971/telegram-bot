from os import getenv
import asyncio
import re
import traceback
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import ErrorEvent, Message

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import ReplyKeyboardRemove

from dotenv import load_dotenv
from openai import OpenAI


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

GREETING_PHRASES = frozenset({
    "привет", "здравствуйте", "hello", "hi", "hola",
})

BOOKING_SUBSTRINGS = (
    "забронировать", "бронь", "снять",
    "reserva", "booking", "reserve",
)

RU_PRICE_SUBSTRINGS = ("цена", "сто", "апрел", "июн")
ES_PRICE_SUBSTRINGS = ("precio", "abril", "junio")

LOCATION_SUBSTRINGS = ("location", "ubicacion", "ubicación", "адрес")
FAQ_SUBSTRINGS = ("faq", "wifi", "wi-fi")

PARKING_YES = frozenset({"да", "yes", "sí", "si"})
PARKING_NO = frozenset({"нет", "no"})

YES_NO_KEYBOARDS = {
    "ru": ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
        resize_keyboard=True
    ),
    "es": ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Sí"), KeyboardButton(text="No")]],
        resize_keyboard=True
    ),
    "en": ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Yes"), KeyboardButton(text="No")]],
        resize_keyboard=True
    )
}

PRICES = {
    "may": 80,
    "june": 110,
    "july": 130
}

user_state = {}

dialog_context = {}

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


def sanitize_dialog_messages(msgs):
    if not isinstance(msgs, list):
        return []
    out = []
    for m in msgs:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant"):
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        out.append({"role": role, "content": content})
    return out


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
    text = text.lower()
    numbers = re.findall(r"\d{1,2}", text)

    if len(numbers) >= 2:
        start = int(numbers[0])
        end = int(numbers[1])

        if end > start:
            return end - start

    return None


def is_booking_intent(text: str) -> bool:
    t = text.lower()
    if any(s in t for s in BOOKING_SUBSTRINGS):
        return True
    return bool(re.search(r"(?<![a-z0-9])book(?![a-z])", t))


def detect_intent(text: str) -> str:
    stripped = text.strip()
    tl = text.lower()

    if stripped in GREETING_PHRASES:
        return "greeting"
    if is_booking_intent(tl):
        return "booking"
    if any(s in tl for s in RU_PRICE_SUBSTRINGS) or any(
        s in tl for s in ES_PRICE_SUBSTRINGS
    ):
        return "price"
    if any(s in tl for s in LOCATION_SUBSTRINGS):
        return "location"
    if any(s in tl for s in FAQ_SUBSTRINGS):
        return "faq"
    return "ai"


AI_REPLY_FALLBACK = "Извините, я не смог ответить."


def ask_ai(text, user_id):
    preview = text if len(text) <= 200 else text[:200] + "…"
    print(f"[pipeline] OpenAI request user_id={user_id} text_preview={preview!r}")
    try:
        raw_hist = dialog_context.get(user_id, [])
        history = sanitize_dialog_messages(
            raw_hist if isinstance(raw_hist, list) else []
        )

        messages = [
            {
                "role": "system",
                "content": (
                    f"""
                        You are assistant for loft rentals in Valencia.

                        Use this information:

                        {KNOWLEDGE}

                        Reply shortly and naturally.
                        Reply in the same language as the user.
                        Do not invent services or features.
                        """
                ),
            }
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": text})

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.4,
            messages=messages,
            max_tokens=120,
        )

        if response is None:
            print("[pipeline] OpenAI response diagnostic: response is None")
            return AI_REPLY_FALLBACK

        choices = getattr(response, "choices", None)
        if not choices:
            print(
                "[pipeline] OpenAI response diagnostic: "
                "response.choices missing or empty"
            )
            return AI_REPLY_FALLBACK

        choice = choices[0]
        if choice is None:
            print("[pipeline] OpenAI response diagnostic: response.choices[0] is None")
            return AI_REPLY_FALLBACK

        msg = getattr(choice, "message", None)
        if msg is None:
            print(
                "[pipeline] OpenAI response diagnostic: "
                "choice.message is missing or None"
            )
            return AI_REPLY_FALLBACK

        content = getattr(msg, "content", None)
        if content is None or (isinstance(content, str) and not content.strip()):
            print(
                "[pipeline] OpenAI response diagnostic: "
                "choice.message.content missing, None, or empty/whitespace"
            )
            return AI_REPLY_FALLBACK

        ai_text = content

        out_preview = ai_text if len(ai_text) <= 200 else ai_text[:200] + "…"
        print(
            f"[pipeline] OpenAI response user_id={user_id} content_preview={out_preview!r}"
        )

        hist = dialog_context.get(user_id)
        if not isinstance(hist, list):
            hist = []
        hist = sanitize_dialog_messages(hist)
        hist.append({"role": "user", "content": text})
        hist.append({"role": "assistant", "content": ai_text})
        dialog_context[user_id] = hist[-10:]

        return ai_text

    except Exception as e:
        print("[pipeline] exception caught in ask_ai")
        traceback.print_exception(type(e), e, e.__traceback__)
        return AI_REPLY_FALLBACK


async def start_booking(message, lang, nights, month_name, total, dates_text):
    user_id = message.from_user.id
    print(
        "[pipeline] booking flow: start_booking "
        f"user_id={user_id} nights={nights} month_name={month_name!r} total={total}"
    )

    user_state[user_id] = {
        "step": "people",
        "nights": nights,
        "month": month_name,
        "total": total,
        "lang": lang,
        "user_dates": dates_text
    }

    if lang == "ru":
        await safe_answer(
            message,
            f"На этот период стоимость примерно {total}€ за 1 человека.\n\n"
            f"Сколько будет человек?",
        )

    elif lang == "es":
        await safe_answer(
            message,
            f"Para este período el precio es aproximadamente {total}€ por persona.\n\n"
            f"¿Cuántas personas?",
        )

    else:
        await safe_answer(
            message,
            f"For this period the price is about {total}€ per person.\n\n"
            f"How many people?",
        )

    print("[pipeline] telegram answer sent (booking quote)")


# --- CONFIG ---
load_dotenv()

with open(
    Path(__file__).resolve().parent / "knowledge.txt",
    "r",
    encoding="utf-8",
) as _knowledge_file:
    KNOWLEDGE = _knowledge_file.read()

TOKEN = getenv("BOT_TOKEN")
OPENAI_API_KEY = getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


if not TOKEN:
    raise ValueError("BOT_TOKEN not found")

ADMIN_ID = int(getenv("ADMIN_ID"))

DEFAULT_LANG = "es"


def detect_lang(text: str):
    text = text.lower()

    if any(word in text for word in ["precio", "mayo", "junio", "julio", "hola", "metro"]):
        return "es"

    if any(word in text for word in ["price", "may", "june", "july", "hello", "how"]):
        return "en"

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


async def safe_answer(message: Message, text: str, **kwargs):
    preview = text if len(text) <= 200 else text[:200] + "…"
    print(
        "[pipeline] safe_answer: sending "
        f"chat_id={message.chat.id} len={len(text)} preview={preview!r} kwargs={list(kwargs)}"
    )
    try:
        await message.answer(text, **kwargs)
        print("[pipeline] telegram answer sent (safe_answer ok)")
    except Exception as e:
        print("[pipeline] safe_answer: Telegram API exception")
        traceback.print_exception(type(e), e, e.__traceback__)


# --- ROUTER ---
dp = Dispatcher()
router = Router()
dp.include_router(router)


@dp.errors()
async def global_error_handler(event: ErrorEvent):
    exc = event.exception
    print("[pipeline] exception caught (global error handler)")
    traceback.print_exception(type(exc), exc, exc.__traceback__)


# --- HANDLERS ---
@router.message(Command("start"))
async def start(message: Message):
    lang = detect_lang(message.text or "")
    await safe_answer(message, TEXTS[lang]["start"])


@router.message(Command("price"))
async def price(message: Message):
    lang = detect_lang(message.text or "")
    await safe_answer(message, TEXTS[lang]["price"])


@router.message(Command("location"))
async def location(message: Message):
    lang = detect_lang(message.text or "")
    await safe_answer(message, TEXTS[lang]["location"])


@router.message(Command("faq"))
async def faq(message: Message):
    lang = detect_lang(message.text or "")
    await safe_answer(message, TEXTS[lang]["faq"])


@router.message()
async def handle_text(message: Message):
    bot = message.bot
    user_id = message.from_user.id
    print(
        "[pipeline] message received "
        f"user_id={user_id} chat_id={message.chat.id} "
        f"content_type={message.content_type}"
    )

    if message.text is None:
        print("[pipeline] intent detection: non-text message, prompt user for text")
        await safe_answer(message, "Пожалуйста, отправьте текстовое сообщение.")
        print("[pipeline] telegram answer sent (text-only prompt)")
        return

    text = message.text.lower()
    lang = detect_lang(message.text or "")

    if user_id in user_state:
        state = user_state[user_id]
        lang = state["lang"]
        print(
            "[pipeline] booking flow: active session "
            f"user_id={user_id} step={state['step']!r}"
        )

        if state["step"] == "people":
            try:
                people = int(message.text)
            except Exception:
                print(
                    "[pipeline] booking flow: invalid people count "
                    f"user_id={user_id} raw={message.text!r}"
                )
                if lang == "ru":
                    await safe_answer(message, "Введите число, например 2")
                elif lang == "es":
                    await safe_answer(message, "Ingrese un número, por ejemplo 2")
                else:
                    await safe_answer(message, "Enter a number, for example 2")
                print("[pipeline] telegram answer sent (booking invalid people)")
                return

            state["people"] = people

            total = state["total"] * people
            state["total"] = total

            state["step"] = "parking"

            if lang == "ru":
                await safe_answer(
                    message,
                    f"Итого {total}€.\nНужна парковка?",
                    reply_markup=YES_NO_KEYBOARDS[lang],
                )
            elif lang == "es":
                await safe_answer(
                    message,
                    f"Total {total}€.\n¿Necesita parking?",
                    reply_markup=YES_NO_KEYBOARDS[lang],
                )
            else:
                await safe_answer(
                    message,
                    f"Total {total}€.\nDo you need parking?",
                    reply_markup=YES_NO_KEYBOARDS[lang],
                )

            print("[pipeline] telegram answer sent (booking parking question)")
            return

        if state["step"] == "parking":
            state["parking"] = message.text
            state["step"] = "contact"

            if lang == "ru":
                await safe_answer(
                    message,
                    "Оставьте ваш телефон или WhatsApp",
                    reply_markup=ReplyKeyboardRemove(),
                )
            elif lang == "es":
                await safe_answer(
                    message,
                    "Deje su teléfono o WhatsApp",
                    reply_markup=ReplyKeyboardRemove(),
                )
            else:
                await safe_answer(
                    message,
                    "Leave your phone or WhatsApp",
                    reply_markup=ReplyKeyboardRemove(),
                )
            print("[pipeline] telegram answer sent (booking ask contact)")
            return

        if state["step"] == "contact":
            print(f"[pipeline] booking flow: contact step user_id={user_id}")
            state["contact"] = message.text

            raw = state["user_dates"]

            numbers = re.findall(r"\d{1,2}", raw)

            if len(numbers) >= 2:
                d1, d2 = numbers[0], numbers[1]
                month_key = detect_month(state["user_dates"])
                month = MONTH_NAMES["es"].get(month_key, state["month"])
                dates_es = f"del {d1} al {d2} de {month}"
            else:
                dates_es = raw

            lang_names = {
                "ru": "ruso",
                "es": "español",
                "en": "inglés"
            }

            lang_label = lang_names.get(state["lang"], "unknown")

            parking_raw = state["parking"].lower()

            if parking_raw in PARKING_YES:
                parking = "sí"
            elif parking_raw in PARKING_NO:
                parking = "no"
            else:
                parking = parking_raw

            admin_text = (
                f"📥 NUEVA RESERVA\n\n"
                f"Idioma: {lang_label}\n\n"
                f"📅 Fechas: {dates_es}\n"
                f"🌙 Noches: {state['nights']}\n"
                f"💶 Total: {state['total']}€\n"
                f"👥 Personas: {state['people']}\n"
                f"🚗 Parking: {parking}\n"
                f"📞 Contacto: {state['contact']}"
            )

            await bot.send_message(ADMIN_ID, admin_text)
            print(
                "[pipeline] booking flow: admin reservation message sent "
                f"admin_id={ADMIN_ID}"
            )

            lang = state["lang"]

            if lang == "ru":
                await safe_answer(message, "Спасибо! Мы свяжемся с вами 👍")
            elif lang == "es":
                await safe_answer(message, "¡Gracias! Nos pondremos en contacto 👍")
            else:
                await safe_answer(message, "Thanks! We will contact you 👍")

            del user_state[user_id]
            print("[pipeline] telegram answer sent (booking complete)")
            return

    month = detect_month(text)
    nights = detect_nights(text)
    range_nights = detect_range(text)
    dates_text = text
    intent = detect_intent(text)
    print(
        "[pipeline] intent detection "
        f"month={month!r} nights={nights!r} range_nights={range_nights!r} "
        f"lang={lang!r} intent={intent!r}"
    )

    if intent == "booking":
        if month and range_nights:
            price_per_night = PRICES.get(month)
            total = price_per_night * range_nights
            month_name = MONTH_NAMES[lang][month]

            print("[pipeline] booking flow: range-based quote -> start_booking")
            await start_booking(
                message, lang, range_nights, month_name, total, dates_text
            )
            return

        if month and nights:
            price_per_night = PRICES.get(month)
            total = price_per_night * nights
            month_name = MONTH_NAMES[lang][month]

            print("[pipeline] booking flow: nights-based quote -> start_booking")
            await start_booking(message, lang, nights, month_name, total, dates_text)
            return

        print(
            "[pipeline] intent router: booking intent without dates -> AI fallback"
        )

    if intent == "greeting":
        print("[pipeline] intent router: greeting -> start text")
        await safe_answer(message, TEXTS[lang]["start"])
        print("[pipeline] telegram answer sent (greeting)")
        return

    if intent == "price":
        if any(s in text for s in ES_PRICE_SUBSTRINGS):
            print("[pipeline] intent router: price (es keywords)")
            await safe_answer(message, TEXTS["es"]["price"])
        else:
            print("[pipeline] intent router: price (lang from detect_lang)")
            await safe_answer(message, TEXTS[lang]["price"])
        print("[pipeline] telegram answer sent (price)")
        return

    if intent == "location":
        print("[pipeline] intent router: location")
        await safe_answer(message, TEXTS[lang]["location"])
        print("[pipeline] telegram answer sent (location)")
        return

    if intent == "faq":
        print("[pipeline] intent router: faq")
        await safe_answer(message, TEXTS[lang]["faq"])
        print("[pipeline] telegram answer sent (faq)")
        return

    print(f"[pipeline] AI fallback user_id={user_id}")
    ai_answer = ask_ai(text, user_id)

    print(f"[pipeline] AI fallback result preview={ai_answer[:200]!r}")

    if ai_answer:
        await safe_answer(message, ai_answer)
        print("[pipeline] telegram answer sent (AI reply)")
        return

    lang = detect_lang(message.text or "")
    print("[pipeline] intent detection: empty AI reply -> fallback text")
    await safe_answer(message, TEXTS[lang]["fallback"])
    print("[pipeline] telegram answer sent (fallback)")


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
