from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton




class TestState(StatesGroup):
    choosing_mode = State()
    choosing_count = State()
    testing = State()
    current_index = State()
    score = State()
    words = State()
    mode = State()


router = Router()
@router.message(F.text == "⛔ Прервать тест")
async def handle_stop_button(message: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    index = data.get("current_index", 0)

    from aiogram.types import ReplyKeyboardRemove
    await message.answer(
        f"🛑 Тест остановлен. Результат: {score} из {index}",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

@router.message(Command("test"))
async def start_test(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Викторина (варианты)", callback_data="mode_quiz")],
        [InlineKeyboardButton(text="✍️ Правописание (ввод)", callback_data="mode_typing")]
    ])
    await state.set_state(TestState.choosing_mode)
    await message.answer("Выбери режим теста:", reply_markup=kb)

@router.callback_query(F.data.startswith("mode_"))
async def mode_chosen(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.replace("mode_", "")
    await state.update_data(mode=mode)

    # Показать выбор количества слов
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 слов", callback_data="count_5")],
        [InlineKeyboardButton(text="10 слов", callback_data="count_10")],
        [InlineKeyboardButton(text="15 слов", callback_data="count_15")],
    ])
    await state.set_state(TestState.choosing_count)
    await callback.message.edit_text("Сколько слов ты хочешь пройти?", reply_markup=kb)


@router.callback_query(F.data.startswith("count_"))
async def count_chosen(callback: CallbackQuery, state: FSMContext):
    count = int(callback.data.replace("count_", ""))
    await state.update_data(word_limit=count)
    data = await state.get_data()

    mode = data["mode"]
    cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⛔ Прервать тест")]],
    resize_keyboard=True,
    one_time_keyboard=False 
        )

    tmp = await callback.message.answer(f"✅ Режим: {mode.upper()}, слов: {count}", reply_markup=cancel_kb)
    message_ids = data.get("message_ids", [])
    message_ids.append(tmp.message_id)


    # Вызов конкретного теста
    if mode == "quiz":
        await start_quiz(callback, state)
    elif mode == "typing":
        await start_typing(callback, state)

from database import get_user_words_test, get_random_words

