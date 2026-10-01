import random
from kessel_run.maze import Maze, Direction

def generate(maze, rng):
    """Carve a perfect maze into an all-walls-closed maze using recursive backtracking."""

    visited = [[False] * maze.cols for _ in range(maze.rows)]
    stack = []
    row = rng.randrange(maze.rows)
    col = rng.randrange(maze.cols)
    stack.append((row, col))
    visited[row][col] = True

    while stack:
        curr_row, curr_col = stack[-1]
        neighbors = []

        for d in Direction:
            neighbor = maze.neighbor(curr_row, curr_col, d)
            if neighbor is None:
                continue
            nr, nc = neighbor
            if visited[nr][nc]:
                continue
            neighbors.append((nr, nc, d))

        if neighbors:
            nr, nc, d = rng.choice(neighbors)
            maze.open_wall(curr_row, curr_col, d)
            stack.append((nr, nc))
            visited[nr][nc] = True
        else:
            stack.pop()

def build_maze(rows, cols, seed, loop_fraction):
    """Order for RNG: Generate maze, get start_cell, get exit_cell, add loops. The same inputs give the same maze."""
    rng = random.Random(seed)
    maze = Maze(rows, cols)
    generate(maze, rng)

    border_cells = maze.border_cells()

    maze.start_cell = rng.choice(border_cells)
    distances = maze.distances_from(maze.start_cell)
    maze.exit_cell = max((cell for cell in border_cells), key=distances.get)

    er, ec = maze.exit_cell
    maze.exit_wall = next(d for d in Direction if maze.neighbor(er, ec, d) is None)
    maze.open_wall(er, ec, maze.exit_wall)

    walls = maze.closed_interior_walls()
    rng.shuffle(walls)

    limit = round(loop_fraction * len(walls))
    for row, col, direction in walls[:limit]:
        maze.open_wall(row, col, direction)

    return maze