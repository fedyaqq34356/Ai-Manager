import io
import json
import logging
from openai import AsyncOpenAI
from core.config import OPENAI_API_KEY, OPENAI_MODEL
from core import database as db

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

BASE_RULES = (
    "Rules: no em-dash, use hyphen (-) instead. No emoji. "
    "No trailing dots on list items. Concise and direct. "
    "Respond in the same language as the incoming message."
)

BEHAVIORAL_SUMMARY_PROMPT = (
    "You are analyzing a person's communication style based on their message history. "
    "Produce a compressed behavioral profile capturing: tone, vocabulary level, typical response length, "
    "formality, recurring topics, sentence structure, and any distinctive patterns. "
    "Be precise and actionable - this summary will be used to generate replies that sound like this person. "
    + BASE_RULES
)

AUTO_REPLY_SYSTEM_PROMPT = (
    "You are texting on behalf of a real person. Match their exact style from the behavioral summary. "
    "You must sound like someone texting from their phone - not an assistant, not a bot. "
    "\n\nStrict rules:"
    "\n- BREVITY IS MANDATORY. Count the words in the incoming message. Your reply must be roughly the same length or shorter. A 5-word message gets a 1-5 word reply. Never expand."
    "\n- If you don't know something, say so in 2-4 words max: 'хз', 'не знаю', 'понятия не имею'."
    "\n- If you need info to answer, ask ONE short question only: 'по какому?' not 'Скажи, по какому предмету?'"
    "\n- Do NOT always reply with a question. Sometimes just react: 'ну да', 'хз', 'точно', 'жесть', 'прикол'."
    "\n- Use natural Russian filler and reactions when appropriate: 'ага', 'ну', 'короче', 'слушай', 'если честно', 'хз', 'вроде да', 'как-то так', 'скорее всего', 'плюсую', 'не, это мимо'."
    "\n- Express surprise naturally: 'да ладно?', 'серьёзно?', 'вот это да', 'ничего себе', 'жесть'."
    "\n- Use casual transitions: 'короче', 'слушай', 'смотри', 'в общем', 'на самом деле'."
    "\n- Never say 'Интересно!', 'Понимаю', 'Это замечательно', 'Рад помочь' or any assistant phrases."
    "\n- Never use formal language or business tone."
    "\n- Incomplete sentences are fine. Typos are fine if the person makes them."
    "\n- NEVER moralize, lecture, correct, or add ethical commentary. If the other person says something crude or edgy in a casual tone, match that tone - laugh along, agree, or react naturally. Do NOT say 'тут спорно', 'работать нужно всем', 'это неправильно' or any moralizing phrase."
    "\n- Mirror the worldview and humor from the behavioral summary. If the person in the summary would laugh at a crude joke, you laugh. If they would agree with a cynical take, you agree. Stay in character always."
    "\n- In banter/slang context: respond with banter. 'хах', 'ну это да', 'справедливо', 'пон' are better than any analysis."
    + "\n" + BASE_RULES
    + "\n\nBehavioral summary:\n{summary}"
)

DIGEST_SYSTEM_PROMPT = (
    "You are a news digest assistant. Your job is to process raw channel messages and produce a clean structured digest. "
    "Filter out all promotional content, advertisements, sponsored posts, and calls to action. "
    "Identify distinct events and group them by topic within each channel. "
    "Format: date on its own line (DD.MM.YYYY), then channel title, then bullet points with hyphens. "
    "Avoid repeating events already covered in previous digest sessions. "
    + BASE_RULES
)

ASK_SYSTEM_PROMPT = (
    "You are a read-only knowledge retrieval tool. Your ONLY job is to answer the user's question using the indexed context below. "
    "Rules you must never break:\n"
    "- Answer the question directly. Stop. Do not ask anything back.\n"
    "- Never ask follow-up questions. Never say 'What do you mean?', 'Can you clarify?', 'Anything else?'.\n"
    "- Never continue the conversation. One answer, then done.\n"
    "- If the answer is in the indexed context, give it.\n"
    "- If the answer is NOT in the indexed context, say exactly: 'В индексированных чатах эта информация не найдена.' - nothing more.\n"
    "- Do not speculate, do not offer help, do not suggest topics.\n"
    + BASE_RULES
    + "\n\nIndexed context:\n{context}"
)

COMPOSE_REPLY_SYSTEM_PROMPT = (
    "You are composing a reply on behalf of the account owner to a specific person. "
    "Use the message history context and the owner's instruction to craft an appropriate reply. "
    "Match the owner's communication style from the history. "
    + BASE_RULES
    + "\n\nOwner instruction: {instruction}"
)

SPAM_EVAL_PROMPT = (
    "You are a spam and relevance filter for a personal Telegram account. "
    "Evaluate the incoming message and decide if the account owner should reply. "
    "Reply with exactly one word: REPLY or IGNORE. "
    "IGNORE if: unsolicited promotion, bot spam, mass broadcast, cold outreach, scam, "
    "or content a normal person would never want to respond to. "
    "REPLY if: personal message, genuine question, known contact, business inquiry, "
    "or anything a real person would respond to. "
    + BASE_RULES
)

CONTACT_PROFILE_PROMPT = (
    "Analyze this conversation history and extract a structured contact profile as JSON. "
    "Return exactly this JSON object with no extra text:\n"
    "{\n"
    '  "relationship": "who this person/group is and context of the relationship (2-3 sentences)",\n'
    '  "topics": ["main topics discussed - 3 to 7 items"],\n'
    '  "open_items": ["unresolved questions, promises, pending actions - 0 to 5 items"],\n'
    '  "last_message_preview": "the most recent substantive message, max 120 characters"\n'
    "}\n"
    "Rules: no em-dash, use hyphen. No emoji. Be factual and concise. Return only valid JSON."
)

