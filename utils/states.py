"""FSM состояния для бота"""

from aiogram.fsm.state import State, StatesGroup


class PostSelectionState(StatesGroup):
    """Состояния для выбора поста"""

    waiting_for_selection = State()
