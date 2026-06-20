import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_ID = int(os.environ["TELEGRAM_API_ID"])
TELEGRAM_API_HASH = os.environ["TELEGRAM_API_HASH"]
TELEGRAM_PHONE = os.environ["TELEGRAM_PHONE"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OWNER_TELEGRAM_ID = int(os.environ["OWNER_TELEGRAM_ID"])
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")

OPENAI_MODEL = "gpt-4o-mini"
USERBOT_SESSION = "ai_manager_session"

AUTORESPONDER_DELAY_MIN = 5
AUTORESPONDER_DELAY_MAX = 20
HISTORY_FETCH_LIMIT = 200
RESPONDER_CONTEXT_LIMIT = 50
DIALOGS_PAGE_SIZE = 10

AI_SIGNATURE = (
    "\n-\n"
    "This message was autonomously composed by an AI responder, "
    "architected by the individual you are in direct contact with.\n\n"
    "Engineered with AI Manager - https://github.com/fedyaqq34356/Ai-Manager.git"
)
