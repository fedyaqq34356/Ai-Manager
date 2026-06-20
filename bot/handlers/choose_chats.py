import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import dialogs_kb, main_menu_reply_kb, BTN_LEARN
from bot.states.forms import LearnChatsState
from core import database as db
from userbot.client import get_client
from userbot.learner import learn_chat

logger = logging.getLogger(__name__)
router = Router()

PREFIX = "learn"


def _get_selected(data: dict) -> set[int]:
    return set(data.get("learn_selected", []))


async def _fetch_dialogs() -> list[dict]:
    client = get_client()
    dialogs = []
    async for dialog in client.iter_dialogs():
        if dialog.entity:
            dialogs.append({
                "id": dialog.entity.id,
                "title": dialog.name or str(dialog.entity.id),
            })
    return dialogs


async def _show_learn_screen(target, state: FSMContext):
    is_message = isinstance(target, Message)
    await state.set_state(LearnChatsState.browsing)

    send = target.answer if is_message else target.message.edit_text

    try:
        dialogs = await _fetch_dialogs()
    except Exception as e:
        logger.error("Не удалось загрузить диалоги: %s", e)
        await send("Не удалось загрузить диалоги. Запущен ли юзербот?")
        return

    await state.update_data(learn_dialogs=dialogs, learn_selected=[])
    kb = dialogs_kb(dialogs, set(), 0, PREFIX, confirm_data="learn:confirm")
    await send("Выберите чаты для обучения:", reply_markup=kb)

    if not is_message:
        await target.answer()


@router.message(F.text == BTN_LEARN)
async def enter_learn_message(message: Message, state: FSMContext):
    await state.clear()
    await _show_learn_screen(message, state)


@router.callback_query(lambda c: c.data == "menu:learn")
async def enter_learn_callback(callback: CallbackQuery, state: FSMContext):
    await _show_learn_screen(callback, state)


@router.callback_query(lambda c: c.data and c.data.startswith("learn:page:"))
async def learn_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[2])
    data = await state.get_data()
    dialogs = data.get("learn_dialogs", [])
    selected = _get_selected(data)
    kb = dialogs_kb(dialogs, selected, page, PREFIX, confirm_data="learn:confirm")
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("learn:toggle:"))
async def learn_toggle(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    chat_id = int(parts[2])
    page = int(parts[3])
    data = await state.get_data()
    dialogs = data.get("learn_dialogs", [])
    selected = _get_selected(data)

    if chat_id in selected:
        selected.discard(chat_id)
    else:
        selected.add(chat_id)

    await state.update_data(learn_selected=list(selected))
    kb = dialogs_kb(dialogs, selected, page, PREFIX, confirm_data="learn:confirm")
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data == "learn:confirm")
async def learn_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dialogs = data.get("learn_dialogs", [])
    selected = _get_selected(data)

    if not selected:
        await callback.answer("Ни один чат не выбран.")
        return

    await callback.message.edit_text("Сохраняю выбор и индексирую сообщения...")
    await callback.answer()

    id_to_title = {d["id"]: d["title"] for d in dialogs}
    client = get_client()

    for chat_id in selected:
        title = id_to_title.get(chat_id, str(chat_id))
        await db.add_learned_chat(chat_id, title)
        try:
            await learn_chat(client, chat_id, title=title)
        except Exception as e:
            logger.error("Не удалось обучить чат %s: %s", chat_id, e)

    await callback.message.answer(
        f"Готово. Проиндексировано {len(selected)} чат(ов).",
        reply_markup=main_menu_reply_kb(),
    )
    await state.clear()
