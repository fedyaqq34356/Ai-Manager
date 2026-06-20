import logging
from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import summarize_dialogs_kb, summarize_period_kb, main_menu_reply_kb, BTN_SUMMARIZE
from bot.states.forms import SummarizeState
from core import ai, database as db
from userbot.client import get_client

logger = logging.getLogger(__name__)
router = Router()

PERIOD_MAP = {
    "1h": ("последний час", timedelta(hours=1)),
    "24h": ("последние 24 часа", timedelta(hours=24)),
    "7d": ("последние 7 дней", timedelta(days=7)),
    "30d": ("последние 30 дней", timedelta(days=30)),
}

MAX_MSG_LEN = 4096


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


async def _show_summarize_screen(target, state: FSMContext):
    is_message = isinstance(target, Message)
    await state.set_state(SummarizeState.selecting_chat)

    send = target.answer if is_message else target.message.edit_text

    try:
        dialogs = await _fetch_dialogs()
    except Exception as e:
        logger.error("Не удалось загрузить диалоги для саммари: %s", e)
        await send("Не удалось загрузить диалоги. Запущен ли юзербот?")
        return

    await state.update_data(sum_dialogs=dialogs)
    kb = summarize_dialogs_kb(dialogs, 0)
    await send("Выберите чат для саммари:", reply_markup=kb)

    if not is_message:
        await target.answer()


@router.message(F.text == BTN_SUMMARIZE)
async def enter_summarize_message(message: Message, state: FSMContext):
    await state.clear()
    await _show_summarize_screen(message, state)


@router.callback_query(lambda c: c.data == "menu:summarize")
async def enter_summarize_callback(callback: CallbackQuery, state: FSMContext):
    await _show_summarize_screen(callback, state)


@router.callback_query(lambda c: c.data and c.data.startswith("summarize:page:"))
async def summarize_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[2])
    data = await state.get_data()
    dialogs = data.get("sum_dialogs", [])
    kb = summarize_dialogs_kb(dialogs, page)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("summarize:chat:"))
async def summarize_select_chat(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    chat_id = int(parts[2])
    data = await state.get_data()
    dialogs = data.get("sum_dialogs", [])
    title = next((d["title"] for d in dialogs if d["id"] == chat_id), str(chat_id))

    await state.update_data(sum_chat_id=chat_id, sum_chat_title=title)
    await state.set_state(SummarizeState.selecting_period)
    await callback.message.edit_text(
        f"Чат: {title}\n\nВыберите период для саммари:",
        reply_markup=summarize_period_kb(chat_id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("summarize:period:"))
async def summarize_run(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    chat_id = int(parts[2])
    period_code = parts[3]

    period_label, delta = PERIOD_MAP.get(period_code, ("последние 24 часа", timedelta(hours=24)))
    since = datetime.now(timezone.utc) - delta

    data = await state.get_data()
    chat_title = data.get("sum_chat_title", str(chat_id))

    await callback.message.edit_text(f"Получаю сообщения из {chat_title} за {period_label}...")
    await callback.answer()

    client = get_client()
    messages = []
    try:
        me = await client.get_me()
        async for msg in client.iter_messages(chat_id, limit=1000):
            if msg.date is None:
                continue
            msg_date = msg.date if msg.date.tzinfo else msg.date.replace(tzinfo=timezone.utc)
            if msg_date < since:
                break
            if msg.text:
                role = "owner" if msg.sender_id == me.id else "other"
                messages.append({"sender_role": role, "message_text": msg.text})
        messages.reverse()
    except Exception as e:
        logger.error("Не удалось получить сообщения для саммари: %s", e)
        await callback.message.edit_text("Не удалось получить сообщения.", reply_markup=main_menu_reply_kb())
        return

    if not messages:
        await callback.message.answer(
            f"Нет сообщений в {chat_title} за {period_label}.",
            reply_markup=main_menu_reply_kb(),
        )
        return

    try:
        summary = await ai.summarize_chat_history(messages, period_label)
    except Exception as e:
        logger.error("Ошибка создания саммари: %s", e)
        await callback.message.answer("Не удалось создать саммари.", reply_markup=main_menu_reply_kb())
        return

    header = f"{chat_title} - {period_label} ({len(messages)} сообщений)\n\n"
    full = header + summary

    chunks = [full[i:i + MAX_MSG_LEN] for i in range(0, len(full), MAX_MSG_LEN)]
    for i, chunk in enumerate(chunks):
        if i == 0:
            await callback.message.edit_text(chunk)
        else:
            await callback.message.answer(chunk)

    await callback.message.answer("Саммари готово.", reply_markup=main_menu_reply_kb())
    await state.clear()
