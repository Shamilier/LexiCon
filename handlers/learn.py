

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import random, asyncio
from database import get_user_words_learn, delete_word_from_db, mark_word_as_known

def escape_md(text: str) -> str:
    """
    Экранирует спецсимволы MarkdownV2 согласно документации Telegram
    """
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

router = Router()

class LearnState(StatesGroup):
    active = State()

@router.message(F.text.in_(["/learn", "🔁 Повторение слов"]))
async def start_learn(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    words = await get_user_words_learn(user_id)

    if not words:
        await message.answer("У тебя пока нет слов для повторения. Добавь сначала новое слово.")
        return

    await state.set_state(LearnState.active)
    await state.update_data(words=words, last_word=None)

    msg = await send_next_word(message, state, edit=False)
    if msg:
        await state.update_data(current_message_id=msg.message_id)

async def send_next_word(event: types.Message | types.CallbackQuery, state: FSMContext, edit: bool = True):
    # Унификация: получить объект message
    message = event.message if isinstance(event, types.CallbackQuery) else event
    bot = message.bot

    data = await state.get_data()
    words = data.get("words", [])
    last_word = data.get("last_word")
    current_message_id = data.get("current_message_id")

    if not words:
        await message.answer("Слова закончились. Молодец! 🎉")
        await state.clear()
        return

    # Выбор нового слова
    word = random.choice(words)
    while word == last_word and len(words) > 1:
        word = random.choice(words)

    ru, foreign, lang_code = word
    show_ru = random.choice([True, False])
    question_raw = ru if show_ru else foreign
    answer_raw = foreign if show_ru else ru

    question = escape_md(question_raw)
    answer = escape_md(answer_raw)

    progress_frames = [
        "[░░░░░░░░░░]",
        "[█░░░░░░░░░]",
        "[██░░░░░░░░]",
        "[███░░░░░░░]",
        "[████░░░░░░]",
        "[█████░░░░░]",
        "[██████░░░░]",
        "[███████░░░]",
        "[████████░░]",
        "[█████████░]",
        "[██████████]",
    ]

    text_base = f"📚 Повторение\n\n❓ Переведи:\n{'🇷🇺' if show_ru else '🌍'} *{question}*"

    try:
        if not edit:
            sent_msg = await message.answer(
                text=f"{text_base}\n\n{progress_frames[0]}",
                parse_mode="MarkdownV2"
            )
            current_message_id = sent_msg.message_id
        else:
            sent_msg = await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=current_message_id,
                text=f"{text_base}\n\n{progress_frames[0]}",
                parse_mode="MarkdownV2"
            )
            current_message_id = sent_msg.message_id
    except Exception as e:
        print(f"[ERROR] edit_message_text (start): {e}")
        return

    await state.update_data(last_word=word, current_message_id=current_message_id)

    for frame in progress_frames[1:]:
        await asyncio.sleep(0.08)
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=current_message_id,
                text=f"{text_base}\n\n{frame}",
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            print(f"[ERROR] edit_message_text (frame): {e}")
            break

    # Показываем перевод
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выучил", callback_data="learn_known"),
            InlineKeyboardButton(text="⏭ Далее", callback_data="learn_next")
        ]
    ])

    final_text = f"📚 Повторение\n\n❓ Переведи:\n*{question}*\n\n📖 Ответ: ||{answer}||"

    await asyncio.sleep(0.2)
    try:
        sent_msg = await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=current_message_id,
            text=final_text,
            parse_mode="MarkdownV2",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"[ERROR] edit_message_text (final): {e}")
        return

    await state.update_data(current_message_id=sent_msg.message_id)
    return sent_msg

@router.callback_query(F.data == "learn_next")
async def next_word(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await send_next_word(callback, state, edit=True)

@router.callback_query(F.data == "learn_known")
async def known_word(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    word = data.get("last_word")

    if word:
        ru, foreign, lang_code = word
        await mark_word_as_known(callback.from_user.id, ru, foreign)

        # Убираем из текущего списка слов, чтобы не повторялось
        words = data.get("words", [])
        words = [w for w in words if w != word]
        await state.update_data(words=words)

    await callback.answer("Отмечено как известное")
    await send_next_word(callback, state, edit=True)

@router.message(F.text == "⛔ Остановить повторение")
async def stop_learn(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Повторение завершено. Отличная работа! 👏")