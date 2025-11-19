from __future__ import annotations
import pygame
from datetime import date
from typing import List, Optional

from solver import solve_for_date, DLXSolver
from gui import (
    WINDOW_WIDTH, WINDOW_HEIGHT, BG,
    draw_menu, get_menu_action,
    draw_top_bar, draw_solution_grid
)
from ui_state import AppState, UIState
from ui_intro import draw_intro, get_intro_action
from ui_viz import VizState, draw_viz, handle_viz_input
from placements import Placement

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Calendar Puzzle")
    
    # Fonts
    title_font = pygame.font.SysFont("SF Pro Display", 32, bold=True)
    label_font = pygame.font.SysFont("SF Pro Text", 24)
    cell_font = pygame.font.SysFont("SF Pro Text", 24, bold=True)
    button_font = pygame.font.SysFont("SF Pro Text", 20)
    body_font = pygame.font.SysFont("SF Pro Text", 18)

    clock = pygame.time.Clock()
    app_state = AppState()
    
    # State for Solve Today
    solutions: List[List[Placement]] = []
    current_sol_idx = 0
    anim_time = 0.4
    anim_progress: float | None = None
    fade_out = True
    next_sol_idx = 0
    
    # State for Algorithm View
    viz_state: VizState | None = None
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                
            if app_state.current_state == UIState.MENU:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    action = get_menu_action(event.pos, screen.get_size())
                    if action == "solve_today":
                        app_state.current_state = UIState.SOLVE_TODAY
                        today = date.today()
                        app_state.selected_date = (today.month, today.day)
                        print(f"Solving for {today}...")
                        found = solve_for_date(today.month, today.day, find_all=True)
                        solutions = found if found else []
                        current_sol_idx = 0
                        
                    elif action == "algorithm":
                        app_state.current_state = UIState.ALGORITHM_INTRO
                        
                    elif action == "stats":
                        print("Stats selected (not implemented)")

            elif app_state.current_state == UIState.ALGORITHM_INTRO:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    action = get_intro_action(event.pos, screen.get_size())
                    if action == "start_viz":
                        app_state.current_state = UIState.ALGORITHM_VIEW
                        today = date.today()
                        print("Initializing visualization...")
                        viz_state = VizState(today.month, today.day)

            elif app_state.current_state == UIState.ALGORITHM_VIEW:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        app_state.current_state = UIState.MENU
                        viz_state = None
                # Pass all events to viz input handler first
                action = handle_viz_input(event, viz_state, screen.get_size())
                
                if action == "prev":
                    viz_state.step_backward()
                elif action == "next":
                    viz_state.step_forward()
                elif action == "toggle":
                    viz_state.toggle_play()
                elif action == "menu":
                    app_state.current_state = UIState.MENU
                
                # Keep mouse wheel for convenience (optional, but good to keep)
                if event.type == pygame.MOUSEWHEEL:
                     if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                         viz_state.scroll_x(event.y * -1)
                     else:
                         viz_state.scroll_y(event.y * -1)

            elif app_state.current_state == UIState.SOLVE_TODAY:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        app_state.current_state = UIState.MENU
                        
                    if not solutions:
                        continue
                        
                    if anim_progress is None:
                        if event.key == pygame.K_RIGHT and current_sol_idx < len(solutions) - 1:
                            next_sol_idx = current_sol_idx + 1
                            anim_progress = 0
                            fade_out = True
                        elif event.key == pygame.K_LEFT and current_sol_idx > 0:
                            next_sol_idx = current_sol_idx - 1
                            anim_progress = 0
                            fade_out = True

        # Update
        if app_state.current_state == UIState.ALGORITHM_VIEW and viz_state:
            viz_state.update(dt)

        # Draw
        if app_state.current_state == UIState.MENU:
            draw_menu(screen, title_font, button_font)
            
        elif app_state.current_state == UIState.ALGORITHM_INTRO:
            draw_intro(screen, title_font, body_font)
            
        elif app_state.current_state == UIState.ALGORITHM_VIEW and viz_state:
            draw_viz(screen, title_font, body_font, viz_state)

        elif app_state.current_state == UIState.SOLVE_TODAY:
            screen.fill(BG)
            if app_state.selected_date:
                month, day = app_state.selected_date
                draw_top_bar(screen, title_font, label_font, current_sol_idx, len(solutions), month, day)
                
                if solutions:
                    if anim_progress is None:
                        draw_solution_grid(screen, cell_font, solutions[current_sol_idx], month, day, alpha=255)
                    else:
                        anim_progress += dt
                        if fade_out:
                            alpha = max(0, int(255 * (1 - anim_progress / (anim_time / 2))))
                            draw_solution_grid(screen, cell_font, solutions[current_sol_idx], month, day, alpha)
                            if anim_progress >= anim_time / 2:
                                fade_out = False
                                anim_progress = 0
                        else:
                            alpha = min(255, int(255 * (anim_progress / (anim_time / 2))))
                            draw_solution_grid(screen, cell_font, solutions[next_sol_idx], month, day, alpha)
                            if anim_progress >= anim_time / 2:
                                anim_progress = None
                                current_sol_idx = next_sol_idx
                else:
                    pass 

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
