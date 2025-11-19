import pygame
from typing import List, Dict, Any, Optional
from dlx import DLXSolver
from placements import Placement
from board import BOARD_ROWS, BOARD_COLS, MONTH_COORDS, DAY_COORDS, ILLEGAL_CELLS
from gui import (
    WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE, TOP_BAR_HEIGHT,
    BG, CARD_BG, GRID, TEXT_MAIN, TEXT_SECONDARY, PIECE_COLORS, ILLEGAL, DATE_BORDER,
    _month_short_name
)

# Colors for High IQ Mode
MATRIX_BG = (10, 10, 12)
MATRIX_HEADER_BG = (20, 20, 25)
MATRIX_ROW_HOVER = (30, 30, 35)
MATRIX_ROW_SELECTED = (40, 50, 40)
MATRIX_GRID = (40, 40, 45)
SCROLLBAR_BG = (20, 20, 22)
SCROLLBAR_FG = (60, 60, 65)
SCROLLBAR_HOVER = (80, 80, 85)

CONSTRAINT_PIECE = (100, 100, 255) # Blueish for piece constraints
CONSTRAINT_BOARD = (255, 200, 50)  # Yellowish for board constraints

class VizState:
    def __init__(self, month: int, day: int):
        self.month = month
        self.day = day
        
        # Initialize solver
        from solver import build_exact_cover
        self.solver, self.placements, self.column_labels = build_exact_cover(month, day)
        
        # Generate history in memory
        print("Generating history...")
        self.history = []
        # Manually iterate to stop after first solution
        for event in self.solver.solve_steps():
            self.history.append(event)
            if event["type"] == "SOLUTION":
                break
                
        self.history = self.process_history(self.history)
        print(f"History generated: {len(self.history)} steps.")
        
        self.total_steps = len(self.history)
        self.current_step = 0
        self.playing = False
        self.play_speed = 0.1 
        self.timer = 0.0
        self.step_timer = 0.0
        
        # Cache current event
        if self.history:
            self.current_event = self.history[0]
        else:
            # Fallback if no events (shouldn't happen)
            self.current_event = {"type": "INIT", "data": {}, "state": []}
        
        # Scroll state
        self.scroll_col_idx = 0.0
        self.target_scroll_col_idx = 0.0
        
        self.scroll_row_idx = 0.0
        self.target_scroll_row_idx = 0.0
        
        # Pre-calculate column -> rows mapping for visualization
        self.col_to_rows: Dict[int, List[int]] = {}
        self.label_to_index = {label: i for i, label in enumerate(self.column_labels)}
        
        # Identify split between Piece columns and Board columns
        self.num_piece_cols = 0
        for label in self.column_labels:
            if not isinstance(label, tuple):
                self.num_piece_cols += 1
            else:
                break
        
        # Generate descriptive row labels (keep for debug)
        self.row_labels: List[str] = []
        
        for row_id, placement in enumerate(self.placements):
            # Generate label
            min_r = min(r for r, c in placement.cells)
            min_c = min(c for r, c in placement.cells if r == min_r)
            self.row_labels.append(f"Piece {placement.piece} at ({min_r},{min_c})")
            
            # Piece column
            p_col = self.label_to_index[placement.piece]
            if p_col not in self.col_to_rows: self.col_to_rows[p_col] = []
            self.col_to_rows[p_col].append(row_id)
            
            # Cell columns
            for cell in placement.cells:
                c_label = f"({cell[0]},{cell[1]})"
                if c_label in self.label_to_index:
                    c_idx = self.label_to_index[c_label]
                    if c_idx not in self.col_to_rows: self.col_to_rows[c_idx] = []
                    self.col_to_rows[c_idx].append(row_id)

    def process_history(self, raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregates and enriches raw DLX events to create a smoother, book-like narrative.
        - Filters out COVER/UNCOVER noise.
        - Tracks recursion depth to add 'Option X of Y' context.
        """
        processed = []
        
        # Stack to track: {col_name, total_options, current_option_index}
        context_stack = []
        
        for event in raw_events:
            etype = event["type"]
            data = event.get("data", {})
            
            if etype == "INIT":
                processed.append(event)
                
            elif etype == "CHOOSE_COL":
                # Push new context
                context_stack.append({
                    "col": data["chosen"],
                    "total": data["size"],
                    "current": 0
                })
                processed.append(event)
                
            elif etype == "SELECT_ROW":
                # Increment current option index for the active column
                if context_stack:
                    context_stack[-1]["current"] += 1
                    
                    # Enrich event
                    ctx = context_stack[-1]
                    event["narrative_ctx"] = {
                        "col": ctx["col"],
                        "option_idx": ctx["current"],
                        "total_options": ctx["total"]
                    }
                processed.append(event)
                
            elif etype == "BACKTRACK":
                # Enrich with context if available
                if context_stack:
                    ctx = context_stack[-1]
                    event["narrative_ctx"] = {
                        "col": ctx["col"],
                        "total_options": ctx["total"]
                    }
                    
                    # CRITICAL FIX: If total options is 0, we return immediately in DLX,
                    # so UNCOVER_COL is never called. We must pop here.
                    if ctx["total"] == 0:
                        context_stack.pop()
                processed.append(event)
                
            elif etype == "UNCOVER_COL":
                # Pop context (we are done with this column)
                # Robustness: Pop until we find the matching column (handling any previous desyncs)
                while context_stack:
                    if context_stack[-1]["col"] == data["col"]:
                        context_stack.pop()
                        break
                    else:
                        # This shouldn't happen if logic is correct, but safe to clean up
                        context_stack.pop()
                # Don't yield this event
                
            elif etype == "UNSELECT_ROW":
                # Keep this for the "Backtracking..." visual
                processed.append(event)
                
            elif etype == "SOLUTION":
                processed.append(event)
                
            # Ignore COVER_COL
            
        return processed
        
    def update(self, dt: float):
        self.step_timer += dt
        if self.playing and self.current_step < self.total_steps - 1:
            self.timer += dt
            if self.timer >= self.play_speed:
                self.timer = 0
                self.set_step(self.current_step + 1)
        elif self.current_step >= self.total_steps - 1:
            self.playing = False
            
        # Smooth scroll X
        diff_x = self.target_scroll_col_idx - self.scroll_col_idx
        if abs(diff_x) > 0.1:
            self.scroll_col_idx += diff_x * dt * 10
        else:
            self.scroll_col_idx = self.target_scroll_col_idx

        # Smooth scroll Y
        diff_y = self.target_scroll_row_idx - self.scroll_row_idx
        if abs(diff_y) > 0.1:
            self.scroll_row_idx += diff_y * dt * 10
        else:
            self.scroll_row_idx = self.target_scroll_row_idx

    def set_step(self, step: int):
        self.current_step = step
        self.current_event = self.history[step]
        self.step_timer = 0.0
        
        # Auto-scroll to active column/row
        event = self.current_event
        data = event.get("data", {})
        
        # 1. Focus Column
        active_col_name = None
        if event["type"] in ("CHOOSE_COL", "COVER_COL", "UNCOVER_COL"):
            active_col_name = data.get("chosen") or data.get("col")
            
        if active_col_name:
            try:
                col_idx = self.column_labels.index(active_col_name)
                # Center the column (approximate, will be clamped in draw)
                self.target_scroll_col_idx = max(0, col_idx - 5) 
            except ValueError:
                pass

        # 2. Focus Row
        active_row = data.get("row")
        if active_row is not None:
            # We need to know where this row is in the *current view*.
            # Since we show ALL rows in the matrix (just scrolled), 
            # we can just scroll to the row index.
            self.target_scroll_row_idx = max(0, active_row - 5)

    def step_forward(self):
        if self.current_step < self.total_steps - 1:
            self.set_step(self.current_step + 1)

    def step_backward(self):
        if self.current_step > 0:
            self.set_step(self.current_step - 1)

    def toggle_play(self):
        self.playing = not self.playing
        
    def scroll_x(self, dx: float):
        self.target_scroll_col_idx = max(0, min(len(self.column_labels) - 1, self.target_scroll_col_idx + dx))

    def scroll_y(self, dy: float):
        self.target_scroll_row_idx = max(0, min(len(self.placements) - 1, self.target_scroll_row_idx + dy))

def draw_scrollbar(screen: pygame.Surface, rect: pygame.Rect, content_size: float, view_size: float, scroll_pos: float, vertical: bool = True):
    """Draws a scrollbar."""
    pygame.draw.rect(screen, SCROLLBAR_BG, rect)
    
    if content_size <= view_size:
        return # No scroll needed
        
    # Calculate thumb size and position
    ratio = view_size / content_size
    thumb_size = max(20, int((rect.height if vertical else rect.width) * ratio))
    
    track_len = (rect.height if vertical else rect.width) - thumb_size
    max_scroll = content_size - view_size
    scroll_ratio = scroll_pos / max_scroll if max_scroll > 0 else 0
    scroll_ratio = max(0.0, min(1.0, scroll_ratio))
    
    thumb_pos = int(track_len * scroll_ratio)
    
    if vertical:
        thumb_rect = pygame.Rect(rect.x + 2, rect.y + thumb_pos, rect.width - 4, thumb_size)
    else:
        thumb_rect = pygame.Rect(rect.x + thumb_pos, rect.y + 2, thumb_size, rect.height - 4)
        
    pygame.draw.rect(screen, SCROLLBAR_FG, thumb_rect, border_radius=4)


def draw_mini_piece_correct(screen: pygame.Surface, rect: pygame.Rect, placement: Placement):
    """
    Draws the piece shape on a mini-grid.
    Highlights the cells that correspond to the placement.
    """
    # 1. Determine Piece Shape Bounding Box (0,0 based)
    # We need the generic shape of the piece, not just this placement.
    # But actually, the placement *defines* the shape.
    # We just need to normalize it.
    
    cells = placement.cells
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    norm_cells = [(r - min_r, c - min_c) for r, c in cells]
    
    max_r = max(r for r, c in norm_cells)
    max_c = max(c for r, c in norm_cells)
    
    # Grid dimensions (e.g. 5x5 max for any pentomino)
    grid_w = max_c + 1
    grid_h = max_r + 1
    
    # Fit grid into rect
    padding = 6
    avail_w = rect.width - padding * 2
    avail_h = rect.height - padding * 2
    
    cell_s = min(avail_w / grid_w, avail_h / grid_h)
    cell_s = min(cell_s, 12) # Cap max size
    
    # Center the grid
    draw_w = grid_w * cell_s
    draw_h = grid_h * cell_s
    start_x = rect.x + (rect.width - draw_w) // 2
    start_y = rect.y + (rect.height - draw_h) // 2
    
    color = PIECE_COLORS[placement.piece]
    
    for r, c in norm_cells:
        r_rect = pygame.Rect(start_x + c * cell_s, start_y + r * cell_s, cell_s - 1, cell_s - 1)
        pygame.draw.rect(screen, color, r_rect)

def draw_shadow(screen: pygame.Surface, rect: pygame.Rect, vertical: bool = False, radius: int = 10):
    """Draws a gradient shadow."""
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    if vertical:
        # Shadow on the right
        for i in range(radius):
            alpha = int(100 * (1 - i/radius))
            pygame.draw.line(s, (0, 0, 0, alpha), (i, 0), (i, rect.height))
    else:
        # Shadow on the bottom
        for i in range(radius):
            alpha = int(100 * (1 - i/radius))
            pygame.draw.line(s, (0, 0, 0, alpha), (0, i), (rect.width, i))
    screen.blit(s, rect)

def draw_matrix(screen: pygame.Surface, rect: pygame.Rect, state: VizState, font: pygame.font.Font):
    """Draws the High IQ Matrix View."""
    # Background
    pygame.draw.rect(screen, MATRIX_BG, rect)
    
    # Dimensions
    HEADER_HEIGHT = 50
    ROW_LABEL_WIDTH = 80
    MIN_COL_WIDTH = 35
    MAX_COL_WIDTH = 80
    ROW_HEIGHT = 35
    SCROLLBAR_SIZE = 12
    
    # Viewport Area (excluding headers and scrollbars)
    view_rect = pygame.Rect(
        rect.x + ROW_LABEL_WIDTH, 
        rect.y + HEADER_HEIGHT, 
        rect.width - ROW_LABEL_WIDTH - SCROLLBAR_SIZE, 
        rect.height - HEADER_HEIGHT - SCROLLBAR_SIZE
    )
    
    # Data
    num_cols = len(state.column_labels)
    num_rows = len(state.placements)
    
    # Dynamic Column Width Calculation
    available_w = view_rect.width
    # Try to fit all columns
    dynamic_col_w = available_w / num_cols if num_cols > 0 else MIN_COL_WIDTH
    COL_WIDTH = max(MIN_COL_WIDTH, min(MAX_COL_WIDTH, int(dynamic_col_w)))
    
    # Centering Logic
    total_content_w = num_cols * COL_WIDTH
    centering_offset_x = 0
    if total_content_w < view_rect.width:
        centering_offset_x = (view_rect.width - total_content_w) // 2
    
    # Scroll Clamping
    max_scroll_x = max(0, num_cols - view_rect.width / COL_WIDTH)
    state.target_scroll_col_idx = max(0.0, min(max_scroll_x, state.target_scroll_col_idx))
    # Update scroll_col_idx if it drifted too far (e.g. resize)
    state.scroll_col_idx = max(0.0, min(max_scroll_x + 5, state.scroll_col_idx)) # +5 buffer

    max_scroll_y = max(0, num_rows - view_rect.height / ROW_HEIGHT)
    state.target_scroll_row_idx = max(0.0, min(max_scroll_y, state.target_scroll_row_idx))
    state.scroll_row_idx = max(0.0, min(max_scroll_y + 5, state.scroll_row_idx))

    # Visible Range
    start_col = int(state.scroll_col_idx)
    visible_cols = int(view_rect.width / COL_WIDTH) + 2
    end_col = min(num_cols, start_col + visible_cols)
    
    start_row = int(state.scroll_row_idx)
    visible_rows_count = int(view_rect.height / ROW_HEIGHT) + 2
    end_row = min(num_rows, start_row + visible_rows_count)
    
    # Offsets for smooth scrolling
    offset_x = int((state.scroll_col_idx - start_col) * COL_WIDTH) - centering_offset_x
    offset_y = int((state.scroll_row_idx - start_row) * ROW_HEIGHT)
    
    # --- Draw Grid & Content ---
    
    event = state.current_event
    data = event.get("data", {})
    current_solution_rows = set(event.get("state", []))
    active_row = data.get("row")
    
    active_col_idx = None
    candidate_cols_indices = []
    
    if event["type"] in ("CHOOSE_COL", "COVER_COL", "UNCOVER_COL"):
        active_col_idx = data.get("chosen") or data.get("col")
        if event["type"] == "CHOOSE_COL":
             # candidates are dicts with "name" (index) and "size"
             candidate_cols_indices = [c["name"] for c in data.get("candidates", [])]

    # Calculate Covered Columns (for dimming and header coloring)
    covered_cols_indices = set()
    for rid in current_solution_rows:
        p = state.placements[rid]
        # Piece col
        covered_cols_indices.add(state.label_to_index[p.piece])
        # Cell cols
        for r, c in p.cells:
            label = f"({r},{c})"
            if label in state.label_to_index:
                covered_cols_indices.add(state.label_to_index[label])

    # 1. Rows
    for r_idx in range(start_row, end_row):
        y = view_rect.y + (r_idx - start_row) * ROW_HEIGHT - offset_y
        
        # Clip Y
        if y < view_rect.y - ROW_HEIGHT: continue
        if y > view_rect.bottom: continue
        
        row_rect = pygame.Rect(rect.x, y, rect.width - SCROLLBAR_SIZE, ROW_HEIGHT)
        
        # Determine Row State
        placement = state.placements[r_idx]
        
        # Get columns for this row
        row_cols_indices = []
        row_cols_indices.append(state.label_to_index[placement.piece])
        for cell in placement.cells:
            c_label = f"({cell[0]},{cell[1]})"
            if c_label in state.label_to_index:
                row_cols_indices.append(state.label_to_index[c_label])
        
        is_selected = r_idx in current_solution_rows
        is_conflicting = False
        conflict_cols = []
        
        if not is_selected:
            # Check if it hits any covered column
            for c_idx in row_cols_indices:
                if c_idx in covered_cols_indices:
                    is_conflicting = True
                    conflict_cols.append(c_idx)
        
        # Row Background
        bg_color = MATRIX_BG
        
        if r_idx == active_row:
            bg_color = MATRIX_ROW_SELECTED
        elif is_selected:
            bg_color = (25, 55, 25) # Greenish
        elif is_conflicting:
            bg_color = (15, 15, 18) # Very dark/dim
        elif row_rect.collidepoint(pygame.mouse.get_pos()):
            bg_color = MATRIX_ROW_HOVER
            
        pygame.draw.rect(screen, bg_color, row_rect)
        pygame.draw.line(screen, MATRIX_GRID, (rect.x, y + ROW_HEIGHT), (rect.width - SCROLLBAR_SIZE, y + ROW_HEIGHT))
        
        # Row Header (Mini Piece)
        header_rect = pygame.Rect(rect.x, y, ROW_LABEL_WIDTH, ROW_HEIGHT)
        pygame.draw.rect(screen, MATRIX_HEADER_BG, header_rect)
        pygame.draw.line(screen, MATRIX_GRID, (header_rect.right, y), (header_rect.right, y + ROW_HEIGHT))
        
        draw_mini_piece_correct(screen, header_rect, state.placements[r_idx])
        
        if is_conflicting:
             s = pygame.Surface((ROW_LABEL_WIDTH, ROW_HEIGHT), pygame.SRCALPHA)
             s.fill((0, 0, 0, 150))
             screen.blit(s, header_rect)

        # Cells
        for c_idx in range(start_col, end_col):
            x = view_rect.x + (c_idx - start_col) * COL_WIDTH - offset_x
            
            # Clip X
            if x < view_rect.x - COL_WIDTH: continue
            if x > view_rect.right: continue
            
            cell_rect = pygame.Rect(x, y, COL_WIDTH, ROW_HEIGHT)
            
            # Vertical Grid Line
            pygame.draw.line(screen, MATRIX_GRID, (x + COL_WIDTH, y), (x + COL_WIDTH, y + ROW_HEIGHT))
            
            # Draw '1's
            if c_idx in row_cols_indices:
                is_piece_col = c_idx < state.num_piece_cols
                
                color = CONSTRAINT_PIECE if is_piece_col else CONSTRAINT_BOARD
                
                # Conflict Visualization: Red '1' if this specific column is the cause
                if c_idx in conflict_cols:
                    color = (255, 50, 50) # RED for conflict
                elif is_conflicting:
                    color = (60, 60, 70) # Dimmed if row is conflicting but this col isn't the cause (unlikely in exact cover, usually it IS the cause)
                
                if is_piece_col:
                    center = cell_rect.center
                    pygame.draw.circle(screen, color, center, 4)
                else:
                    center = cell_rect.center
                    pygame.draw.rect(screen, color, (center[0]-3, center[1]-3, 6, 6))

    # 2. Column Headers (Floating on top)
    pygame.draw.rect(screen, MATRIX_HEADER_BG, (rect.x, rect.y, rect.width, HEADER_HEIGHT))
    pygame.draw.line(screen, MATRIX_GRID, (rect.x, rect.y + HEADER_HEIGHT), (rect.width, rect.y + HEADER_HEIGHT))
    
    # Corner
    pygame.draw.line(screen, MATRIX_GRID, (rect.x + ROW_LABEL_WIDTH, rect.y), (rect.x + ROW_LABEL_WIDTH, rect.y + HEADER_HEIGHT))
    
    for c_idx in range(start_col, end_col):
        x = view_rect.x + (c_idx - start_col) * COL_WIDTH - offset_x
        
        if x < view_rect.x - COL_WIDTH: continue
        if x > view_rect.right: continue
        
        col_rect = pygame.Rect(x, rect.y, COL_WIDTH, HEADER_HEIGHT)
        
        label = state.column_labels[c_idx]
        
        # Highlight active column
        if c_idx == active_col_idx:
            # Animation: Top-down wipe
            anim_progress = min(1.0, state.step_timer / 0.3) # 0.3s duration
            anim_height = int(col_rect.height * anim_progress)
            
            # Base highlight
            pygame.draw.rect(screen, (50, 50, 80), col_rect)
            
            # Animated "Glow" overlay
            glow_rect = pygame.Rect(col_rect.x, col_rect.y, col_rect.width, anim_height)
            s = pygame.Surface((col_rect.width, anim_height), pygame.SRCALPHA)
            s.fill((255, 255, 100, 30)) # Yellowish glow
            screen.blit(s, glow_rect)
        
        # Highlight Satisfied Columns (Greenish)
        elif c_idx in covered_cols_indices:
            pygame.draw.rect(screen, (20, 60, 20), col_rect) # Satisfied Green
            
        # Highlight candidate columns (lighter blue)
        elif c_idx in candidate_cols_indices:
             pygame.draw.rect(screen, (30, 30, 50), col_rect)
            
        pygame.draw.line(screen, MATRIX_GRID, (x + COL_WIDTH, rect.y), (x + COL_WIDTH, rect.y + HEADER_HEIGHT))
        
        # Draw Label
        # Top: Index
        idx_surf = font.render(str(c_idx), True, (100, 100, 100))
        screen.blit(idx_surf, idx_surf.get_rect(center=(col_rect.centerx, col_rect.y + 12)))
        
        # Bottom: Name
        name = str(label)
        if isinstance(label, tuple): name = f"{label[0]},{label[1]}"
        
        color = CONSTRAINT_PIECE if c_idx < state.num_piece_cols else CONSTRAINT_BOARD
        if c_idx in covered_cols_indices:
            color = (150, 255, 150) # Bright Green text for satisfied
            
        name_surf = font.render(name, True, color)
        if name_surf.get_width() > COL_WIDTH - 2:
             name_surf = pygame.transform.scale(name_surf, (COL_WIDTH - 2, name_surf.get_height()))
        screen.blit(name_surf, name_surf.get_rect(center=(col_rect.centerx, col_rect.y + 32)))
        
        # Separator between Piece and Board cols
        if c_idx == state.num_piece_cols - 1:
            pygame.draw.line(screen, (150, 150, 150), (x + COL_WIDTH, rect.y), (x + COL_WIDTH, rect.bottom), 2)

    # 3. Scrollbars
    # Vertical
    # Add a small top margin (4px) to make it look "floating" and intentional
    sb_y_rect = pygame.Rect(
        rect.right - SCROLLBAR_SIZE, 
        rect.y + HEADER_HEIGHT + 4, 
        SCROLLBAR_SIZE, 
        rect.height - HEADER_HEIGHT - SCROLLBAR_SIZE - 4
    )
    draw_scrollbar(screen, sb_y_rect, num_rows * ROW_HEIGHT, view_rect.height, state.scroll_row_idx * ROW_HEIGHT, vertical=True)
    
    # Horizontal
    sb_x_rect = pygame.Rect(rect.x + ROW_LABEL_WIDTH, rect.bottom - SCROLLBAR_SIZE, rect.width - ROW_LABEL_WIDTH - SCROLLBAR_SIZE, SCROLLBAR_SIZE)
    draw_scrollbar(screen, sb_x_rect, num_cols * COL_WIDTH, view_rect.width, state.scroll_col_idx * COL_WIDTH, vertical=False)
    
    # Corner filler
    pygame.draw.rect(screen, MATRIX_BG, (rect.right - SCROLLBAR_SIZE, rect.bottom - SCROLLBAR_SIZE, SCROLLBAR_SIZE, SCROLLBAR_SIZE))

def draw_viz(screen: pygame.Surface, font_title: pygame.font.Font, font_body: pygame.font.Font, state: VizState):
    w, h = screen.get_size()
    
    # Layout:
    # Top Half (split 50/50): Board | Thoughts
    # Bottom Half: Matrix
    
    half_h = h // 2
    half_w = w // 2
    
    board_area = pygame.Rect(0, 0, half_w, half_h)
    text_area = pygame.Rect(half_w, 0, half_w, half_h)
    matrix_area = pygame.Rect(0, half_h, w, h - half_h)
    
    screen.fill(BG)
    
    # --- 1. Draw Board (Top Left) ---
    current_event = state.current_event
    current_row_ids = current_event.get("state", [])
    current_placements = [state.placements[rid] for rid in current_row_ids]
    
    # Calculate scale to fit board
    board_w = BOARD_COLS * CELL_SIZE
    board_h = BOARD_ROWS * CELL_SIZE
    scale = min(board_area.width / (board_w + 80), board_area.height / (board_h + 80)) # More padding for coords
    scale = min(1.0, scale)
    
    scaled_cell = int(CELL_SIZE * scale)
    start_x = board_area.x + (board_area.width - BOARD_COLS * scaled_cell) // 2
    start_y = board_area.y + (board_area.height - BOARD_ROWS * scaled_cell) // 2
    
    # Draw Board Coordinates
    # Columns (0-6)
    for c in range(BOARD_COLS):
        lbl = font_body.render(str(c), True, TEXT_SECONDARY)
        lbl_rect = lbl.get_rect(center=(start_x + c * scaled_cell + scaled_cell//2, start_y - 15))
        screen.blit(lbl, lbl_rect)
        
    # Rows (0-6)
    for r in range(BOARD_ROWS):
        lbl = font_body.render(str(r), True, TEXT_SECONDARY)
        lbl_rect = lbl.get_rect(center=(start_x - 15, start_y + r * scaled_cell + scaled_cell//2))
        screen.blit(lbl, lbl_rect)

    # Draw Board Grid
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            x = start_x + c * scaled_cell
            y = start_y + r * scaled_cell
            rect = pygame.Rect(x, y, scaled_cell, scaled_cell)
            
            if (r, c) in ILLEGAL_CELLS:
                pygame.draw.rect(screen, ILLEGAL, rect, border_radius=int(12*scale))
            elif (r, c) == MONTH_COORDS[state.month]:
                pygame.draw.rect(screen, BG, rect, border_radius=int(12*scale))
                pygame.draw.rect(screen, DATE_BORDER, rect, width=2, border_radius=int(12*scale))
            elif (r, c) == DAY_COORDS[state.day]:
                pygame.draw.rect(screen, BG, rect, border_radius=int(12*scale))
                pygame.draw.rect(screen, DATE_BORDER, rect, width=2, border_radius=int(12*scale))
            else:
                pygame.draw.rect(screen, BG, rect, border_radius=int(12*scale))
                pygame.draw.rect(screen, GRID, rect, width=1, border_radius=int(12*scale))

    # Draw Placements
    for p in current_placements:
        color = PIECE_COLORS[p.piece]
        for r, c in p.cells:
            x = start_x + c * scaled_cell
            y = start_y + r * scaled_cell
            rect = pygame.Rect(x, y, scaled_cell, scaled_cell)
            pygame.draw.rect(screen, color, rect, border_radius=int(12*scale))
            
    # Highlight current action on board
    event_type = current_event["type"]
    event_data = current_event.get("data", {})
    
    if event_type == "SELECT_ROW":
        row_id = event_data["row"]
        p = state.placements[row_id]
        for r, c in p.cells:
            x = start_x + c * scaled_cell
            y = start_y + r * scaled_cell
            rect = pygame.Rect(x, y, scaled_cell, scaled_cell)
            pygame.draw.rect(screen, (255, 255, 255), rect, width=3, border_radius=int(12*scale))
            
    elif event_type == "CHOOSE_COL":
        col_idx = event_data["chosen"]
        col_label = state.column_labels[col_idx]
        
        # Only highlight if it's a board column (tuple)
        # Actually, column_labels has strings for pieces and strings for cells "(r,c)"
        # Wait, solver.py says: column_labels = piece_names + [f"({r},{c})" for r, c in cells_sorted]
        # So they are ALL strings.
        # But wait, in solver.py:
        # cell_index keys are Tuples, but column_labels are strings?
        # Let's check solver.py line 43: column_labels = piece_names + [f"({r},{c})" for r, c in cells_sorted]
        # Yes, they are strings!
        
        # So I need to parse the string back to a tuple if I want to highlight the board.
        # Or better, rely on the string format.
        
        if isinstance(col_label, str) and col_label.startswith("(") and col_label.endswith(")"):
            try:
                # Parse "(r,c)"
                content = col_label[1:-1]
                r_str, c_str = content.split(',')
                r, c = int(r_str), int(c_str)
                
                x = start_x + c * scaled_cell
                y = start_y + r * scaled_cell
                rect = pygame.Rect(x, y, scaled_cell, scaled_cell)
                
                # Animation: Fade in
                anim_progress = min(1.0, state.step_timer / 0.3)
                alpha = int(255 * anim_progress)
                
                # Draw animated highlight
                s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.rect(s, (255, 200, 50, alpha), s.get_rect(), width=3, border_radius=int(12*scale))
                screen.blit(s, rect)
            except ValueError:
                pass

    # --- 2. Draw Thoughts (Top Right) ---
    pygame.draw.rect(screen, (20, 20, 25), text_area)
    pygame.draw.line(screen, GRID, (text_area.x, 0), (text_area.x, half_h))
    pygame.draw.line(screen, GRID, (0, half_h), (w, half_h))
    
    y = 40
    title = font_title.render("Algorithm's Mind", True, TEXT_MAIN)
    screen.blit(title, (text_area.x + 20, y))
    y += 50
    
    lines = []
    if event_type == "INIT":
        lines = ["INITIALIZING", "I am ready to start.", "Building the matrix..."]
        
    elif event_type == "CHOOSE_COL":
        chosen_idx = event_data['chosen']
        chosen_label = state.column_labels[chosen_idx]
        size = event_data['size']
        candidates = event_data.get('candidates', [])
        
        # Find the minimum size to make the text accurate
        min_size = min((c['size'] for c in candidates), default=size)
        
        lines = [
            "ANALYZING",
            "I am looking for the 'most constrained' column (fewest options).",
            f"I see that column '{chosen_label}' has only {size} possible moves.",
            f"This is the best choice to minimize guessing."
        ]
        
    elif event_type == "SELECT_ROW":
        row_id = event_data['row']
        p = state.placements[row_id]
        ctx = current_event.get("narrative_ctx", {})
        
        idx = ctx.get("option_idx", "?")
        total = ctx.get("total_options", "?")
        col = ctx.get("col", "?")
        
        lines = [
            "DECIDING",
            f"I am trying Option {idx} of {total} for column '{col}'.",
            f"Placing Piece {p.piece} at ({p.cells[0][0]}, {p.cells[0][1]}).",
            "Let's see if this leads to a solution..."
        ]
        
    elif event_type == "BACKTRACK":
        ctx = current_event.get("narrative_ctx", {})
        col = ctx.get("col", "?")
        
        lines = [
            "BACKTRACKING",
            f"I cannot satisfy column '{col}'.",
            "All options for this column conflict with my previous choices.",
            "This means one of my earlier decisions was wrong."
        ]
        
    elif event_type == "SOLUTION":
        lines = ["SOLVED", "I have found a solution.", "All constraints are satisfied exactly once."]
        
    elif event_type == "UNSELECT_ROW":
        lines = [
            "BACKTRACKING", 
            "Removing the last piece.", 
            "I will return to the previous decision point and try the next option."
        ]
    
    # (Removed COVER_COL and UNCOVER_COL blocks as they are filtered out)
    
    for line in lines:
        # Wrap text
        words = line.split(' ')
        curr_line = ""
        for word in words:
            test_line = curr_line + word + " "
            if font_body.size(test_line)[0] < text_area.width - 40:
                curr_line = test_line
            else:
                surf = font_body.render(curr_line, True, TEXT_SECONDARY)
                screen.blit(surf, (text_area.x + 20, y))
                y += 25
                curr_line = word + " "
        surf = font_body.render(curr_line, True, TEXT_SECONDARY)
        screen.blit(surf, (text_area.x + 20, y))
        y += 30
        
    # Timeline Controls (Bottom of Text Area)
    controls_y = half_h - 80
    
    # Progress Bar
    progress = state.current_step / (state.total_steps - 1) if state.total_steps > 1 else 0
    pygame.draw.rect(screen, GRID, (text_area.x + 20, controls_y, text_area.width - 40, 4))
    pygame.draw.circle(screen, TEXT_MAIN, (int(text_area.x + 20 + (text_area.width - 40) * progress), controls_y + 2), 6)
    
    # Buttons
    btn_y = controls_y + 30
    play_text = "PAUSE" if state.playing else "PLAY"
    
    buttons = [
        ("<<", "prev"),
        (play_text, "toggle"),
        (">>", "next")
    ]
    
    # Center buttons in text area
    total_btn_w = len(buttons) * 80
    start_x = text_area.x + (text_area.width - total_btn_w) // 2
    
    for text, action in buttons:
        btn_rect = pygame.Rect(start_x, btn_y, 60, 30)
        pygame.draw.rect(screen, CARD_BG, btn_rect, border_radius=4)
        pygame.draw.rect(screen, GRID, btn_rect, width=1, border_radius=4)
        
        lbl = font_body.render(text, True, TEXT_MAIN)
        lbl_rect = lbl.get_rect(center=btn_rect.center)
        screen.blit(lbl, lbl_rect)
        start_x += 80
            
    # --- 3. Draw Matrix View (Bottom) ---
    draw_matrix(screen, matrix_area, state, font_body)
    
    # --- 4. Visual Polish (Shadows) ---
    # Shadow separating Board and Thoughts (Vertical)
    draw_shadow(screen, pygame.Rect(half_w, 0, 10, half_h), vertical=True)
    
    # Shadow separating Top Half and Matrix (Horizontal)
    draw_shadow(screen, pygame.Rect(0, half_h, w, 10), vertical=False)

def handle_viz_input(event: pygame.event.Event, state: VizState, screen_size: tuple[int, int]) -> str | None:
    """Handles input for the visualization view. Returns an action string if a button is clicked."""
    w, h = screen_size
    half_h = h // 2
    half_w = w // 2
    
    # Areas
    text_area = pygame.Rect(half_w, 0, half_w, half_h)
    matrix_area = pygame.Rect(0, half_h, w, h - half_h)
    
    # Dimensions (must match draw_matrix)
    HEADER_HEIGHT = 50
    ROW_LABEL_WIDTH = 80
    SCROLLBAR_SIZE = 12
    
    # Timeline Controls
    controls_y = half_h - 80
    timeline_rect = pygame.Rect(text_area.x + 20, controls_y - 10, text_area.width - 40, 24) # Larger hit area
    
    # Scrollbar Rects
    sb_y_rect = pygame.Rect(matrix_area.right - SCROLLBAR_SIZE, matrix_area.y + HEADER_HEIGHT, SCROLLBAR_SIZE, matrix_area.height - HEADER_HEIGHT - SCROLLBAR_SIZE)
    sb_x_rect = pygame.Rect(matrix_area.x + ROW_LABEL_WIDTH, matrix_area.bottom - SCROLLBAR_SIZE, matrix_area.width - ROW_LABEL_WIDTH - SCROLLBAR_SIZE, SCROLLBAR_SIZE)

    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1: # Left Click
            # 1. Timeline
            if timeline_rect.collidepoint(event.pos):
                state.dragging_timeline = True
                # Calculate seek
                rel_x = event.pos[0] - (text_area.x + 20)
                progress = max(0.0, min(1.0, rel_x / (text_area.width - 40)))
                step = int(progress * (state.total_steps - 1))
                state.set_step(step)
                return "seek"
            
            # 2. Scrollbars
            if sb_y_rect.collidepoint(event.pos):
                state.dragging_scrollbar_y = True
            elif sb_x_rect.collidepoint(event.pos):
                state.dragging_scrollbar_x = True
                
            # 3. Buttons
            btn_y = controls_y + 30
            buttons = [("<<", "prev"), ("PLAY", "toggle"), (">>", "next")]
            total_btn_w = len(buttons) * 80
            start_x = text_area.x + (text_area.width - total_btn_w) // 2
            
            for _, action in buttons:
                btn_rect = pygame.Rect(start_x, btn_y, 60, 30)
                if btn_rect.collidepoint(event.pos):
                    return action
                start_x += 80

    elif event.type == pygame.MOUSEBUTTONUP:
        if event.button == 1:
            state.dragging_timeline = False
            state.dragging_scrollbar_y = False
            state.dragging_scrollbar_x = False

    elif event.type == pygame.MOUSEMOTION:
        if getattr(state, 'dragging_timeline', False):
            rel_x = event.pos[0] - (text_area.x + 20)
            progress = max(0.0, min(1.0, rel_x / (text_area.width - 40)))
            step = int(progress * (state.total_steps - 1))
            state.set_step(step)
            
        elif getattr(state, 'dragging_scrollbar_y', False):
            # Calculate new scroll_row_idx
            # Mouse Y relative to track top
            track_top = sb_y_rect.y
            track_h = sb_y_rect.height
            rel_y = event.pos[1] - track_top
            
            ratio = rel_y / track_h
            max_scroll = len(state.placements) - (matrix_area.height - HEADER_HEIGHT - SCROLLBAR_SIZE) / 35 # Approx
            state.target_scroll_row_idx = max(0.0, ratio * max_scroll)
            state.scroll_row_idx = state.target_scroll_row_idx
            
        elif getattr(state, 'dragging_scrollbar_x', False):
            track_left = sb_x_rect.x
            track_w = sb_x_rect.width
            rel_x = event.pos[0] - track_left
            
            ratio = rel_x / track_w
            max_scroll = len(state.column_labels) - (matrix_area.width - ROW_LABEL_WIDTH - SCROLLBAR_SIZE) / 35
            state.target_scroll_col_idx = max(0.0, ratio * max_scroll)
            state.scroll_col_idx = state.target_scroll_col_idx

    return None
