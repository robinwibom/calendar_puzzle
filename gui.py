# gui.py

from __future__ import annotations

import calendar
from typing import Dict, List, Tuple

import pygame

from board import (
    BOARD_ROWS,
    BOARD_COLS,
    MONTH_COORDS,
    DAY_COORDS,
    ILLEGAL_CELLS,
)
from placements import Placement

CELL_SIZE = 64
TOP_BAR_HEIGHT = 120

WINDOW_WIDTH = BOARD_COLS * CELL_SIZE
WINDOW_HEIGHT = BOARD_ROWS * CELL_SIZE + TOP_BAR_HEIGHT

# Colors – higher contrast, refined dark mode
BG = (15, 15, 17)
CARD_BG = (30, 30, 34)
GRID = (90, 90, 95)
TEXT_MAIN = (245, 245, 250)
TEXT_SECONDARY = (230, 230, 235)
ILLEGAL = (45, 45, 49)

DATE_BORDER = (220, 90, 90)

# More contrast, vivid colors
PIECE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "A": (60, 200, 80),
    "B": (45, 140, 255),
    "C": (255, 190, 60),
    "D": (190, 70, 210),
    "E": (90, 220, 220),
    "F": (250, 80, 80),
    "G": (210, 145, 50),
    "H": (110, 120, 255),
    "I": (255, 160, 210),
}


def _month_short_name(month: int) -> str:
    return calendar.month_abbr[month].title()


def draw_top_bar(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    label_font: pygame.font.Font,
    current_idx: int,
    total_solutions: int,
    month: int,
    day: int,
):
    pygame.draw.rect(screen, BG, (0, 0, WINDOW_WIDTH, TOP_BAR_HEIGHT))

    card_rect = pygame.Rect(16, 16, WINDOW_WIDTH - 32, TOP_BAR_HEIGHT - 32)
    pygame.draw.rect(screen, CARD_BG, card_rect, border_radius=16)

    title = "Calendar Puzzle"
    title_surf = title_font.render(title, True, TEXT_MAIN)
    screen.blit(title_surf, (card_rect.x + 20, card_rect.y + 12))

    month_name = _month_short_name(month)
    date_surf = label_font.render(f"{month_name} {day}", True, TEXT_MAIN)
    date_x = card_rect.right - date_surf.get_width() - 20
    screen.blit(date_surf, (date_x, card_rect.y + 12))

    sol_text = f"Solution {current_idx + 1} of {total_solutions}"
    sol_surf = label_font.render(sol_text, True, TEXT_SECONDARY)
    screen.blit(sol_surf, (card_rect.x + 20, card_rect.y + 48))


