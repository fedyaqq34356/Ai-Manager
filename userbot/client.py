import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from core.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
from core import database as db

logger = logging.getLogger(__name__)

_client: TelegramClient | None = None


async def init_client() -> TelegramClient:
    global _client
    session_str = await db.get_encrypted_setting("_session_string") or ""
    _client = TelegramClient(StringSession(session_str), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    return _client


async def persist_session():
    if _client is None:
        return
    session_str = _client.session.save()
    await db.set_encrypted_setting("_session_string", session_str)
    logger.info("Session persisted to encrypted database.")


def get_client() -> TelegramClient:
    if _client is None:
        raise RuntimeError("Userbot not initialized. Call init_client() first.")
    return _client
