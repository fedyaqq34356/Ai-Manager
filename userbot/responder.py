import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from core import ai, database as db
from core.config import AUTORESPONDER_DELAY_MIN, AUTORESPONDER_DELAY_MAX, RESPONDER_CONTEXT_LIMIT

logger = logging.getLogger(__name__)

DISCLOSURE_PHRASES = [
    "кстати, ты знал что с тобой AI агент общается?",
    "между прочим, ты сейчас общаешься с AI",
    "ты в курсе что это AI, да?",
    "просто к слову - я AI агент",
    "ну и на всякий - это AI пишет, не он сам",
]

DISCLOSURE_PROBABILITY = 0.12
MIN_WORDS_TO_REPLY = 2


def _is_meaningful(text: str) -> bool:
    words = text.strip().split()
    if len(words) < MIN_WORDS_TO_REPLY and "?" not in text:
        return False
    return True


async def _owner_recently_active(client: TelegramClient, chat_id: int, threshold_minutes: int) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    try:
        async for msg in client.iter_messages(chat_id, limit=20):
            if not msg.out:
                continue
            msg_date = msg.date if msg.date.tzinfo else msg.date.replace(tzinfo=timezone.utc)
            return msg_date > cutoff
        return False
    except Exception:
        return False


async def respond(client: TelegramClient, event):
    chat_id = event.chat_id

    text = event.text or ""
    voice_transcribed = False

    if not text and event.message.voice:
        voice_enabled = await db.get_setting("voice_enabled")
        if voice_enabled == "1":
            try:
                audio_bytes = await client.download_media(event.message, file=bytes)
                text = await ai.transcribe_audio(audio_bytes)
                voice_transcribed = True
            except Exception as e:
                logger.error("Ошибка расшифровки голоса для чата %s: %s", chat_id, e)
                return
        else:
            return

    if not text:
        return

    if not _is_meaningful(text):
        logger.debug("Пропуск короткого/бессмысленного сообщения в чате %s", chat_id)
        return

    pause_if_active = await db.get_setting("pause_if_owner_active")
    if pause_if_active == "1":
        if await _owner_recently_active(client, chat_id, 60):
            logger.info("Пауза авто-ответа: владелец активен в чате %s", chat_id)
            return

    context_messages = []
    try:
        async for msg in client.iter_messages(chat_id, limit=RESPONDER_CONTEXT_LIMIT):
            if msg.text:
                context_messages.append(msg.text)
        context_messages.reverse()
    except Exception as e:
        logger.error("Не удалось получить историю чата %s: %s", chat_id, e)

    behavioral_summary = await db.get_qa_context(chat_id)
    if behavioral_summary is None:
        all_contexts = await db.get_all_qa_contexts()
        behavioral_summary = (
            "\n\n".join(all_contexts[:3])
            if all_contexts
            else "Нет данных о стиле. Отвечай естественно и по делу."
        )

    if voice_transcribed:
        text = f"[Голосовое сообщение]: {text}"

    try:
        reply_text = await ai.generate_auto_reply(text, chat_id, behavioral_summary)
    except Exception as e:
        logger.error("Ошибка генерации ответа для чата %s: %s", chat_id, e)
        return

    delay = random.uniform(AUTORESPONDER_DELAY_MIN, AUTORESPONDER_DELAY_MAX)
    await asyncio.sleep(delay)

    try:
        await client.send_message(chat_id, reply_text)
    except Exception as e:
        logger.error("Не удалось отправить авто-ответ в чат %s: %s", chat_id, e)
        return

    if random.random() < DISCLOSURE_PROBABILITY:
        phrase = random.choice(DISCLOSURE_PHRASES)
        await asyncio.sleep(random.uniform(3, 10))
        try:
            await client.send_message(chat_id, phrase)
        except Exception as e:
            logger.error("Не удалось отправить раскрытие AI в чат %s: %s", chat_id, e)
