import json
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import contacts_list_kb, contact_card_kb, main_menu_reply_kb, BTN_CRM
from bot.states.forms import CRMState, AnswerState
from core import database as db
from userbot.client import get_client
from userbot.contact_builder import build_and_save_contact
from userbot.learner import learn_chat

logger = logging.getLogger(__name__)
router = Router()

SEP = "─" * 32


def _format_card(contact: dict) -> str:
    lines = [SEP]

    name_line = contact["display_name"]
    if contact.get("username"):
        name_line += f"  (@{contact['username']})"
    lines.append(name_line)

    if contact.get("last_interaction_at"):
        try:
            dt = datetime.fromisoformat(contact["last_interaction_at"])
            lines.append(f"Последний раз: {dt.strftime('%d.%m.%Y')}")
        except Exception:
            pass

    lines.append(SEP)

    if contact.get("relationship"):
        lines += ["", "Характер отношений", contact["relationship"]]

    try:
        topics = json.loads(contact.get("topics") or "[]")
    except Exception:
        topics = []
    if topics:
        lines += ["", "Темы обсуждений"]
        lines += [f"- {t}" for t in topics]

    try:
        open_items = json.loads(contact.get("open_items") or "[]")
    except Exception:
        open_items = []
    if open_items:
        lines += ["", "Нерешённые вопросы"]
        lines += [f"- {item}" for item in open_items]

    if contact.get("last_message_preview"):
        lines += ["", "Последнее сообщение", f'"{contact["last_message_preview"]}"']

    lines.append(SEP)
    return "\n".join(lines)


async def _show_contacts(target, state: FSMContext):
    is_message = isinstance(target, Message)
    await state.set_state(CRMState.browsing)
    contacts = await db.get_all_contacts()

    if not contacts:
        text = "Контактов пока нет. Сначала обучите чаты."
        if is_message:
            await target.answer(text, reply_markup=main_menu_reply_kb())
        else:
            await target.message.edit_text(text)
            await target.message.answer("Главное меню:", reply_markup=main_menu_reply_kb())
        return

    await state.update_data(crm_contacts=contacts)
    kb = contacts_list_kb(contacts, 0)
    text = f"Контакты ({len(contacts)}):"

    if is_message:
        await target.answer(text, reply_markup=kb)
    else:
        await target.message.edit_text(text, reply_markup=kb)


@router.message(F.text == BTN_CRM)
async def enter_crm_message(message: Message, state: FSMContext):
    await state.clear()
    await _show_contacts(message, state)


@router.callback_query(lambda c: c.data == "menu:crm")
async def enter_crm_callback(callback: CallbackQuery, state: FSMContext):
    await _show_contacts(callback, state)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("crm:page:"))
async def crm_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[2])
    data = await state.get_data()
    contacts = data.get("crm_contacts", [])
    kb = contacts_list_kb(contacts, page)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("crm:view:"))
async def crm_view(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    contact = await db.get_contact(chat_id)
    if not contact:
        await callback.answer("Контакт не найден.")
        return

    card = _format_card(contact)
    await callback.message.edit_text(card, reply_markup=contact_card_kb(chat_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("crm:refresh:"))
async def crm_refresh(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    contact = await db.get_contact(chat_id)
    display_name = contact["display_name"] if contact else str(chat_id)

    await callback.message.edit_text(f"Обновляю профиль {display_name}...")
    await callback.answer()

    client = get_client()
    try:
        await learn_chat(client, chat_id, title=display_name)
    except Exception as e:
        logger.error("Не удалось обновить контакт %s: %s", chat_id, e)
        await callback.message.edit_text("Не удалось обновить.", reply_markup=contact_card_kb(chat_id))
        return

    contact = await db.get_contact(chat_id)
    if contact:
        await callback.message.edit_text(_format_card(contact), reply_markup=contact_card_kb(chat_id))
    else:
        await callback.message.answer("Профиль обновлён.", reply_markup=main_menu_reply_kb())


@router.callback_query(lambda c: c.data and c.data.startswith("crm:reply:"))
async def crm_reply(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    contact = await db.get_contact(chat_id)
    display_name = contact["display_name"] if contact else str(chat_id)

    await state.set_state(AnswerState.waiting_for_instruction)
    await state.update_data(answer_chat_id=chat_id, answer_chat_title=display_name)
    await callback.message.edit_text(
        f"Составляю ответ для {display_name}\n\nОпишите намерение или вставьте референс."
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "crm:scan_all")
async def crm_scan_all(callback: CallbackQuery, state: FSMContext):
    learned = await db.get_learned_chats()
    if not learned:
        await callback.answer("Нет обученных чатов для сканирования.")
        return

    await callback.message.edit_text(f"Сканирую {len(learned)} чат(ов)...")
    await callback.answer()

    client = get_client()
    for ch in learned:
        try:
            await build_and_save_contact(client, ch["chat_id"], ch["chat_title"])
        except Exception as e:
            logger.error("Ошибка сканирования чата %s: %s", ch["chat_id"], e)

    contacts = await db.get_all_contacts()
    await state.update_data(crm_contacts=contacts)
    kb = contacts_list_kb(contacts, 0)
    await callback.message.edit_text(f"Готово. Контакты ({len(contacts)}):", reply_markup=kb)
