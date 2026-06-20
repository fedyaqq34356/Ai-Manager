# AI Manager

Autonomous Telegram AI assistant that runs silently in the background and handles your messages. Combines a userbot (operates as you) and a management bot (your private control panel).

## Architecture

- **Userbot** (Telethon): Runs as your Telegram account. Monitors incoming messages, sends auto-replies, fetches chat history, and pulls channel content.
- **Management Bot** (aiogram 3.x): Private control panel — only the owner can access it. All configuration and AI interaction happens here.
- **AI Core** (OpenAI gpt-4o-mini): All inference. Behavioral profiling, auto-replies, digests, Q&A, voice transcription, contact cards.
- **Database** (aiosqlite + Fernet encryption): All sensitive data — messages, session tokens, AI history, contact profiles — encrypted at rest.

## Features

- **Learn Chats**: Index up to 200 messages from selected chats. Builds a behavioral profile of your communication style — tone, vocabulary, response length, patterns.
- **Auto-Responder**: Automatically replies in selected chats using your behavioral profile. Replies are short, natural, in your style. Triggered only for chats you explicitly choose. Includes smart filters: skips one-word messages with no question, pauses when you are recently active yourself. Occasionally drops a casual AI disclosure phrase.
- **Voice Messages**: Incoming voice messages are transcribed via Whisper and replied to as text.
- **Anti-Spam Filter**: AI evaluates each message before replying — ignores broadcasts, bots, cold outreach.
- **Content Filter Bypass**: If OpenAI refuses to respond to a harsh message, the system automatically sanitizes the input and retries — maintaining conversation flow without breaking character.
- **News Digest**: Monitors Telegram channels you add. On demand, fetches all new posts since your last request, filters ads and promotions, groups events by topic, and delivers a clean digest.
- **Ask**: Ask any question based on knowledge indexed from your chats. Stateless per-query — no drift, no chatbot behavior.
- **Chat Summary**: Generate a summary of any chat for a selected time period — 1h, 24h, 7d, 30d.
- **Contacts (CRM)**: Builds contact cards for each person — relationship context, topics discussed, open items, last message preview. Scan all chats at once or refresh individual contacts.
- **Compose Reply**: Draft a targeted reply to someone using their chat history and your instruction. Review, edit, or cancel before sending.
- **Settings**: Toggle all features. Clear learned chats, auto-responder list, channels. Reset AI session memory per feature.

## Security

- Session string stored encrypted in SQLite — no `.session` file on disk
- All message content, AI history, and contact data encrypted with Fernet (AES-128-CBC)
- `.env` and database files set to `chmod 600` on startup
- Management bot restricted to owner Telegram ID only
- Userbot never responds to bot accounts or the management bot itself

## Installation

```bash
git clone https://github.com/fedyaqq34356/Ai-Manager.git
cd Ai-Manager
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your credentials, then run:

```bash
python main.py
```

On first run the userbot will ask for your phone number and OTP in the terminal to create and store the session.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_API_ID` | From my.telegram.org |
| `TELEGRAM_API_HASH` | From my.telegram.org |
| `TELEGRAM_PHONE` | Phone number with country code |
| `BOT_TOKEN` | From @BotFather |
| `OPENAI_API_KEY` | OpenAI API key |
| `OWNER_TELEGRAM_ID` | Your Telegram user ID |
| `ENCRYPTION_KEY` | Fernet key — generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

## Stack

- Python 3.11+
- Telethon — userbot
- aiogram 3.x — management bot
- OpenAI API (gpt-4o-mini + whisper-1)
- aiosqlite — async SQLite
- cryptography (Fernet) — encryption

## GitHub

https://github.com/fedyaqq34356/Ai-Manager.git

---

Made with love
