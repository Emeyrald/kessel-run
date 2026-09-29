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

