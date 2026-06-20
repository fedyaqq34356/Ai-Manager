import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import dialogs_kb, main_menu_reply_kb, BTN_AUTORESPOND
from bot.states.forms import AutoRespondState
from core import database as db
from userbot.client import get_client

logger = logging.getLogger(__name__)
router = Router()

PREFIX = "ar"


def _get_selected(data: dict) -> set[int]:
    return set(data.get("ar_selected", []))


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


async def _show_autorespond_screen(target, state: FSMContext):
    is_message = isinstance(target, Message)
    await state.set_state(AutoRespondState.browsing)

    send = target.answer if is_message else target.message.edit_text

    try:
        dialogs = await _fetch_dialogs()
    except Exception as e:
        logger.error("Не удалось загрузить диалоги: %s", e)
        await send("Не удалось загрузить диалоги. Запущен ли юзербот?")
        return

    existing = await db.get_autorespond_chats()
    existing_ids = {ch["chat_id"] for ch in existing}

    await state.update_data(ar_dialogs=dialogs, ar_selected=list(existing_ids))
    kb = dialogs_kb(dialogs, existing_ids, 0, PREFIX, confirm_data="ar:confirm")
    await send("Выберите чаты для авто-ответчика:", reply_markup=kb)

    if not is_message:
        await target.answer()


@router.message(F.text == BTN_AUTORESPOND)
async def enter_autorespond_message(message: Message, state: FSMContext):
    await state.clear()
    await _show_autorespond_screen(message, state)


@router.callback_query(lambda c: c.data == "menu:autorespond")
async def enter_autorespond_callback(callback: CallbackQuery, state: FSMContext):
    await _show_autorespond_screen(callback, state)


@router.callback_query(lambda c: c.data and c.data.startswith("ar:page:"))
async def ar_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[2])
    data = await state.get_data()
    dialogs = data.get("ar_dialogs", [])
    selected = _get_selected(data)
    kb = dialogs_kb(dialogs, selected, page, PREFIX, confirm_data="ar:confirm")
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("ar:toggle:"))
async def ar_toggle(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    chat_id = int(parts[2])
    page = int(parts[3])
    data = await state.get_data()
    dialogs = data.get("ar_dialogs", [])
    selected = _get_selected(data)

    if chat_id in selected:
        selected.discard(chat_id)
    else:
        selected.add(chat_id)

    await state.update_data(ar_selected=list(selected))
    kb = dialogs_kb(dialogs, selected, page, PREFIX, confirm_data="ar:confirm")
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data == "ar:confirm")
async def ar_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dialogs = data.get("ar_dialogs", [])
    selected = _get_selected(data)
    id_to_title = {d["id"]: d["title"] for d in dialogs}

    await db.clear_autorespond_chats()
    for chat_id in selected:
        title = id_to_title.get(chat_id, str(chat_id))
        await db.add_autorespond_chat(chat_id, title)

    await callback.message.answer(
        f"Авто-ответчик настроен для {len(selected)} чат(ов).",
        reply_markup=main_menu_reply_kb(),
    )
    await state.clear()
    await callback.answer()
