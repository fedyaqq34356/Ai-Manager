import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import channels_list_kb, main_menu_reply_kb, BTN_CHANNELS
from bot.states.forms import ParseChannelState
from core import database as db
from userbot.client import get_client

logger = logging.getLogger(__name__)
router = Router()


async def _render_channels(target):
    channels = await db.get_parsed_channels()
    text = "Отслеживаемые каналы:" if channels else "Каналы не добавлены:"
    kb = channels_list_kb(channels)
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb)
    else:
        await target.message.edit_text(text, reply_markup=kb)


@router.message(F.text == BTN_CHANNELS)
async def enter_channels_message(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ParseChannelState.browsing)
    await _render_channels(message)


@router.callback_query(lambda c: c.data == "menu:channels")
async def enter_channels_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ParseChannelState.browsing)
    await _render_channels(callback)
    await callback.answer()


@router.callback_query(lambda c: c.data == "channels:add")
async def channels_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ParseChannelState.waiting_for_channel)
    await callback.message.edit_text(
        "Отправьте @username или ссылку канала для мониторинга."
    )
    await callback.answer()


@router.message(ParseChannelState.waiting_for_channel)
async def receive_channel(message: Message, state: FSMContext):
    identifier = message.text.strip() if message.text else ""
    if not identifier:
        await message.answer("Отправьте корректный @username или ссылку.")
        return

    client = get_client()
    try:
        entity = await client.get_entity(identifier)
    except Exception as e:
        logger.error("Не удалось найти канал %s: %s", identifier, e)
        await message.answer(f"Не удалось найти канал: {identifier}")
        return

    title = getattr(entity, "title", None) or identifier
    username = getattr(entity, "username", None)
    await db.add_parsed_channel(entity.id, title, username)

    auto_leave = await db.get_setting("auto_leave_channels")
    if auto_leave == "1":
        try:
            await client.delete_dialog(entity)
        except Exception as e:
            logger.warning("Не удалось выйти из канала %s: %s", entity.id, e)

    channels = await db.get_parsed_channels()
    await state.set_state(ParseChannelState.browsing)
    await message.answer(
        f"Добавлен: {title}\n\nОтслеживаемые каналы:",
        reply_markup=channels_list_kb(channels),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("channels:remove:"))
async def channels_remove(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split(":")[2])
    await db.remove_parsed_channel(channel_id)
    await callback.answer("Удалён.")
    await _render_channels(callback)
