import asyncio
import logging
import os
import signal
import stat
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.middlewares.auth import OwnerOnlyMiddleware
from bot.router import main_router
from core.config import BOT_TOKEN, TELEGRAM_PHONE, ENCRYPTION_KEY
from core.database import init_db
from core.security import init_fernet
from userbot.client import init_client, persist_session
from userbot.listener import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SENSITIVE_FILES = ["ai_manager.db", ".env"]


def _validate_encryption_key():
    if not ENCRYPTION_KEY:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        print("\n" + "=" * 60)
        print("ERROR: ENCRYPTION_KEY is not set in .env")
        print("Add this line to your .env file:")
        print(f"\nENCRYPTION_KEY={key}\n")
        print("Keep this key safe. Losing it = losing all stored data.")
        print("=" * 60 + "\n")
        sys.exit(1)


def _harden_permissions():
    for path in SENSITIVE_FILES:
        if os.path.exists(path):
            try:
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            except OSError as e:
                logger.warning("Could not set permissions on %s: %s", path, e)

    old_session = "ai_manager_session.session"
    if os.path.exists(old_session):
        try:
            os.remove(old_session)
            logger.info("Removed plaintext session file.")
        except OSError:
            pass


async def run_bot():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(OwnerOnlyMiddleware())
    dp.callback_query.middleware(OwnerOnlyMiddleware())
    dp.include_router(main_router)
    logger.info("Management bot starting...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


async def run_userbot():
    client = await init_client()
    register_handlers(client)
    logger.info("Userbot starting...")
    await client.start(phone=TELEGRAM_PHONE)
    await persist_session()
    logger.info("Userbot connected.")
    await client.run_until_disconnected()


async def main():
    _validate_encryption_key()
    init_fernet(ENCRYPTION_KEY)

    await init_db()
    logger.info("Database initialized.")

    _harden_permissions()

    loop = asyncio.get_event_loop()

    def shutdown(sig):
        logger.info("Received %s, shutting down...", sig.name)
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, shutdown, s)

    try:
        await asyncio.gather(run_bot(), run_userbot())
    except asyncio.CancelledError:
        logger.info("Shutdown complete.")
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