def draw_solution_grid(
    screen: pygame.Surface,
    cell_font: pygame.font.Font,
    solution: List[Placement],
    month: int,
    day: int,
    alpha: int,
):
    """Draws the board. Movable blocks fade with alpha. Date cells remain fully opaque."""
    piece_map: Dict[Tuple[int, int], str] = {}
    for placement in solution:
        for cell in placement.cells:
            piece_map[cell] = placement.piece

    month_cell = MONTH_COORDS[month]
    day_cell = DAY_COORDS[day]
    month_label = _month_short_name(month).upper()
    day_label = str(day)

    # Separate surface so we can fade only the movable blocks
    fade_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    fade_surface.fill((0, 0, 0, 0))

    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            x = c * CELL_SIZE
            y = TOP_BAR_HEIGHT + r * CELL_SIZE

            rect = pygame.Rect(x + 2, y + 2, CELL_SIZE - 4, CELL_SIZE - 4)

            # Illegal
            if (r, c) in ILLEGAL_CELLS:
                pygame.draw.rect(screen, ILLEGAL, rect, border_radius=12)
                continue

            # Date cells – static, no fade
            if (r, c) == month_cell:
                pygame.draw.rect(screen, BG, rect, border_radius=12)
                pygame.draw.rect(screen, DATE_BORDER, rect, width=2, border_radius=12)
                text_surf = cell_font.render(month_label, True, TEXT_MAIN)
                screen.blit(
                    text_surf,
                    (
                        x + (CELL_SIZE - text_surf.get_width()) // 2,
                        y + (CELL_SIZE - text_surf.get_height()) // 2,
                    ),
                )
                continue

            if (r, c) == day_cell:
                pygame.draw.rect(screen, BG, rect, border_radius=12)
                pygame.draw.rect(screen, DATE_BORDER, rect, width=2, border_radius=12)
                text_surf = cell_font.render(day_label, True, TEXT_MAIN)
                screen.blit(
                    text_surf,
                    (
                        x + (CELL_SIZE - text_surf.get_width()) // 2,
                        y + (CELL_SIZE - text_surf.get_height()) // 2,
                    ),
                )
                continue

            # Movable blocks (fade)
            if (r, c) in piece_map:
                piece = piece_map[(r, c)]
                color = PIECE_COLORS[piece]
                col = (*color, alpha)  # add alpha
                pygame.draw.rect(fade_surface, col, rect, border_radius=12)

                # Create a letter surface with per-pixel alpha
                letter_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                letter_surface.fill((0, 0, 0, 0))  # fully transparent base

                # Render text normally (opaque) into a temp surface
                temp_text = cell_font.render(piece, True, (255, 255, 255))

                # Apply our fade alpha manually
                alpha_text = temp_text.copy()
                alpha_text.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)

                # Blit the faded text onto our letter surface
                letter_surface.blit(
                    alpha_text,
                    (
                        (CELL_SIZE - alpha_text.get_width()) // 2,
                        (CELL_SIZE - alpha_text.get_height()) // 2,
                    ),
                )

                # Add letter surface to fade_surface
                fade_surface.blit(letter_surface, (x, y))
            else:
                # Empty playable cell
                pygame.draw.rect(screen, BG, rect, border_radius=12)
                pygame.draw.rect(screen, GRID, rect, width=1, border_radius=12)

    # Overlay the fade surface
    screen.blit(fade_surface, (0, 0))


def show_solutions(
    solutions: List[List[Placement]],
    month: int,
    day: int,
):
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Calendar Puzzle")

    title_font = pygame.font.SysFont("SF Pro Display", 32, bold=True)
    label_font = pygame.font.SysFont("SF Pro Text", 24)
    cell_font = pygame.font.SysFont("SF Pro Text", 24, bold=True)

    clock = pygame.time.Clock()
    total_solutions = len(solutions)
    current_idx = 0

    anim_time = 0.4  # total fade duration (seconds)
    anim_progress: float | None = None
    fade_out = True
    next_idx = current_idx

    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN and anim_progress is None:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key == pygame.K_RIGHT and current_idx < total_solutions - 1:
                    next_idx = current_idx + 1
                    anim_progress = 0
                    fade_out = True

                if event.key == pygame.K_LEFT and current_idx > 0:
                    next_idx = current_idx - 1
                    anim_progress = 0
                    fade_out = True

        screen.fill(BG)
        draw_top_bar(screen, title_font, label_font, current_idx, total_solutions, month, day)

        if anim_progress is None:
            # No animation: draw current fully opaque
            draw_solution_grid(screen, cell_font, solutions[current_idx], month, day, alpha=255)

        else:
            anim_progress += dt

            if fade_out:
                # Fade out current solution
                alpha = max(0, int(255 * (1 - anim_progress / (anim_time / 2))))
                draw_solution_grid(screen, cell_font, solutions[current_idx], month, day, alpha)
                if anim_progress >= anim_time / 2:
                    fade_out = False
                    anim_progress = 0

            else:
                # Fade in next solution
                alpha = min(255, int(255 * (anim_progress / (anim_time / 2))))
                draw_solution_grid(screen, cell_font, solutions[next_idx], month, day, alpha)
                if anim_progress >= anim_time / 2:
                    anim_progress = None
                    current_idx = next_idx

        pygame.display.flip()

    pygame.quit()
