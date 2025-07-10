from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database import create_user_if_not_exists, save_user_language
from aiogram.types import ReplyKeyboardRemove

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await create_user_if_not_exists(message.from_user.id)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇬🇧 Английский"), KeyboardButton(text="🇫🇷 Французский")],
            [KeyboardButton(text="🇩🇪 Немецкий"), KeyboardButton(text="🇨🇳 Китайский")],
        ],
        resize_keyboard=True
    )
    await message.answer("Привет! Выбери язык для изучения:", reply_markup=kb)

import asyncio

@router.message(lambda msg: msg.text in ["🇬🇧 Английский", "🇫🇷 Французский", "🇩🇪 Немецкий", "🇨🇳 Китайский"])
async def language_selected(message: types.Message):
    language_map = {
        "🇬🇧 Английский": "en",
        "🇫🇷 Французский": "fr",
        "🇩🇪 Немецкий": "de",
        "🇨🇳 Китайский": "zh-CN"
    }
    lang_code = language_map[message.text]
    await save_user_language(message.from_user.id, lang_code)

    await message.answer(
        f"Отлично! Язык {message.text} выбран.",
        reply_markup=ReplyKeyboardRemove()
    )

    # ⏳ Небольшие паузы между сообщениями
    await asyncio.sleep(0.8)
    await message.answer(
        "Этот бот — твой личный помощник по изучению слов 💬.\n\n"
        "Он помогает сохранять незнакомые слова и повторять их в удобной форме."
    )

    await asyncio.sleep(3.5)
    await message.answer(
        "Чтобы сохранить незнакомое слово, просто отправь его боту.\n"
        "Он переведёт и добавит его в твой словарь 📚."
    )

    await asyncio.sleep(4)
    await message.answer(
        "Ты можешь тренироваться и расширять словарный запас с помощью встроенных команд:"
    )

    await asyncio.sleep(1.5)
    await message.answer(
        "📖 Команды:\n\n"
        "🔁 /learn — учить свои слова\n"
        "🧩 /sets — новые слова по уровням\n"
        "🧠 /test — проверка знаний\n"
        "📋 /my_words — список твоих слов",
        parse_mode="HTML"
    )