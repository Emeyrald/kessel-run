import pytest
import random
from kessel_run.maze import Maze, Direction
from kessel_run.generation import generate, build_maze

ROWS = 3
COLS = 3
DIRECTIONS = Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST

@pytest.fixture
def maze():
    return Maze(ROWS, COLS)

@pytest.fixture
def generated_maze():
    maze = Maze(10, 10)
    generate(maze, random.Random(42))
    return maze

@pytest.mark.parametrize("row", range(ROWS))
@pytest.mark.parametrize("col", range(COLS))
@pytest.mark.parametrize("direction", DIRECTIONS)
def test_start_closed(maze, row, col, direction):
    assert not maze.is_open(row, col, direction)

@pytest.mark.parametrize("row", range(ROWS))
@pytest.mark.parametrize("col", range(COLS))
@pytest.mark.parametrize("direction", DIRECTIONS)
def test_same_wall(maze, row, col, direction):
    neighbor = maze.neighbor(row, col, direction)
    if neighbor is None:
        pytest.skip
    else:
        maze.open_wall(row, col, direction)
        assert maze.is_open(neighbor[0], neighbor[1], direction.opposite)

def test_open_close(maze):
    maze.open_wall(0, 0, Direction.EAST)
    assert maze.is_open(0, 0, Direction.EAST)
    maze.close_wall(0, 0, Direction.EAST)
    assert not maze.is_open(0, 0, Direction.EAST)

@pytest.mark.parametrize("row, col, direction", [
    (0, 0, Direction.NORTH),
    (0, 0, Direction.WEST),
    (1, 1, Direction.SOUTH),
    (1, 1, Direction.EAST),
])
def test_border_wall(maze, row, col, direction):
    maze.open_wall(row, col, direction)
    assert maze.is_open(row, col, direction)

@pytest.mark.parametrize("row, col, direction", [
    (-1, 0, Direction.NORTH),
    (3, 0, Direction.NORTH),
    (0, 3, Direction.WEST),
    (3, 3, Direction.NORTH),
])
def test_out_of_bounds(maze, row, col, direction):
    with pytest.raises(IndexError):
        maze.is_open(row, col, direction)
    with pytest.raises(IndexError):
        maze.neighbor(row, col, direction)

def test_invalid_direction(maze):
    with pytest.raises(ValueError):
        maze.is_open(0, 0, "not a direction")

@pytest.mark.parametrize("row, col, direction", [
    (0, 1, Direction.NORTH),
    (1, 0, Direction.WEST),
    (2, 1, Direction.SOUTH),
    (1, 2, Direction.EAST),
])
def test_correct_neighbor(maze, row, col, direction):
    neighbor = maze.neighbor(1, 1, direction)
    assert neighbor == (row, col)

@pytest.mark.parametrize("direction", [
    Direction.NORTH,
    Direction.WEST
])
def test_corner_neighbors(maze, direction):
    assert maze.neighbor(0, 0, direction) is None

def test_bfs_start_closed(maze):
    start = 0, 0
    assert maze.distances_from(start) == {start: 0}

def test_bfs_open_corridor():
    maze = Maze(1, 3)
    maze.open_wall(0, 0, Direction.EAST)
    maze.open_wall(0, 1, Direction.EAST)
    assert maze.distances_from((0, 0)) == {(0, 0): 0, (0, 1): 1, (0, 2): 2}

def test_bfs_partly_opened():
    maze = Maze(1, 3)
    maze.open_wall(0, 0, Direction.EAST)
    assert maze.distances_from((0, 0)) == {(0, 0): 0, (0, 1): 1}

def test_all_cells_reachable(generated_maze):
    distances = generated_maze.distances_from((0, 0))
    assert len(distances) == generated_maze.rows * generated_maze.cols

def test_spanning_tree(generated_maze):
    horizontal = sum(row.count(True) for row in generated_maze.horizontal[1:-1])
    vertical = sum(row[1:-1].count(True) for row in generated_maze.vertical)
    assert horizontal + vertical == generated_maze.rows * generated_maze.cols - 1

def test_closed_borders(generated_maze):
    assert not any(generated_maze.horizontal[0])
    assert not any(generated_maze.horizontal[-1])
    assert not any(row[0] for row in generated_maze.vertical)
    assert not any(row[-1] for row in generated_maze.vertical)

def test_deterministic():
    maze1 = Maze(10, 10)
    maze2 = Maze(10, 10)
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    generate(maze1, rng1)
    generate(maze2, rng2)
    assert maze1.horizontal == maze2.horizontal
    assert maze1.vertical == maze2.vertical

def test_seed_matters():
    maze1 = Maze(10, 10)
    maze2 = Maze(10, 10)
    generate(maze1, random.Random(0))
    generate(maze2, random.Random(1))
    assert maze1.horizontal != maze2.horizontal or maze1.vertical != maze2.vertical

