from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from core.config import DIALOGS_PAGE_SIZE

# Тексты кнопок главного меню (используются как константы во всех хендлерах)
BTN_LEARN = "Обучить чатам"
BTN_AUTORESPOND = "Авто-ответчик"
BTN_CHANNELS = "Каналы"
BTN_DIGEST = "Что произошло"
BTN_ASK = "Спросить"
BTN_SUMMARIZE = "Саммари чата"
BTN_CRM = "Контакты"
BTN_SETTINGS = "Настройки"

SUMMARIZE_PERIODS = [
    ("1 час", "1h"),
    ("24 часа", "24h"),
    ("7 дней", "7d"),
    ("30 дней", "30d"),
]


def main_menu_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LEARN), KeyboardButton(text=BTN_AUTORESPOND)],
            [KeyboardButton(text=BTN_CHANNELS), KeyboardButton(text=BTN_DIGEST)],
            [KeyboardButton(text=BTN_ASK), KeyboardButton(text=BTN_SUMMARIZE)],
            [KeyboardButton(text=BTN_CRM), KeyboardButton(text=BTN_SETTINGS)],
        ],
        resize_keyboard=True,
    )


def back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Главное меню", callback_data="menu:main")],
    ])


def dialogs_kb(
    dialogs: list[dict],
    selected_ids: set[int],
    page: int,
    prefix: str,
    confirm_data: str | None = None,
) -> InlineKeyboardMarkup:
    start = page * DIALOGS_PAGE_SIZE
    end = start + DIALOGS_PAGE_SIZE
    page_items = dialogs[start:end]

    rows = []
    for d in page_items:
        cid = d["id"]
        mark = "- " if cid in selected_ids else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{mark}{d['title']}",
                callback_data=f"{prefix}:toggle:{cid}:{page}",
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"{prefix}:page:{page - 1}"))
    if end < len(dialogs):
        nav.append(InlineKeyboardButton(text="Далее", callback_data=f"{prefix}:page:{page + 1}"))
    if nav:
        rows.append(nav)

    bottom = []
    if confirm_data:
        bottom.append(InlineKeyboardButton(text="Подтвердить выбор", callback_data=confirm_data))
    bottom.append(InlineKeyboardButton(text="Главное меню", callback_data="menu:main"))
    rows.append(bottom)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def summarize_dialogs_kb(dialogs: list[dict], page: int) -> InlineKeyboardMarkup:
    start = page * DIALOGS_PAGE_SIZE
    end = start + DIALOGS_PAGE_SIZE
    page_items = dialogs[start:end]

    rows = []
    for d in page_items:
        rows.append([
            InlineKeyboardButton(
                text=d["title"],
                callback_data=f"summarize:chat:{d['id']}:{page}",
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"summarize:page:{page - 1}"))
    if end < len(dialogs):
        nav.append(InlineKeyboardButton(text="Далее", callback_data=f"summarize:page:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="Главное меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def summarize_period_kb(chat_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"summarize:period:{chat_id}:{code}")]
        for label, code in SUMMARIZE_PERIODS
    ]
    rows.append([InlineKeyboardButton(text="Главное меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channels_list_kb(channels: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        rows.append([
            InlineKeyboardButton(text=ch["channel_title"], callback_data="noop"),
            InlineKeyboardButton(text="Удалить", callback_data=f"channels:remove:{ch['channel_id']}"),
        ])
    rows.append([InlineKeyboardButton(text="Добавить канал", callback_data="channels:add")])
    rows.append([InlineKeyboardButton(text="Главное меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_reply_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Отправить", callback_data="answer:confirm"),
            InlineKeyboardButton(text="Редактировать", callback_data="answer:edit"),
            InlineKeyboardButton(text="Отмена", callback_data="menu:main"),
        ]
    ])


def settings_kb(
    autoresponder_on: bool,
    respond_unknown: bool,
    auto_leave: bool,
    voice_on: bool,
    antispam_on: bool,
    pause_if_active: bool = False,
) -> InlineKeyboardMarkup:
    def tog(val: bool) -> str:
        return "ВКЛ" if val else "ВЫКЛ"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Авто-ответчик: {tog(autoresponder_on)}",
            callback_data="settings:toggle:autoresponder_enabled",
        )],
        [InlineKeyboardButton(
            text=f"Отвечать незнакомцам: {tog(respond_unknown)}",
            callback_data="settings:toggle:respond_unknown_chats",
        )],
        [InlineKeyboardButton(
            text=f"Авто-выход из каналов: {tog(auto_leave)}",
            callback_data="settings:toggle:auto_leave_channels",
        )],
        [InlineKeyboardButton(
            text=f"Голосовые сообщения: {tog(voice_on)}",
            callback_data="settings:toggle:voice_enabled",
        )],
        [InlineKeyboardButton(
            text=f"Анти-спам фильтр: {tog(antispam_on)}",
            callback_data="settings:toggle:antispam_enabled",
        )],
        [InlineKeyboardButton(
            text=f"Пауза если я пишу сам: {tog(pause_if_active)}",
            callback_data="settings:toggle:pause_if_owner_active",
        )],
        [InlineKeyboardButton(text="Очистить обученные чаты", callback_data="settings:clear:learned")],
        [InlineKeyboardButton(text="Очистить авто-ответчик", callback_data="settings:clear:autorespond")],
        [InlineKeyboardButton(text="Очистить каналы", callback_data="settings:clear:channels")],
        [InlineKeyboardButton(text="Сбросить память AI: дайджест", callback_data="settings:reset_ai:digest")],
        [InlineKeyboardButton(text="Сбросить память AI: вопросы", callback_data="settings:reset_ai:ask")],
        [InlineKeyboardButton(text="Главное меню", callback_data="menu:main")],
    ])


def ask_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить кому-то", callback_data="answer:start")],
        [InlineKeyboardButton(text="Главное меню", callback_data="menu:main")],
    ])


def contacts_list_kb(contacts: list[dict], page: int) -> InlineKeyboardMarkup:
    start = page * DIALOGS_PAGE_SIZE
    end = start + DIALOGS_PAGE_SIZE
    page_items = contacts[start:end]

    rows = []
    for c in page_items:
        last_dt = ""
        if c.get("last_interaction_at"):
            try:
                dt = datetime.fromisoformat(c["last_interaction_at"])
                last_dt = f"  {dt.strftime('%d.%m.%y')}"
            except Exception:
                pass
        rows.append([
            InlineKeyboardButton(
                text=f"{c['display_name']}{last_dt}",
                callback_data=f"crm:view:{c['chat_id']}",
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"crm:page:{page - 1}"))
    if end < len(contacts):
        nav.append(InlineKeyboardButton(text="Далее", callback_data=f"crm:page:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="Сканировать все чаты", callback_data="crm:scan_all")])
    rows.append([InlineKeyboardButton(text="Главное меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def contact_card_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Ответить", callback_data=f"crm:reply:{chat_id}"),
            InlineKeyboardButton(text="Обновить", callback_data=f"crm:refresh:{chat_id}"),
        ],
        [InlineKeyboardButton(text="К контактам", callback_data="menu:crm")],
        [InlineKeyboardButton(text="Главное меню", callback_data="menu:main")],
    ])
