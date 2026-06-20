import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import main_menu_reply_kb

logger = logging.getLogger(__name__)
router = Router()

MAIN_MENU_TEXT = "AI Manager - Главное меню"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_reply_kb())


@router.callback_query(lambda c: c.data == "menu:main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_reply_kb())
