import os
import json
from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import save_word, get_user_words_for_set, count_user_progress_for_set
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# helpers/escape_md.py
def escape_md(text: str) -> str:
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)

stop_reply_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⛔ Остановить")]],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Нажми, если хочешь завершить набор"
)

router = Router()

WORD_SETS_PATH = "data/"


class SetSelect(StatesGroup):
    choosing_set = State()
    browsing_words = State()


@router.message(F.text == "/sets")
async def show_sets(message: types.Message, state: FSMContext):
    files = [f for f in os.listdir(WORD_SETS_PATH) if f.endswith(".json") and f.startswith("en_")]
    
    # {'en_a1.json': 'A1', ...}
    level_map = {f: f.replace(".json", "").split("_")[1].upper() for f in files}

    # Упорядочим по порядку уровней
    level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    sorted_levels = sorted(level_map.items(), key=lambda x: level_order.index(x[1]))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=level, callback_data=f"set:{file.replace('.json', '')}")]
        for file, level in sorted_levels
    ])

    await state.set_state(SetSelect.choosing_set)
    await message.answer("Чтобы остановить — нажми ⛔", reply_markup=stop_reply_kb)
    await message.answer("📚 Выбери уровень:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("set:"))
async def start_set(callback: types.CallbackQuery, state: FSMContext):
    set_name = callback.data.split(":")[1]
    file_path = os.path.join(WORD_SETS_PATH, f"{set_name}.json")

    with open(file_path, "r", encoding="utf-8") as f:
        all_words = json.load(f)

    existing_words = await get_user_words_for_set(callback.from_user.id, set_name)
    existing_set = {(w[0], w[1]) for w in existing_words}
    filtered = [w for w in all_words if (w["ru"], w["en"]) not in existing_set]

    if not filtered:
        await callback.message.edit_text("🎉 Ты уже прошёл все слова в этом наборе.")
        return

    await state.update_data(
        set_name=set_name,
        words=filtered,
        index=0,
        last_message_id=callback.message.message_id,
        show_translation=False  # сбрасываем при старте
    )   
    await state.set_state(SetSelect.browsing_words)

    await show_current_word(callback.message, state)


async def show_current_word(message: types.Message, state: FSMContext):
    data = await state.get_data()
    show_translation = data.get("show_translation", False)
    index = data["index"]
    words = data["words"]
    message_id = data.get("last_message_id")


    set_name = data.get("set_name")
    user_id = message.chat.id
    total_words = len(data["words"]) + data.get("index", 0)  # исходный full list, до фильтрации

    # Но лучше (и точнее) — перечитать json:
    file_path = os.path.join("data/", f"{set_name}.json")
    with open(file_path, "r", encoding="utf-8") as f:
        all_words = json.load(f)
    total_words = len(all_words)

    user_progress = await count_user_progress_for_set(user_id, set_name)
    level = set_name.upper().replace("EN_", "")
    progress = f"Набор {level}\nПрогресс: {user_progress} / {total_words}"

    if index >= len(words):
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text="✅ Ты просмотрел все слова в этом наборе!"
        )
        await message.answer("📘 Возвращаемся в главное меню", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    word = words[index]
    ru = escape_md(word["ru"])
    en = escape_md(word["en"])

    if not show_translation:
        hidden = "*" * len(word["en"])
        text = f"{progress}\n\n❓Знаешь перевод слова?\n\n🔹 *{ru[0].upper() + ru[1:]}*\n\nПеревод: `{hidden}`"
    else:
        text = f"{progress}\n\n❓Знаешь перевод слова?\n\n*🔹 {ru[0].upper() + ru[1:]}*\n\nПеревод: *{en}*"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👁", callback_data="show"),
            InlineKeyboardButton(text="✅", callback_data="known"),
            InlineKeyboardButton(text="➕", callback_data="add"),
            InlineKeyboardButton(text="⏭", callback_data="skip"),
        ]
    ])

    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=text,
            parse_mode="MarkdownV2",
            reply_markup=keyboard
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Ничего не делаем — просто игнорируем
            pass
        else:
            raise


@router.callback_query(F.data == "show")
async def reveal_translation(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    current_flag = data.get("show_translation", False)
    await state.update_data(show_translation=not current_flag)
    await callback.answer()
    await show_current_word(callback.message, state)


@router.callback_query(F.data.in_(["known", "add", "skip"]))
async def handle_response(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data["index"]
    words = data["words"]
    set_name = data["set_name"]
    user_id = callback.from_user.id

    word = words[index]
    ru = word["ru"]
    en = word["en"]

    if callback.data == "known":
        await save_word(user_id, ru, en, "en", source_set=set_name, status="known")
    elif callback.data == "add":
        await save_word(user_id, ru, en, "en", source_set=set_name, status="learning")

    await state.update_data(index=index + 1, show_translation=False)  # сброс при переходе
    await callback.answer()
    await show_current_word(callback.message, state)


@router.message(F.text == "⛔ Остановить")
async def stop_set_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    set_name = data.get("set_name", "набор")
    index = data.get("index", 0)

    await state.clear()
    await message.answer(
        f"🛑 Повторение остановлено.\nТы просмотрел {index} слов из набора *{escape_md(set_name.upper())}*.",
        parse_mode="MarkdownV2",
        reply_markup=ReplyKeyboardRemove()
    )