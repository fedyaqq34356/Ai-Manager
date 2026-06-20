import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import ask_kb, main_menu_reply_kb, BTN_ASK
from bot.states.forms import AskState
from core import ai, database as db

logger = logging.getLogger(__name__)
router = Router()

ASK_PROMPT = "Отправьте вопрос текстом или голосом. Отвечу на основе проиндексированных чатов."


@router.message(F.text == BTN_ASK)
async def enter_ask_message(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AskState.waiting_for_question)
    await message.answer(ASK_PROMPT, reply_markup=ask_kb())


@router.callback_query(lambda c: c.data == "menu:ask")
async def enter_ask_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AskState.waiting_for_question)
    await callback.message.edit_text(ASK_PROMPT, reply_markup=ask_kb())
    await callback.answer()


@router.message(AskState.waiting_for_question)
async def handle_question(message: Message, state: FSMContext):
    question = ""

    if message.voice:
        voice_enabled = await db.get_setting("voice_enabled")
        if voice_enabled != "1":
            await message.answer("Голосовой ввод отключён. Включите в Настройках.")
            return
        try:
            voice_io = await message.bot.download(message.voice.file_id)
            audio_bytes = voice_io.read()
            question = await ai.transcribe_audio(audio_bytes)
            await message.answer(f"Расшифровано: {question}")
        except Exception as e:
            logger.error("Ошибка расшифровки голоса: %s", e)
            await message.answer("Не удалось расшифровать голосовое сообщение.")
            return
    else:
        question = message.text or ""

    if not question:
        return

    await message.answer("Думаю...")

    context_summaries = await db.get_all_qa_contexts()

    try:
        answer = await ai.answer_question(question, context_summaries)
    except Exception as e:
        logger.error("Ошибка генерации ответа: %s", e)
        await message.answer("Не удалось сгенерировать ответ.")
        return

    await message.answer(answer, reply_markup=ask_kb())
