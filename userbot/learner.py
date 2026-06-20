import logging
from telethon import TelegramClient
from core import ai, database as db
from core.config import HISTORY_FETCH_LIMIT
from userbot.contact_builder import build_and_save_contact

logger = logging.getLogger(__name__)


async def learn_chat(client: TelegramClient, chat_id: int, title: str = ""):
    me = await client.get_me()
    owner_id = me.id

    messages = []
    try:
        async for msg in client.iter_messages(chat_id, limit=HISTORY_FETCH_LIMIT):
            if not msg.text:
                continue
            role = "owner" if msg.sender_id == owner_id else "other"
            messages.append({
                "role": role,
                "text": msg.text,
                "sent_at": msg.date.isoformat() if msg.date else "",
            })
    except Exception as e:
        logger.error("Failed to fetch history for chat %s: %s", chat_id, e)
        return

    if not messages:
        logger.info("No messages found in chat %s", chat_id)
        return

    await db.clear_chat_messages(chat_id)
    await db.insert_chat_messages(
        chat_id,
        [{"role": m["role"], "text": m["text"], "sent_at": m["sent_at"]} for m in messages],
    )

    try:
        summary = await ai.generate_behavioral_summary(
            [{"sender_role": m["role"], "message_text": m["text"]} for m in messages]
        )
        await db.upsert_qa_context(chat_id, summary)
        logger.info("Learned chat %s successfully", chat_id)
    except Exception as e:
        logger.error("Failed to generate behavioral summary for chat %s: %s", chat_id, e)

    display_name = title or str(chat_id)
    try:
        await build_and_save_contact(client, chat_id, display_name)
    except Exception as e:
        logger.error("Failed to build contact profile for chat %s: %s", chat_id, e)
