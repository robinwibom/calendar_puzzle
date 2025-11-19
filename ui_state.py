from enum import Enum, auto

class UIState(Enum):
    MENU = auto()
    SOLVE_TODAY = auto()
    ALGORITHM_INTRO = auto()
    ALGORITHM_VIEW = auto()
    STATS = auto()

class AppState:
    def __init__(self):
        self.current_state = UIState.MENU
        self.selected_date = None  # (month, day)
        # Add other shared state here if needed