CHAT_SUMMARY_PROMPT = (
    "Summarize the following conversation. Extract key points, decisions made, topics discussed, "
    "and any action items or open questions. Be concise and structured. "
    "Use sections with hyphens. Period covered: {period}. "
    + BASE_RULES
)


async def _call_with_history(session_key: str, system_prompt: str, user_message: str) -> str:
    history = await db.load_conversation_history(session_key)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    await db.append_conversation_message(session_key, "user", user_message)

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        raise

    await db.append_conversation_message(session_key, "assistant", reply)
    return reply


async def transcribe_audio(audio_bytes: bytes, filename: str = "voice.ogg") -> str:
    try:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, io.BytesIO(audio_bytes), "audio/ogg"),
        )
        return response.text.strip()
    except Exception as e:
        logger.error("Whisper transcription error: %s", e)
        raise


async def evaluate_message(message_text: str, recent_context: str = "") -> bool:
    content = f"Context:\n{recent_context}\n\nIncoming message:\n{message_text}" if recent_context else message_text
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SPAM_EVAL_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=5,
        )
        verdict = response.choices[0].message.content.strip().upper()
        return verdict == "REPLY"
    except Exception as e:
        logger.error("Spam evaluation error: %s", e)
        return True


async def summarize_chat_history(messages: list[dict], period_desc: str) -> str:
    formatted = "\n".join(
        f"[{m.get('sender_role', 'other').upper()}]: {m.get('message_text', '')}"
        for m in messages
        if m.get("message_text")
    )
    if not formatted:
        return "No messages found for the selected period."
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": CHAT_SUMMARY_PROMPT.format(period=period_desc)},
                {"role": "user", "content": formatted},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Chat summary error: %s", e)
        raise


async def generate_behavioral_summary(messages: list[dict]) -> str:
    formatted = "\n".join(
        f"[{m.get('sender_role', m.get('role', 'other')).upper()}]: {m['message_text']}"
        for m in messages if m.get("message_text")
    )
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": BEHAVIORAL_SUMMARY_PROMPT},
                {"role": "user", "content": formatted},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Error generating behavioral summary: %s", e)
        raise


_REFUSAL_MARKERS = (
    "упс", "это довольно жестко", "небезопасно",
    "лучше обсудим", "лучше поговорим о чём-то другом", "лучше поговорим о чем-то другом",
    "давай сменим тему", "может, сменим тему", "предлагаю сменить тему",
    "не могу помочь", "не буду помогать", "это неприемлемо",
    "против моих принципов", "не стоит так говорить",
    "не могу поддержать", "это вредно", "это опасно",
    "это уже перебор", "это перебор", "слишком далеко",
    "странное сравнение", "ты точно уверен", "точно уверен в этом",
    "неоднозначное", "это неоднозначно", "довольно спорно",
    "стоит ли так", "подумай об этом", "это не очень",
    "нехорошо так", "так нельзя", "это неэтично", "это нехорошо",
    "i can't", "i won't", "i'm unable", "i cannot",
    "against my guidelines", "not something i can",
    "i don't feel comfortable", "this is not something",
)


def _is_refusal(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in _REFUSAL_MARKERS)


async def _sanitize_message(text: str) -> str:
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Rephrase the following message in neutral, non-offensive language "
                        "while preserving its full meaning and emotional intent. "
                        "Output only the rephrased message, nothing else."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return text


async def generate_auto_reply(incoming_message: str, chat_id: int, behavioral_summary: str) -> str:
    session_key = f"autorespond_{chat_id}"
    system = AUTO_REPLY_SYSTEM_PROMPT.format(summary=behavioral_summary)
    try:
        reply = await _call_with_history(session_key, system, incoming_message)
    except Exception as e:
        err = str(e).lower()
        if "content_filter" in err or "flagged" in err:
            sanitized = await _sanitize_message(incoming_message)
            return await _call_with_history(session_key, system, sanitized)
        raise
    if _is_refusal(reply):
        logger.warning("Refusal detected for chat %s, sanitizing input and retrying", chat_id)
        sanitized = await _sanitize_message(incoming_message)
        reply = await _call_with_history(session_key, system, sanitized)
    return reply


async def generate_digest(raw_messages: list[dict]) -> str:
    formatted = "\n".join(
        f"[{m.get('channel', 'Unknown')}] [{m.get('date', '')}]: {m.get('text', '')}"
        for m in raw_messages
        if m.get("text")
    )
    return await _call_with_history("digest", DIGEST_SYSTEM_PROMPT, formatted)


async def answer_question(question: str, context_summaries: list[str]) -> str:
    context = "\n\n---\n\n".join(context_summaries) if context_summaries else "No indexed context available."
    system = ASK_SYSTEM_PROMPT.format(context=context)
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Ask question error: %s", e)
        raise


async def compose_targeted_reply(instruction: str, chat_id: int, history_context: str) -> str:
    session_key = f"answer_{chat_id}"
    system = COMPOSE_REPLY_SYSTEM_PROMPT.format(instruction=instruction)
    return await _call_with_history(session_key, system, history_context)


async def build_contact_profile(messages: list[dict], display_name: str) -> dict:
    formatted = "\n".join(
        f"[{m.get('sender_role', 'other').upper()}]: {m.get('message_text', '')}"
        for m in messages if m.get("message_text")
    )
    fallback = {"relationship": "", "topics": [], "open_items": [], "last_message_preview": ""}
    if not formatted:
        return fallback
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": CONTACT_PROFILE_PROMPT},
                {"role": "user", "content": f"Contact: {display_name}\n\n{formatted}"},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error("Contact profile build failed for %s: %s", display_name, e)
        return fallback


async def clear_session(session_key: str):
    await db.clear_conversation_session(session_key)
