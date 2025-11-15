# board.py
# Board geometry, month/day coordinate maps

from __future__ import annotations

BOARD_ROWS = 7
BOARD_COLS = 7

# Month coordinates (1–12)
MONTH_COORDS: dict[int, tuple[int, int]] = {
    1: (0, 0),
    2: (0, 1),
    3: (0, 2),
    4: (0, 3),
    5: (0, 4),
    6: (0, 5),
    7: (1, 0),
    8: (1, 1),
    9: (1, 2),
    10: (1, 3),
    11: (1, 4),
    12: (1, 5),
}

# Day coordinates (1–31)
DAY_COORDS: dict[int, tuple[int, int]] = {
    1: (2, 0),
    2: (2, 1),
    3: (2, 2),
    4: (2, 3),
    5: (2, 4),
    6: (2, 5),
    7: (2, 6),
    8: (3, 0),
    9: (3, 1),
    10: (3, 2),
    11: (3, 3),
    12: (3, 4),
    13: (3, 5),
    14: (3, 6),
    15: (4, 0),
    16: (4, 1),
    17: (4, 2),
    18: (4, 3),
    19: (4, 4),
    20: (4, 5),
    21: (4, 6),
    22: (5, 0),
    23: (5, 1),
    24: (5, 2),
    25: (5, 3),
    26: (5, 4),
    27: (5, 5),
    28: (5, 6),
    29: (6, 2),
    30: (6, 3),
    31: (6, 4),
}

# Illegal fixed X-cells on the board (pink corners etc.)
ILLEGAL_CELLS: set[tuple[int, int]] = {
    (0, 6),
    (1, 6),
    (6, 0),
    (6, 1),
    (6, 5),
    (6, 6),
}


def all_playable_cells() -> set[tuple[int, int]]:
    """All cells that can ever be covered by pieces (months + days)."""
    cells: set[tuple[int, int]] = set(MONTH_COORDS.values()) | set(DAY_COORDS.values())
    return cells


def playable_cells_for_date(month: int, day: int) -> set[tuple[int, int]]:
    """Playable cells when month/day squares are left empty."""
    cells = all_playable_cells().copy()
    month_cell = MONTH_COORDS[month]
    day_cell = DAY_COORDS[day]
    cells.discard(month_cell)
    cells.discard(day_cell)
    return cells
