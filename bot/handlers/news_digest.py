import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import main_menu_reply_kb, BTN_DIGEST
from core import database as db
from core.config import OWNER_TELEGRAM_ID
from core.parser import build_digest
from userbot.client import get_client

logger = logging.getLogger(__name__)
router = Router()

MAX_MSG_LEN = 4096


async def _run_digest(send_func, state: FSMContext):
    client = get_client()
    try:
        digest = await build_digest(client)
    except Exception as e:
        logger.error("Не удалось создать дайджест: %s", e)
        await send_func("Не удалось создать дайджест.", reply_markup=main_menu_reply_kb())
        return

    await db.update_digest_time(OWNER_TELEGRAM_ID)

    chunks = [digest[i:i + MAX_MSG_LEN] for i in range(0, len(digest), MAX_MSG_LEN)]
    for chunk in chunks:
        await send_func(chunk)

    await send_func("Дайджест готов.", reply_markup=main_menu_reply_kb())


@router.message(F.text == BTN_DIGEST)
async def handle_digest_message(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Получаю события с момента последнего запроса...")
    await _run_digest(message.answer, state)


@router.callback_query(lambda c: c.data == "menu:digest")
async def handle_digest_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Получаю события с момента последнего запроса...")
    await callback.answer()
    await _run_digest(callback.message.answer, state)
