import json
import logging
from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import confirm_reply_kb, main_menu_reply_kb
from bot.states.forms import AnswerState
from core import ai, database as db
from core.config import AI_SIGNATURE
from userbot.client import get_client

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(lambda c: c.data == "answer:start")
async def answer_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AnswerState.waiting_for_contact)
    await callback.message.edit_text(
        "Отправьте @username или контакт человека, которому хотите ответить."
    )
    await callback.answer()


@router.message(AnswerState.waiting_for_contact)
async def answer_contact(message: Message, state: FSMContext):
    username = message.text.strip() if message.text else None
    if not username:
        await message.answer("Отправьте корректный @username или контакт.")
        return

    client = get_client()
    try:
        entity = await client.get_entity(username)
        chat_id = entity.id
        chat_title = (
            getattr(entity, "title", None)
            or getattr(entity, "first_name", None)
            or username
        )
    except Exception as e:
        logger.error("Не удалось найти контакт %s: %s", username, e)
        await message.answer(f"Не удалось найти контакт: {username}")
        return

    await state.update_data(answer_chat_id=chat_id, answer_chat_title=chat_title)
    await state.set_state(AnswerState.waiting_for_instruction)
    await message.answer(
        f"Найдено: {chat_title}\n\nОпишите свой намерение или вставьте референс для ответа."
    )


@router.message(AnswerState.waiting_for_instruction)
async def answer_instruction(message: Message, state: FSMContext):
    instruction = message.text or ""
    data = await state.get_data()
    chat_id = data.get("answer_chat_id")

    await message.answer("Составляю ответ...")

    client = get_client()
    history_lines = []
    try:
        me = await client.get_me()
        async for msg in client.iter_messages(chat_id, limit=30):
            if msg.text:
                sender = "Я" if msg.sender_id == me.id else "Они"
                history_lines.append(f"{sender}: {msg.text}")
        history_lines.reverse()
    except Exception as e:
        logger.error("Не удалось получить историю для ответа: %s", e)

    history_context = "\n".join(history_lines) if history_lines else "Нет предыдущих сообщений."

    contact = await db.get_contact(chat_id)
    if contact:
        topics = json.loads(contact.get("topics") or "[]")
        open_items = json.loads(contact.get("open_items") or "[]")
        contact_context = (
            f"\nПрофиль контакта - {contact['display_name']}:\n"
            f"Характер отношений: {contact.get('relationship', '')}\n"
            f"Темы: {', '.join(topics)}\n"
            f"Нерешённые вопросы: {', '.join(open_items)}\n"
        )
        history_context = contact_context + "\nИстория переписки:\n" + history_context

    try:
        composed = await ai.compose_targeted_reply(instruction, chat_id, history_context)
    except Exception as e:
        logger.error("Ошибка составления ответа: %s", e)
        await message.answer("Не удалось составить ответ.")
        return

    await state.update_data(answer_composed=composed)
    await state.set_state(AnswerState.confirming)
    await message.answer(
        f"Составленный ответ:\n\n{composed}{AI_SIGNATURE}\n\nОтправить?",
        reply_markup=confirm_reply_kb(),
    )


@router.callback_query(lambda c: c.data == "answer:confirm")
async def answer_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id = data.get("answer_chat_id")
    composed = data.get("answer_composed", "")

    client = get_client()
    try:
        await client.send_message(chat_id, composed + AI_SIGNATURE)
        await callback.message.answer("Ответ отправлен.", reply_markup=main_menu_reply_kb())
    except Exception as e:
        logger.error("Не удалось отправить ответ: %s", e)
        await callback.message.answer(f"Не удалось отправить: {e}", reply_markup=main_menu_reply_kb())

    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "answer:edit")
async def answer_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AnswerState.waiting_for_instruction)
    await callback.message.edit_text("Отправьте правки или новую инструкцию.")
    await callback.answer()
