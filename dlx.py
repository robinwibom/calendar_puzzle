# dlx.py
# Algorithm X (Dancing Links) implementation

from __future__ import annotations


class ColumnNode:
    def __init__(self, name: int):
        self.name = name
        self.size = 0
        self.left: ColumnNode = self
        self.right: ColumnNode = self
        self.up: "Node" = self  # type: ignore[assignment]
        self.down: "Node" = self  # type: ignore[assignment]


class Node:
    def __init__(self, column: ColumnNode, row_id: int):
        self.column = column
        self.row_id = row_id
        self.left: Node = self
        self.right: Node = self
        self.up: Node = self
        self.down: Node = self


class DLXSolver:
    def __init__(self, num_columns: int):
        self.header = ColumnNode(-1)
        # Create column headers in a circular doubly-linked list.
        self.columns = [ColumnNode(i) for i in range(num_columns)]
        last = self.header
        for col in self.columns:
            col.left = last
            col.right = self.header
            last.right = col
            self.header.left = col
            last = col

    def add_row(self, row_id: int, column_indices: list[int]) -> None:
        first_node: Node | None = None
        prev: Node | None = None

        for c_idx in sorted(column_indices):
            column = self.columns[c_idx]
            node = Node(column, row_id)

            # Insert into column (at bottom)
            node.down = column
            node.up = column.up
            column.up.down = node
            column.up = node
            column.size += 1

            # Link horizontally within row
            if first_node is None:
                first_node = node
            if prev is not None:
                node.left = prev
                node.right = first_node
                prev.right = node
                first_node.left = node
            prev = node

    def _cover(self, column: ColumnNode) -> None:
        column.right.left = column.left
        column.left.right = column.right
        row = column.down
        while row is not column:
            node = row.right
            while node is not row:
                node.down.up = node.up
                node.up.down = node.down
                node.column.size -= 1
                node = node.right
            row = row.down

    def _uncover(self, column: ColumnNode) -> None:
        row = column.up
        while row is not column:
            node = row.left
            while node is not row:
                node.column.size += 1
                node.down.up = node
                node.up.down = node
                node = node.left
            row = row.up
        column.right.left = column
        column.left.right = column

    def _choose_column(self) -> ColumnNode:
        # Heuristic: choose column with smallest size.
        c = self.header.right
        best = c
        while c is not self.header:
            if c.size < best.size:
                best = c
            c = c.right
        return best

    def solve(self):
        solution: list[Node] = []

        def search():
            if self.header.right is self.header:
                yield [node.row_id for node in solution]
                return

            column = self._choose_column()
            if column.size == 0:
                return

            self._cover(column)

            row = column.down
            while row is not column:
                solution.append(row)

                node = row.right
                while node is not row:
                    self._cover(node.column)
                    node = node.right

                yield from search()

                row = solution.pop()
                node = row.left
                while node is not row:
                    self._uncover(node.column)
                    node = node.left

                row = row.down

            self._uncover(column)

        yield from search()

    def solve_one(self):
        for sol in self.solve():
            return sol
        return None

    def solve_steps(self):
        """
        Generator that yields events describing the solving process.
        Events are dicts with 'type', 'data', and optional 'state'.
        """
        solution: list[Node] = []
        
        # Helper to capture current state (list of row_ids)
        def get_state():
            return [node.row_id for node in solution]

        def search(depth=0):
            # 1. Check if solved
            if self.header.right is self.header:
                yield {
                    "type": "SOLUTION",
                    "data": {"solution": get_state()},
                    "state": get_state()
                }
                return

            # 2. Choose Column (with detailed POV)
            # We iterate manually to capture the thought process
            c = self.header.right
            best_col = c
            candidates = []
            
            while c is not self.header:
                candidates.append({"name": c.name, "size": c.size})
                if c.size < best_col.size:
                    best_col = c
                c = c.right
            
            yield {
                "type": "CHOOSE_COL",
                "data": {
                    "chosen": best_col.name,
                    "size": best_col.size,
                    "candidates": candidates, # All checked columns
                    "reason": f"Column {best_col.name} has the fewest options ({best_col.size})."
                },
                "state": get_state()
            }

            column = best_col
            
            if column.size == 0:
                yield {
                    "type": "BACKTRACK",
                    "data": {"reason": f"Column {column.name} has no options left."},
                    "state": get_state()
                }
                return

            self._cover(column)
            yield {
                "type": "COVER_COL", 
                "data": {"col": column.name},
                "state": get_state()
            }

            row = column.down
            while row is not column:
                solution.append(row)
                yield {
                    "type": "SELECT_ROW",
                    "data": {"row": row.row_id},
                    "state": get_state()
                }

                node = row.right
                while node is not row:
                    self._cover(node.column)
                    # yield {"type": "COVER_COL_IMPLICIT", "data": {"col": node.column.name}}
                    node = node.right

                yield from search(depth + 1)

                row = solution.pop()
                yield {
                    "type": "UNSELECT_ROW",
                    "data": {"row": row.row_id},
                    "state": get_state()
                }

                node = row.left
                while node is not row:
                    self._uncover(node.column)
                    node = node.left

                row = row.down

            self._uncover(column)
            yield {
                "type": "UNCOVER_COL",
                "data": {"col": column.name},
                "state": get_state()
            }
            
            if depth > 0:
                 yield {
                    "type": "BACKTRACK",
                    "data": {"reason": "Tried all options for this column, going back."},
                    "state": get_state()
                }

        yield {
            "type": "INIT",
            "data": {"message": "Starting search..."},
            "state": []
        }
        yield from search()
