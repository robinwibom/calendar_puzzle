import pygame
from gui import WINDOW_WIDTH, WINDOW_HEIGHT, BG, TEXT_MAIN, TEXT_SECONDARY, CARD_BG, GRID

def draw_intro(screen: pygame.Surface, title_font: pygame.font.Font, body_font: pygame.font.Font):
    screen.fill(BG)
    w, h = screen.get_size()
    
    # Title
    title = title_font.render("How it Works: Dancing Links", True, TEXT_MAIN)
    screen.blit(title, (40, 40))
    
    # Content
    lines = [
        "The puzzle is solved using an algorithm called 'Dancing Links' (DLX).",
        "",
        "1. The Matrix:",
        "   Imagine a giant grid where:",
        "   - ROWS represent every possible position of every piece.",
        "   - COLUMNS represent the days on the board.",
        "",
        "2. The Goal:",
        "   We need to select a set of ROWS such that every COLUMN",
        "   has exactly one '1' (is covered exactly once).",
        "",
        "3. The Dance:",
        "   The algorithm efficiently 'covers' columns and removes conflicting",
        "   rows, then 'backtracks' if it gets stuck.",
    ]
    
    y = 100
    for line in lines:
        surf = body_font.render(line, True, TEXT_SECONDARY)
        screen.blit(surf, (40, y))
        y += 30
        
    # Next Button
    button_rect = pygame.Rect(w - 160, h - 80, 120, 50)
    mouse_pos = pygame.mouse.get_pos()
    color = CARD_BG
    if button_rect.collidepoint(mouse_pos):
        color = (50, 50, 55)
        
    pygame.draw.rect(screen, color, button_rect, border_radius=8)
    pygame.draw.rect(screen, GRID, button_rect, width=1, border_radius=8)
    
    btn_text = body_font.render("Start >", True, TEXT_MAIN)
    text_rect = btn_text.get_rect(center=button_rect.center)
    screen.blit(btn_text, text_rect)

def get_intro_action(mouse_pos: tuple[int, int], screen_size: tuple[int, int]) -> str | None:
    w, h = screen_size
    button_rect = pygame.Rect(w - 160, h - 80, 120, 50)
    if button_rect.collidepoint(mouse_pos):
        return "start_viz"
    return None
