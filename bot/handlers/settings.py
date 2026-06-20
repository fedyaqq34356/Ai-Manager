import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from bot.keyboards.inline import settings_kb, main_menu_reply_kb, BTN_SETTINGS
from bot.states.forms import SettingsState
from core import ai, database as db

logger = logging.getLogger(__name__)
router = Router()


async def _render_settings(target):
    ar = await db.get_setting("autoresponder_enabled")
    ru = await db.get_setting("respond_unknown_chats")
    al = await db.get_setting("auto_leave_channels")
    vo = await db.get_setting("voice_enabled")
    sp = await db.get_setting("antispam_enabled")
    pa = await db.get_setting("pause_if_owner_active")
    kb = settings_kb(ar == "1", ru == "1", al == "1", vo == "1", sp == "1", pa == "1")
    if isinstance(target, Message):
        await target.answer("Настройки:", reply_markup=kb)
    else:
        try:
            await target.message.edit_text("Настройки:", reply_markup=kb)
        except TelegramBadRequest:
            pass


@router.message(F.text == BTN_SETTINGS)
async def enter_settings_message(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SettingsState.main)
    await _render_settings(message)


@router.callback_query(lambda c: c.data == "menu:settings")
async def enter_settings_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.main)
    await _render_settings(callback)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("settings:toggle:"))
async def toggle_setting(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":")[2]
    current = await db.get_setting(key)
    new_val = "0" if current == "1" else "1"
    await db.set_setting(key, new_val)
    await _render_settings(callback)
    await callback.answer()


@router.callback_query(lambda c: c.data == "settings:clear:learned")
async def clear_learned(callback: CallbackQuery, state: FSMContext):
    await db.clear_all_learned_chats()
    await callback.answer("Обученные чаты очищены.")
    await _render_settings(callback)


@router.callback_query(lambda c: c.data == "settings:clear:autorespond")
async def clear_autorespond(callback: CallbackQuery, state: FSMContext):
    await db.clear_autorespond_chats()
    await callback.answer("Авто-ответчик очищен.")
    await _render_settings(callback)


@router.callback_query(lambda c: c.data == "settings:clear:channels")
async def clear_channels(callback: CallbackQuery, state: FSMContext):
    await db.clear_parsed_channels()
    await callback.answer("Каналы очищены.")
    await _render_settings(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("settings:reset_ai:"))
async def reset_ai_session(callback: CallbackQuery, state: FSMContext):
    session_key = callback.data.split(":")[2]
    await ai.clear_session(session_key)
    await callback.answer(f"Память AI сброшена: {session_key}")
    await _render_settings(callback)
