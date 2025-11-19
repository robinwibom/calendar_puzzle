# Calendar Puzzle Solver

A Python-based solver and visualizer for the "Calendar Puzzle" (also known as "A-Puzzle-A-Day").

## Overview

This project solves the daily calendar puzzle where the goal is to place 8 polyomino pieces on a 7x7 grid such that only the current month and day remain uncovered.

It uses **Algorithm X** with **Dancing Links (DLX)** to efficiently find solutions to the exact cover problem.

## Features

- **Fast Solver**: Finds solutions in milliseconds using Knuth's Algorithm X.
- **GUI Visualization**: Interactive Pygame-based interface to view solutions.
- **Daily Puzzle**: Automatically defaults to solving for the current date.
- **All Solutions**: Can find and display all possible solutions for a given date.

## How to Run

1.  **Install Dependencies**:
    You need Python 3.8+ and `pygame`.
    ```bash
    pip install pygame
    ```

2.  **Run the Solver**:
    ```bash
    python main.py
    ```
    By default, it solves for today's date.

## Project Structure

- `main.py`: Entry point. Sets up the date and calls the solver/GUI.
- `solver.py`: Orchestrates the solving process. Builds the exact cover matrix.
- `dlx.py`: Implementation of Algorithm X using Dancing Links.
- `board.py`: Defines the board geometry, coordinate systems for months/days, and illegal cells.
- `pieces.py`: Defines the 8 polyomino pieces and handles their rotations/flips.
- `placements.py`: Generates all valid placements of pieces on the board.
- `gui.py`: Pygame visualization of the board and solutions.

## How it Works

The puzzle is modeled as an **Exact Cover** problem:
- **Universe**: The set of elements that must be covered exactly once.
    - Each of the 8 pieces must be used exactly once.
    - Each valid cell on the board (excluding the target month/day) must be covered exactly once.
- **Subsets**: Each possible placement of a piece constitutes a subset of the universe.

The `dlx.py` module implements the Dancing Links technique to efficiently backtrack and find a collection of subsets (piece placements) that partition the universe.
