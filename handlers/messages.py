from aiogram import Router, types
from translator import detect_language, translate_text
from database import get_user_language, save_word

router = Router()

@router.message()
async def handle_text_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip()

    user_lang = await get_user_language(user_id)
    if not user_lang:
        await message.answer("Пожалуйста, сначала выбери язык с помощью команды /start.")
        return

    source_lang = await detect_language(user_text)

    # Если текст на русском → переводим на изучаемый язык
    if source_lang == 'ru':
        ru_word = user_text
        foreign_word = await translate_text(user_text, dest_lang=user_lang)
        translated = foreign_word
    else:
        foreign_word = user_text
        ru_word = await translate_text(user_text, dest_lang='ru')
        translated = ru_word


    # Сохраняем в базу
    await save_word(
    user_id=user_id,
    ru_word=ru_word,
    foreign_word=foreign_word,
    lang_code=user_lang,  # если у тебя там язык, то надо фиксить
    source_set="user",
    status="learning"
)
    await message.answer(f"Перевод слова \"{user_text}\" → \"{translated}\"")