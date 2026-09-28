import pytest
from kessel_run.maze import Maze, Direction

ROWS = 3
COLS = 3
DIRECTIONS = Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST

@pytest.fixture
def maze():
    return Maze(ROWS, COLS)

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
    if neighbor == None:
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
    assert maze.neighbor(0, 0, direction) == None

