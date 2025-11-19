# solver.py
# Combines everything; solves for a given date

from __future__ import annotations

from typing import Dict, List, Tuple

from board import playable_cells_for_date
from pieces import all_piece_orientations
from placements import generate_placements, Placement
from dlx import DLXSolver


def build_exact_cover(
    month: int,
    day: int,
) -> tuple[DLXSolver, List[Placement], List[str]]:
    # Board cells excluding the chosen month/day holes.
    playable = playable_cells_for_date(month, day)

    # Piece orientations.
    piece_orients = all_piece_orientations()

    # Generate placements.
    placements = generate_placements(playable, piece_orients)

    # Column mapping:
    # First piece columns, then cell columns.
    piece_names = sorted(piece_orients.keys())
    num_pieces = len(piece_names)

    piece_index: Dict[str, int] = {name: idx for idx, name in enumerate(piece_names)}

    cells_sorted = sorted(playable)
    cell_index: Dict[Tuple[int, int], int] = {
        coord: num_pieces + i for i, coord in enumerate(cells_sorted)
    }

    num_columns = num_pieces + len(cells_sorted)
    solver = DLXSolver(num_columns)
    
    # Generate column labels
    column_labels = piece_names + [f"({r},{c})" for r, c in cells_sorted]

    # Build rows.
    for row_id, placement in enumerate(placements):
        cols: List[int] = [piece_index[placement.piece]]
        cols.extend(cell_index[c] for c in placement.cells)
        solver.add_row(row_id, cols)

    return solver, placements, column_labels


def solve_for_date(month: int, day: int, find_all: bool = False):
    solver, placements, _ = build_exact_cover(month, day)

    if find_all:
        all_solutions = []
        for sol in solver.solve():
            all_solutions.append([placements[rid] for rid in sol])
        return all_solutions

    sol = solver.solve_one()
    if sol is None:
        return None
    return [[placements[rid] for rid in sol]]
