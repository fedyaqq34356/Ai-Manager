import json
import logging
from telethon import TelegramClient
from core import ai, database as db

logger = logging.getLogger(__name__)


async def build_and_save_contact(client: TelegramClient, chat_id: int, display_name: str):
    username = None
    try:
        entity = await client.get_entity(chat_id)
        username = getattr(entity, "username", None)
    except Exception:
        pass

    messages = await db.get_chat_messages(chat_id)
    if not messages:
        logger.info("No messages in DB for contact %s, skipping profile build", chat_id)
        return

    last_interaction_at = messages[-1].get("sent_at", "") if messages else ""

    profile = await ai.build_contact_profile(
        [{"sender_role": m["sender_role"], "message_text": m["message_text"]} for m in messages],
        display_name,
    )

    await db.upsert_contact(
        chat_id=chat_id,
        display_name=display_name,
        username=username,
        relationship=profile.get("relationship", ""),
        topics=json.dumps(profile.get("topics", []), ensure_ascii=False),
        open_items=json.dumps(profile.get("open_items", []), ensure_ascii=False),
        last_message_preview=profile.get("last_message_preview", ""),
        last_interaction_at=last_interaction_at,
    )
    logger.info("Contact profile saved for %s (%s)", display_name, chat_id)
