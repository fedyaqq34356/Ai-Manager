import logging
from telethon import TelegramClient, events
from telethon.tl.types import User
from core import database as db
from core.config import BOT_TOKEN
from userbot import responder

logger = logging.getLogger(__name__)

_MANAGEMENT_BOT_ID = int(BOT_TOKEN.split(":")[0])


def register_handlers(client: TelegramClient):
    @client.on(events.NewMessage(incoming=True))
    async def on_message(event):
        autoresponder_enabled = await db.get_setting("autoresponder_enabled")
        if autoresponder_enabled != "1":
            return

        has_content = bool(event.text) or bool(event.message.voice)
        if not has_content:
            return

        sender = await event.get_sender()
        if isinstance(sender, User) and (sender.bot or sender.id == _MANAGEMENT_BOT_ID):
            return

        chat_id = event.chat_id

        if await db.is_autorespond_chat(chat_id):
            logger.debug("Авто-ответ: чат %s в списке", chat_id)
            await responder.respond(client, event)
            return

        respond_unknown = await db.get_setting("respond_unknown_chats")
        if respond_unknown == "1":
            logger.debug("Авто-ответ: чат %s (режим незнакомцев)", chat_id)
            await responder.respond(client, event)