def test_one_by_one():
    maze = Maze(1, 1)
    generate(maze, random.Random(42))
    horizontal = sum(row.count(True) for row in maze.horizontal)
    vertical = sum(row.count(True) for row in maze.vertical)
    assert horizontal + vertical == 0

def test_one_by_n():
    maze = Maze(1, 10)
    generate(maze, random.Random(42))
    assert all(maze.vertical[0][1:-1])

def test_border_cells_normal():
    maze = Maze(10, 10)
    cells = maze.border_cells()

    assert len(cells) == len(set(cells))
    assert len(cells) == (2 * 10 + 2 * 10 - 4)

    for r, c in cells:
        assert r == 0 or r == 9 or c == 0 or c == 9

@pytest.mark.parametrize("r, c, expected_count", [
    (1, 1, 1),
    (1, 5, 5),
    (5, 1, 5),
])
def test_border_cells_edge_shapes(r, c, expected_count):
    maze = Maze(r, c)
    cells = maze.border_cells()

    assert len(cells) == len(set(cells))
    assert len(cells) == expected_count

def test_closed_interior_walls_fresh():
    maze = Maze(10, 10)
    walls = maze.closed_interior_walls()

    assert len(walls) == 180

    for r, c, d in walls:
        assert not maze.is_open(r, c, d)
        assert maze.neighbor(r, c, d) is not None

def test_closed_interior_walls_after_generate():
    maze = Maze(10, 10)
    generate(maze, random.Random(42))
    walls = maze.closed_interior_walls()

    assert len(walls) == 81

    for r, c, d in walls:
        assert not maze.is_open(r, c, d)
        assert maze.neighbor(r, c, d) is not None

def test_build_maze_deterministic():
    maze1 = build_maze(10, 10, 42, 0.5)
    maze2 = build_maze(10, 10, 42, 0.5)

    assert maze1.horizontal == maze2.horizontal
    assert maze1.vertical == maze2.vertical
    assert maze1.start_cell == maze2.start_cell
    assert maze1.exit_cell == maze2.exit_cell
    assert maze1.exit_wall == maze2.exit_wall

def test_build_maze_superset():
    maze_low = build_maze(10, 10, 42, 0.2)
    maze_high = build_maze(10, 10, 42, 0.5)

    for r in range(10):
        for c in range(10):
            for d in DIRECTIONS:
                if maze_low.is_open(r, c, d) and maze_low.neighbor(r, c, d) is not None:
                    assert maze_high.is_open(r, c, d)

def test_build_maze_fraction_zero():
    maze = build_maze(10, 10, 42, 0.0)

    open_interior = 0
    for r in range(10):
        for c in range(10):
            for d in [Direction.SOUTH, Direction.EAST]:
                if maze.neighbor(r, c, d) is not None and maze.is_open(r, c, d):
                    open_interior += 1

    assert open_interior == 99

def test_build_maze_fraction_one():
    maze = build_maze(10, 10, 42, 1.0)

    for r in range(10):
        for c in range(10):
            for d in DIRECTIONS:
                if maze.neighbor(r, c, d) is not None:
                    assert maze.is_open(r, c, d)

def test_build_maze_loop_count():
    fraction = 0.4
    maze = build_maze(10, 10, 42, fraction)

    open_interior = 0
    for r in range(10):
        for c in range(10):
            for d in [Direction.SOUTH, Direction.EAST]:
                if maze.neighbor(r, c, d) is not None and maze.is_open(r, c, d):
                    open_interior += 1

    assert open_interior == 99 + round(fraction * 81)

def test_build_maze_start_and_exit_placement():
    maze = build_maze(10, 10, 42, 0.5)
    border_cells = maze.border_cells()

    assert maze.start_cell in border_cells
    assert maze.exit_cell in border_cells
    assert maze.start_cell != maze.exit_cell

def test_build_maze_one_open_border_wall():
    maze = build_maze(10, 10, 42, 0.5)

    for r in range(10):
        for c in range(10):
            for d in DIRECTIONS:
                if maze.neighbor(r, c, d) is None:
                    if (r, c) == maze.exit_cell and d == maze.exit_wall:
                        assert maze.is_open(r, c, d)
                    else:
                        assert not maze.is_open(r, c, d)

def test_build_maze_exit_is_farthest():
    maze = build_maze(10, 10, 42, 0.0)
    distances = maze.distances_from(maze.start_cell)

    exit_dist = distances[maze.exit_cell]
    border_cells = maze.border_cells()

    for cell in border_cells:
        if cell in distances:
            assert distances[cell] <= exit_dist

def test_build_maze_exit_independent_of_loops():
    maze_clean = build_maze(10, 10, 42, 0.0)
    maze_loopy = build_maze(10, 10, 42, 0.7)

    assert maze_clean.start_cell == maze_loopy.start_cell
    assert maze_clean.exit_cell == maze_clean.exit_cell

def test_build_maze_all_reachable_after_loops():
    maze = build_maze(10, 10, 42, 0.3)
    distances = maze.distances_from(maze.start_cell)

    assert len(distances) == 100