import aiosqlite
import logging
from datetime import datetime
from core.security import encrypt, decrypt

DB_PATH = "ai_manager.db"
logger = logging.getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS learned_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                chat_title TEXT NOT NULL,
                selected_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                sender_role TEXT NOT NULL,
                message_text TEXT NOT NULL,
                sent_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS autorespond_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                chat_title TEXT NOT NULL,
                is_new_only INTEGER NOT NULL DEFAULT 0,
                enabled_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS parsed_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER UNIQUE NOT NULL,
                channel_title TEXT NOT NULL,
                channel_username TEXT,
                added_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS digest_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER UNIQUE NOT NULL,
                last_requested_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS qa_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                summary_text TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                username TEXT,
                relationship TEXT,
                topics TEXT,
                open_items TEXT,
                last_message_preview TEXT,
                last_interaction_at TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            INSERT OR IGNORE INTO settings (key, value) VALUES
                ('autoresponder_enabled', '1'),
                ('respond_unknown_chats', '0'),
                ('auto_leave_channels', '0'),
                ('voice_enabled', '1'),
                ('antispam_enabled', '0'),
                ('pause_if_owner_active', '0');
        """)
        await db.commit()


async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


async def get_encrypted_setting(key: str) -> str | None:
    raw = await get_setting(key)
    if raw is None:
        return None
    try:
        return decrypt(raw)
    except Exception:
        return None


async def set_encrypted_setting(key: str, value: str):
    await set_setting(key, encrypt(value))


async def add_learned_chat(chat_id: int, chat_title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO learned_chats (chat_id, chat_title, selected_at) VALUES (?, ?, ?)",
            (chat_id, chat_title, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def remove_learned_chat(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM learned_chats WHERE chat_id = ?", (chat_id,))
        await db.commit()


async def get_learned_chats() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM learned_chats ORDER BY selected_at DESC") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def is_learned_chat(chat_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM learned_chats WHERE chat_id = ?", (chat_id,)) as cur:
            return await cur.fetchone() is not None


async def insert_chat_messages(chat_id: int, messages: list[dict]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO chat_messages (chat_id, sender_role, message_text, sent_at) VALUES (?, ?, ?, ?)",
            [(chat_id, m["role"], encrypt(m["text"]), m["sent_at"]) for m in messages],
        )
        await db.commit()


async def get_chat_messages(chat_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM chat_messages WHERE chat_id = ? ORDER BY sent_at ASC", (chat_id,)
        ) as cur:
            rows = await cur.fetchall()
            result = []
            for r in rows:
                row = dict(r)
                try:
                    row["message_text"] = decrypt(row["message_text"])
                except Exception:
                    pass
                result.append(row)
            return result


async def clear_chat_messages(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM chat_messages WHERE chat_id = ?", (chat_id,))
        await db.commit()


async def add_autorespond_chat(chat_id: int, chat_title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO autorespond_chats (chat_id, chat_title, is_new_only, enabled_at) VALUES (?, ?, 0, ?)",
            (chat_id, chat_title, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def remove_autorespond_chat(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM autorespond_chats WHERE chat_id = ?", (chat_id,))
        await db.commit()


async def get_autorespond_chats() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM autorespond_chats ORDER BY enabled_at DESC") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def is_autorespond_chat(chat_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM autorespond_chats WHERE chat_id = ?", (chat_id,)) as cur:
            return await cur.fetchone() is not None


async def clear_autorespond_chats():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM autorespond_chats")
        await db.commit()


async def add_parsed_channel(channel_id: int, channel_title: str, channel_username: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO parsed_channels (channel_id, channel_title, channel_username, added_at) VALUES (?, ?, ?, ?)",
            (channel_id, channel_title, channel_username, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def remove_parsed_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM parsed_channels WHERE channel_id = ?", (channel_id,))
        await db.commit()


async def get_parsed_channels() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM parsed_channels ORDER BY added_at DESC") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def clear_parsed_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM parsed_channels")
        await db.commit()


async def get_last_digest_time(owner_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_requested_at FROM digest_log WHERE owner_id = ?", (owner_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def update_digest_time(owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO digest_log (owner_id, last_requested_at) VALUES (?, ?) "
            "ON CONFLICT(owner_id) DO UPDATE SET last_requested_at = excluded.last_requested_at",
            (owner_id, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def upsert_qa_context(chat_id: int, summary_text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO qa_context (chat_id, summary_text, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET summary_text = excluded.summary_text, updated_at = excluded.updated_at",
            (chat_id, encrypt(summary_text), datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_qa_context(chat_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT summary_text FROM qa_context WHERE chat_id = ?", (chat_id,)
        ) as cur:
            row = await cur.fetchone()
            if row is None:
                return None
            try:
                return decrypt(row[0])
            except Exception:
                return row[0]


async def get_all_qa_contexts() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT summary_text FROM qa_context ORDER BY updated_at DESC") as cur:
            rows = await cur.fetchall()
            result = []
            for r in rows:
                try:
                    result.append(decrypt(r[0]))
                except Exception:
                    result.append(r[0])
            return result


async def load_conversation_history(session_key: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role, content FROM ai_conversation_history WHERE session_key = ? ORDER BY id ASC",
            (session_key,),
        ) as cur:
            rows = await cur.fetchall()
            result = []
            for r in rows:
                try:
                    content = decrypt(r[1])
                except Exception:
                    content = r[1]
                result.append({"role": r[0], "content": content})
            return result


async def append_conversation_message(session_key: str, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ai_conversation_history (session_key, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_key, role, encrypt(content), datetime.utcnow().isoformat()),
        )
        await db.commit()


async def clear_conversation_session(session_key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM ai_conversation_history WHERE session_key = ?", (session_key,)
        )
        await db.commit()


async def clear_all_learned_chats():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM learned_chats")
        await db.execute("DELETE FROM chat_messages")
        await db.execute("DELETE FROM qa_context")
        await db.commit()


async def upsert_contact(
    chat_id: int,
    display_name: str,
    username: str | None,
    relationship: str,
    topics: str,
    open_items: str,
    last_message_preview: str,
    last_interaction_at: str,
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO contacts
                (chat_id, display_name, username, relationship, topics, open_items,
                 last_message_preview, last_interaction_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                display_name = excluded.display_name,
                username = excluded.username,
                relationship = excluded.relationship,
                topics = excluded.topics,
                open_items = excluded.open_items,
                last_message_preview = excluded.last_message_preview,
                last_interaction_at = excluded.last_interaction_at,
                updated_at = excluded.updated_at
            """,
            (
                chat_id, display_name, username,
                encrypt(relationship), encrypt(topics), encrypt(open_items),
                encrypt(last_message_preview), last_interaction_at,
                datetime.utcnow().isoformat(),
            ),
        )
        await db.commit()


async def get_all_contacts() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM contacts ORDER BY last_interaction_at DESC NULLS LAST"
        ) as cur:
            rows = await cur.fetchall()
            result = []
            for r in rows:
                c = dict(r)
                for field in ("relationship", "topics", "open_items", "last_message_preview"):
                    if c.get(field):
                        try:
                            c[field] = decrypt(c[field])
                        except Exception:
                            pass
                result.append(c)
            return result


async def get_contact(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM contacts WHERE chat_id = ?", (chat_id,)) as cur:
            row = await cur.fetchone()
            if row is None:
                return None
            c = dict(row)
            for field in ("relationship", "topics", "open_items", "last_message_preview"):
                if c.get(field):
                    try:
                        c[field] = decrypt(c[field])
                    except Exception:
                        pass
            return c


async def delete_contact(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM contacts WHERE chat_id = ?", (chat_id,))
        await db.commit()
