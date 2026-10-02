from enum import Enum, unique
from collections import deque

@unique
class Direction(Enum):
    NORTH = -1, 0
    SOUTH = 1, 0
    WEST = 0, -1
    EAST = 0, 1

    @property
    def opposite(self):
        return Direction((-self.value[0], -self.value[1]))

class Maze:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.horizontal = [[False] * cols for _ in range(rows + 1)]
        self.vertical = [[False] * (cols + 1) for _ in range(rows)]
        self.start_cell = None
        self.exit_cell = None
        self.exit_wall = None

    def is_open(self, row, col, direction):
        arr, r, c = self._wall_index(row, col, direction)
        return arr[r][c]

    def open_wall(self, row, col, direction):
        arr, r, c = self._wall_index(row, col, direction)
        arr[r][c] = True

    def close_wall(self, row, col, direction):
        arr, r, c = self._wall_index(row, col, direction)
        arr[r][c] = False

    def neighbor(self, row, col, direction):
        if not self._in_bounds(row, col):
            raise IndexError(f"{row, col} out of bounds")
        dr, dc = direction.value
        nr = row + dr
        nc = col + dc
        if not self._in_bounds(nr, nc):
            return None
        return nr, nc

    def distances_from(self, start):
        """Dictionary mapping each reachable cell to its step distance from the start"""
        queue = deque([start])
        distances = {start: 0}

        while queue:
            cell = queue.popleft()
            row, col = cell
            for d in Direction:
                neighbor = self.neighbor(row, col, d)
                if neighbor is None:
                    continue
                if not self.is_open(row, col, d):
                    continue
                if neighbor in distances:
                    continue
                distances[neighbor] = distances[cell] + 1
                queue.append(neighbor)

        return distances

    def border_cells(self):
        if self.rows == 1 or self.cols == 1:
            if self.rows == 1:
                return [(0, j) for j in range(self.cols)]
            else:
                return [(i, 0) for i in range(self.rows)]
            
        border_cells = (
            [(0, j) for j in range(self.cols)] +
            [(i, self.cols - 1) for i in range(1, self.rows)] +
            [(self.rows - 1, j) for j in range(self.cols - 2, -1, -1)] +
            [(i, 0) for i in range(self.rows - 2, 0, -1)]
        )

        return border_cells

    def closed_interior_walls(self):
        walls = []
        for row in range(self.rows):
            for col in range(self.cols):
                south_neighbor = self.neighbor(row, col, Direction.SOUTH)
                if south_neighbor is not None and not self.is_open(row, col, Direction.SOUTH):
                    walls.append((row, col, Direction.SOUTH))
                                
                east_neighbor = self.neighbor(row, col, Direction.EAST)
                if east_neighbor is not None and not self.is_open(row, col, Direction.EAST):
                    walls.append((row, col, Direction.EAST))

        return walls

    def open_interior_walls(self):
        walls = []
        for row in range(self.rows):
            for col in range(self.cols):
                south_neighbor = self.neighbor(row, col, Direction.SOUTH)
                if south_neighbor is not None and self.is_open(row, col, Direction.SOUTH):
                    walls.append((row, col, Direction.SOUTH))

                east_neighbor = self.neighbor(row, col, Direction.EAST)
                if east_neighbor is not None and self.is_open(row, col, Direction.EAST):
                    walls.append((row, col, Direction.EAST))

        return walls
        
    def _wall_index(self, row, col, direction):
        if not self._in_bounds(row, col):
            raise IndexError(f"{row, col} out of bounds")
        match direction:
            case Direction.NORTH:
                return self.horizontal, row, col
            case Direction.SOUTH:
                return self.horizontal, row + 1, col
            case Direction.WEST:
                return self.vertical, row, col
            case Direction.EAST:
                return self.vertical, row, col + 1
            case _:
                raise ValueError(f"Invalid direction: {direction!r}")

    def _in_bounds(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols