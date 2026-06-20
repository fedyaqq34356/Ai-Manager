from aiogram import Router
from bot.handlers import start, choose_chats, autorespond, channels, news_digest, ask, answer, settings, summarize, crm

main_router = Router()

main_router.include_router(start.router)
main_router.include_router(choose_chats.router)
main_router.include_router(autorespond.router)
main_router.include_router(channels.router)
main_router.include_router(news_digest.router)
main_router.include_router(ask.router)
main_router.include_router(answer.router)
main_router.include_router(settings.router)
main_router.include_router(summarize.router)
main_router.include_router(crm.router)
