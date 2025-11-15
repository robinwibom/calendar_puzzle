# pieces.py
# Piece definitions + rotations/flips

from __future__ import annotations

from typing import Iterable

# Canonical piece shapes as sets of (row, col)
PIECE_SHAPES: dict[str, set[tuple[int, int]]] = {
    "A": {(0, 0), (0, 1), (1, 0), (1, 1)},
    "B": {(0, 0), (0, 1), (0, 2), (0, 3), (1, 0)},
    "C": {(0, 2), (1, 0), (1, 1), (1, 2), (2, 0)},
    "D": {(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)},
    "E": {(0, 1), (1, 0), (1, 1), (2, 0)},
    "F": {(0, 0), (0, 1), (0, 2), (1, 0), (1, 2)},
    "G": {(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)},
    "H": {(0, 0), (0, 1), (0, 2), (1, 0)},
    "I": {(0, 0), (0, 1), (0, 2), (1, 1)},
}


def _normalize(shape: Iterable[tuple[int, int]]) -> frozenset[tuple[int, int]]:
    xs = [r for r, _ in shape]
    ys = [c for _, c in shape]
    min_r, min_c = min(xs), min(ys)
    return frozenset((r - min_r, c - min_c) for r, c in shape)


def _rotate90(shape: Iterable[tuple[int, int]]) -> set[tuple[int, int]]:
    # (r, c) -> (c, -r)
    return {(c, -r) for r, c in shape}


def _flip_horizontal(shape: Iterable[tuple[int, int]]) -> set[tuple[int, int]]:
    # (r, c) -> (r, -c)
    return {(r, -c) for r, c in shape}


def generate_orientations(shape: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    """All unique rotations + horizontal flip orientations, normalized to (0,0)."""
    seen: set[frozenset[tuple[int, int]]] = set()
    result: list[set[tuple[int, int]]] = []

    variants = [shape]
    # Rotations
    for _ in range(3):
        variants.append(_rotate90(variants[-1]))

    # Flips (flip base shape, then rotate)
    flipped = _flip_horizontal(shape)
    variants.append(flipped)
    for _ in range(3):
        variants.append(_rotate90(variants[-1]))

    for v in variants:
        norm = _normalize(v)
        if norm not in seen:
            seen.add(norm)
            result.append(set(norm))

    return result


def all_piece_orientations() -> dict[str, list[set[tuple[int, int]]]]:
    return {name: generate_orientations(shape) for name, shape in PIECE_SHAPES.items()}
