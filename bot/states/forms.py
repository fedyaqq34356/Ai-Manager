from aiogram.fsm.state import State, StatesGroup


class LearnChatsState(StatesGroup):
    browsing = State()


class AutoRespondState(StatesGroup):
    browsing = State()


class ParseChannelState(StatesGroup):
    waiting_for_channel = State()
    browsing = State()


class AskState(StatesGroup):
    waiting_for_question = State()


class AnswerState(StatesGroup):
    waiting_for_contact = State()
    waiting_for_instruction = State()
    confirming = State()


class SettingsState(StatesGroup):
    main = State()


class SummarizeState(StatesGroup):
    selecting_chat = State()
    selecting_period = State()


class CRMState(StatesGroup):
    browsing = State()
