import pytest
import random
from kessel_run.maze import Maze, Direction
from kessel_run.generation import generate

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