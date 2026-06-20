import logging
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from core.config import OWNER_TELEGRAM_ID

logger = logging.getLogger(__name__)


class OwnerOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or user.id != OWNER_TELEGRAM_ID:
            logger.warning("Blocked unauthorized access from user %s", user.id if user else "unknown")
            return
        return await handler(event, data)
