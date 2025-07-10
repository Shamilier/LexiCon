from aiogram import Router, types
from aiogram.filters import Command
from database import get_user_words_test

router = Router()

@router.message(Command("my_words"))
async def my_words_handler(message: types.Message):
    user_id = message.from_user.id
    words = await get_user_words_test(user_id)

    if not words:
        await message.answer("У тебя пока нет сохранённых слов. Отправь слово, чтобы я его перевёл и запомнил.")
        return

    lines = []
    lang_emojis = {
    'en': '🇬🇧',
    'fr': '🇫🇷',
    'de': '🇩🇪',
    'zh-CN': '🇨🇳'
}

    for ru, foreign, lang_code in words:
        flag = lang_emojis.get(lang_code, '')
        lines.append(f"🔹 {flag} {ru} ↔ {foreign}")

    response = "\n".join(lines[:30])
    await message.answer(response)