# placements.py
# Generate all valid piece placements on the board

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from board import BOARD_ROWS, BOARD_COLS


@dataclass(frozen=True)
class Placement:
    piece: str
    cells: tuple[tuple[int, int], ...]  # board coordinates covered by this placement


def generate_placements(
    playable_cells: set[tuple[int, int]],
    piece_orientations: dict[str, list[set[tuple[int, int]]]],
) -> list[Placement]:
    """Generate all valid placements of all pieces on the board."""
    placements: list[Placement] = []
    cell_set = playable_cells

    for piece_name, orientations in piece_orientations.items():
        for shape in orientations:
            max_r = max(r for r, _ in shape)
            max_c = max(c for _, c in shape)

            # Slide shape over the 7x7 board
            for dr in range(BOARD_ROWS - max_r):
                for dc in range(BOARD_COLS - max_c):
                    placed = {(r + dr, c + dc) for r, c in shape}
                    # Valid if all cells are inside playable region
                    if placed.issubset(cell_set):
                        placements.append(
                            Placement(
                                piece=piece_name,
                                cells=tuple(sorted(placed)),
                            )
                        )

    return placements
