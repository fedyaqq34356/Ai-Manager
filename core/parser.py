import logging
from datetime import datetime, timedelta, timezone
from telethon.tl.types import PeerChannel
from core import ai, database as db
from core.config import OWNER_TELEGRAM_ID

logger = logging.getLogger(__name__)


async def fetch_channel_messages(client, channel: dict, since: datetime) -> list[dict]:
    since_aware = since.replace(tzinfo=timezone.utc) if not since.tzinfo else since
    messages = []
    try:
        ref = channel.get("channel_username") or PeerChannel(channel["channel_id"])
        async for msg in client.iter_messages(ref, limit=500):
            if msg.date is None:
                continue
            msg_date = msg.date if msg.date.tzinfo else msg.date.replace(tzinfo=timezone.utc)
            if msg_date < since_aware:
                break
            if msg.text:
                messages.append({
                    "channel": channel["channel_title"],
                    "text": msg.text,
                    "date": msg_date.strftime("%d.%m.%Y"),
                })
    except Exception as e:
        logger.error("Failed to fetch messages from channel %s: %s", channel.get("channel_title"), e)
    return messages


async def build_digest(client) -> str:
    channels = await db.get_parsed_channels()
    if not channels:
        return "No channels configured for monitoring."

    last_time_str = await db.get_last_digest_time(OWNER_TELEGRAM_ID)
    since = datetime.fromisoformat(last_time_str) if last_time_str else datetime.utcnow() - timedelta(hours=24)

    all_messages = []
    for ch in channels:
        msgs = await fetch_channel_messages(client, ch, since)
        all_messages.extend(msgs)

    if not all_messages:
        return "No new messages since last digest."

    return await ai.generate_digest(all_messages)
