from __future__ import annotations
from datetime import date
from solver import solve_for_date
from gui import show_solutions


def main():
    today = date.today()
    month = today.month
    day = today.day

    print(f"Solving puzzle for {today} (month={month}, day={day})")

    solutions = solve_for_date(month, day, find_all=True)
    if solutions is None:
        print("No solution found.")
        return

    print(f"Found {len(solutions)} solutions.")
    show_solutions(solutions, month, day)


if __name__ == "__main__":
    main()