async def start_quiz(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    count = data["word_limit"]

    words = await get_user_words_test(user_id)
    if len(words) < 1:
        await callback.message.answer("Недостаточно слов для теста. Добавь хотя бы одно.")
        await state.clear()
        return

    import random
    sample = random.sample(words, min(count, len(words)))  # Каждое: (ru, foreign, lang_code)
    await state.update_data(words=sample, current_index=0, score=0)

    await send_quiz_question(callback.message, state)

from database import get_random_words

async def send_quiz_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    words = data["words"]
    index = data["current_index"]

    if index >= len(words):
        await message.answer(f"🎓 Тест окончен! Ты набрал {data['score']} из {len(words)}.")
        await state.clear()
        return

    import random
    ru, foreign, lang_code = words[index]
    show_ru = random.choice([True, False])

    if show_ru:
        question_word = ru
        correct_answer = foreign
        distractor_lang = lang_code  # ищем другие foreign слова
    else:
        question_word = foreign
        correct_answer = ru
        distractor_lang = 'ru'  # ищем другие русские слова

    other_options = await get_random_words(
        exclude_word=correct_answer,
        lang_code=distractor_lang,
        limit=3
    )

    options = other_options + [correct_answer]
    random.shuffle(options)

    # Кнопки
    # Разбиваем варианты по 2 в строку
    buttons = [
        [InlineKeyboardButton(text=options[i], callback_data=f"quiz_{options[i]}"),
        InlineKeyboardButton(text=options[i + 1], callback_data=f"quiz_{options[i + 1]}")]
        for i in range(0, len(options) - 1, 2)
    ]

    await state.update_data(current_answer=correct_answer)
    await message.answer(
        f"🔸 Переведи: {question_word}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("quiz_"))
async def handle_quiz_answer(callback: CallbackQuery, state: FSMContext):
    selected = callback.data.replace("quiz_", "")
    data = await state.get_data()
    correct = data["current_answer"]
    index = data["current_index"]
    score = data["score"]

    if selected == correct:
        score += 1
        await callback.message.answer("✅ Верно!")
    else:
        await callback.message.answer(f"❌ Неверно. Правильный ответ: *{correct}*", parse_mode="Markdown")

    await state.update_data(current_index=index + 1, score=score)
    await send_quiz_question(callback.message, state)

@router.callback_query(F.data == "quiz_stop")
async def stop_quiz(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    index = data.get("current_index", 0)
    await callback.message.answer(f"🛑 Тест остановлен. Результат: {score} из {index}")
    await state.clear()





async def start_typing(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    count = data["word_limit"]

    words = await get_user_words_test(user_id)
    if len(words) < 1:
        await callback.message.answer("Недостаточно слов для теста. Добавь хотя бы одно.")
        await state.clear()
        return

    import random
    sample = random.sample(words, min(count, len(words)))  # (ru, foreign, lang_code)
    await state.update_data(words=sample, current_index=0, score=0)

    # Показываем кнопку "⛔ Прервать тест"
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    cancel_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⛔ Прервать тест")]],
        resize_keyboard=True
    )

    tmp =  await callback.message.answer("Начинаем", reply_markup=cancel_kb)
    await state.set_state(TestState.testing)
    await send_typing_question(callback.message, state)

    message_ids = data.get("message_ids", [])
    message_ids.append(tmp.message_id)


async def send_typing_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    words = data["words"]
    index = data["current_index"]

    if index >= len(words):
        from aiogram.types import ReplyKeyboardRemove

        for msg_id in data.get("message_ids", []):
            try:
                await message.bot.delete_message(message.chat.id, msg_id)
            except:
                pass

        await message.answer(
            f"🎓 Тест завершён! Ты правильно ответил на {data['score']} из {len(words)}.",
            reply_markup=ReplyKeyboardRemove()
        )
        errors = data.get("errors", [])
        if errors:
            lines = ["🔁 *Работа над ошибками:*"]
            for err in errors:
                lines.append(f"🔹*{err['question']}* \n      ❌ {err['user_input']}\n      ✅ {err['correct']}")
            await message.answer("\n".join(lines), parse_mode="Markdown")
        await state.clear()
        return

    ru, foreign, lang_code = words[index]
    await state.update_data(current_answer=foreign, current_question=ru)
    tmp = await message.answer(f"✍️ Переведи слово: \n {ru}")

    message_ids = data.get("message_ids", [])
    message_ids.append(tmp.message_id)
    await state.update_data(current_answer=foreign, message_ids=message_ids)





@router.message(TestState.testing)
async def check_typing_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ru = data["current_question"]
    correct = data["current_answer"]
    user_input = message.text.strip().lower().replace(" ", "")

    import re
    user_input = re.sub(r"[^a-zA-Zа-яА-ЯёЁ]", "", user_input)
    correct_clean = re.sub(r"[^a-zA-Zа-яА-ЯёЁ]", "", correct.strip().lower().replace(" ", ""))

    errors = data.get("errors", [])

    if user_input == correct_clean:
        data["score"] += 1
        tmp = await message.answer("✅ Верно!")
    else:
        errors.append({
            "question": ru,
            "correct": data["current_answer"],
            "user_input": message.text
        })
        tmp = await message.answer(f"❌ Неправильно. Правильный ответ: \n {data['current_answer']}")

    message_ids = data.get("message_ids", [])
    message_ids.append(tmp.message_id)

    await state.update_data(
        message_ids=message_ids,
        score=data["score"],
        current_index=data["current_index"] + 1,
        errors=errors
    )

    await send_typing_question(message, state)





@router.message(F.text == "⛔ Прервать тест")
async def handle_stop_button(message: types.Message, state: FSMContext):
    data = await state.get_data()

    for msg_id in data.get("message_ids", []):
        try:
            await message.bot.delete_message(message.chat.id, msg_id)
        except:
            pass

    score = data.get("score", 0)
    index = data.get("current_index", 0)

    from aiogram.types import ReplyKeyboardRemove
    await message.answer(
        f"🛑 Тест остановлен. Результат: {score} из {index}",
        reply_markup=ReplyKeyboardRemove()
    )
    errors = data.get("errors", [])
    if errors:
        lines = ["🔁 Работа над ошибками:"]
        for err in errors:
            lines.append(f"🔹**{err['question']}** \n      ❌ {err['user_input']}\n      ✅ {err['correct']}")
        await message.answer("\n".join(lines), parse_mode="Markdown")
    await state.clear()
