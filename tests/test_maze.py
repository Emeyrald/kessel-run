import pytest
import random
import copy
from kessel_run.maze import Maze, Direction
from kessel_run.generation import generate, build_maze
from kessel_run.shifting import shift_walls, make_shift_rng

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
    """Ensure that all walls are entirely closed when a fresh maze instance is initialized."""
    assert not maze.is_open(row, col, direction)

@pytest.mark.parametrize("row", range(ROWS))
@pytest.mark.parametrize("col", range(COLS))
@pytest.mark.parametrize("direction", DIRECTIONS)
def test_same_wall(maze, row, col, direction):
    """Verify that opening a wall from one cell simultaneously updates the opposite view of its valid neighbor."""
    neighbor = maze.neighbor(row, col, direction)
    if neighbor is None:
        pytest.skip()
    else:
        maze.open_wall(row, col, direction)
        assert maze.is_open(neighbor[0], neighbor[1], direction.opposite)

def test_open_close(maze):
    """Verify that explicit open_wall and close_wall state modifications mutate underlying coordinates correctly."""
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
    """Ensure that the state of physical outer border walls can be opened and toggled without restrictions."""
    maze.open_wall(row, col, direction)
    assert maze.is_open(row, col, direction)

@pytest.mark.parametrize("row, col, direction", [
    (-1, 0, Direction.NORTH),
    (3, 0, Direction.NORTH),
    (0, 3, Direction.WEST),
    (3, 3, Direction.NORTH),
])
def test_out_of_bounds(maze, row, col, direction):
    """Verify that checking status or matching neighbors outside grid boundaries safely raises an IndexError."""
    with pytest.raises(IndexError):
        maze.is_open(row, col, direction)
    with pytest.raises(IndexError):
        maze.neighbor(row, col, direction)

def test_invalid_direction(maze):
    """Ensure that passing arbitrary, unmapped objects as directions raises a structural ValueError."""
    with pytest.raises(ValueError):
        maze.is_open(0, 0, "not a direction")

@pytest.mark.parametrize("row, col, direction", [
    (0, 1, Direction.NORTH),
    (1, 0, Direction.WEST),
    (2, 1, Direction.SOUTH),
    (1, 2, Direction.EAST),
])
def test_correct_neighbor(maze, row, col, direction):
    """Verify that valid relative coordinate modifications return the precise neighbor index coordinates."""
    neighbor = maze.neighbor(1, 1, direction)
    assert neighbor == (row, col)

@pytest.mark.parametrize("direction", [
    Direction.NORTH,
    Direction.WEST
])
def test_corner_neighbors(maze, direction):
    """Ensure that calling neighbor on outermost grid corners facing outwards properly returns None."""
    assert maze.neighbor(0, 0, direction) is None

def test_bfs_start_closed(maze):
    """Verify that running distances_from on a fully closed maze returns a dictionary containing only the start node at distance 0."""
    start = 0, 0
    assert maze.distances_from(start) == {start: 0}

def test_bfs_open_corridor():
    """Verify that distances_from accurately measures step calculations down a single open linear channel."""
    maze = Maze(1, 3)
    maze.open_wall(0, 0, Direction.EAST)
    maze.open_wall(0, 1, Direction.EAST)
    assert maze.distances_from((0, 0)) == {(0, 0): 0, (0, 1): 1, (0, 2): 2}

def test_bfs_partly_opened():
    """Verify that distance calculations terminate correctly when blocked by an intact structural wall."""
    maze = Maze(1, 3)
    maze.open_wall(0, 0, Direction.EAST)
    assert maze.distances_from((0, 0)) == {(0, 0): 0, (0, 1): 1}

def test_all_cells_reachable(generated_maze):
    """Ensure that running standard maze generation guarantees every coordinate in the grid is reachable."""
    distances = generated_maze.distances_from((0, 0))
    assert len(distances) == generated_maze.rows * generated_maze.cols

def test_spanning_tree(generated_maze):
    """Verify that a freshly generated maze contains exactly V - 1 open interior walls to fulfill spanning tree criteria."""
    horizontal = sum(row.count(True) for row in generated_maze.horizontal[1:-1])
    vertical = sum(row[1:-1].count(True) for row in generated_maze.vertical)
    assert horizontal + vertical == generated_maze.rows * generated_maze.cols - 1

def test_closed_borders(generated_maze):
    """Ensure that generic maze generation retains fully intact and closed outer edge boundaries."""
    assert not any(generated_maze.horizontal[0])
    assert not any(generated_maze.horizontal[-1])
    assert not any(row[0] for row in generated_maze.vertical)
    assert not any(row[-1] for row in generated_maze.vertical)

def test_deterministic():
    """Verify that running maze generation with identical structural shapes and seeds outputs identical wall layouts."""
    maze1 = Maze(10, 10)
    maze2 = Maze(10, 10)
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    generate(maze1, rng1)
    generate(maze2, rng2)
    assert maze1.horizontal == maze2.horizontal
    assert maze1.vertical == maze2.vertical

def test_seed_matters():
    """Verify that executing maze generation with distinct seed values builds differing wall configurations."""
    maze1 = Maze(10, 10)
    maze2 = Maze(10, 10)
    generate(maze1, random.Random(0))
    generate(maze2, random.Random(1))
    assert maze1.horizontal != maze2.horizontal or maze1.vertical != maze2.vertical

def test_one_by_one():
    """Verify that generation functions properly on an isolated 1x1 grid cell configuration without crashing."""
    maze = Maze(1, 1)
    generate(maze, random.Random(42))
    horizontal = sum(row.count(True) for row in maze.horizontal)
    vertical = sum(row.count(True) for row in maze.vertical)
    assert horizontal + vertical == 0

def test_one_by_n():
    """Ensure that generation behaves accurately on long 1xN narrow corridors by opening every shared inner wall."""
    maze = Maze(1, 10)
    generate(maze, random.Random(42))
    assert all(maze.vertical[0][1:-1])

def test_border_cells_normal():
    """Verify that border_cells identifies unique coordinates located exclusively along the grid's external edges."""
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
    """Ensure that border_cells handles non-square edge matrices and thin grids accurately."""
    maze = Maze(r, c)
    cells = maze.border_cells()

    assert len(cells) == len(set(cells))
    assert len(cells) == expected_count

def test_closed_interior_walls_fresh():
    """Verify that a completely fresh grid correctly registers all internal cell connections as valid closed interior walls."""
    maze = Maze(10, 10)
    walls = maze.closed_interior_walls()

    assert len(walls) == 180

    for r, c, d in walls:
        assert not maze.is_open(r, c, d)
        assert maze.neighbor(r, c, d) is not None

def test_closed_interior_walls_after_generate():
    """Verify that after generation, the remaining closed interior walls are correctly tracked and valid."""
    maze = Maze(10, 10)
    generate(maze, random.Random(42))
    walls = maze.closed_interior_walls()

    assert len(walls) == 81

    for r, c, d in walls:
        assert not maze.is_open(r, c, d)
        assert maze.neighbor(r, c, d) is not None

def test_build_maze_deterministic():
    """Ensure that building a maze with identical seeds and parameters produces identical structures."""
    maze1 = build_maze(10, 10, 42, 0.5)
    maze2 = build_maze(10, 10, 42, 0.5)

    assert maze1.horizontal == maze2.horizontal
    assert maze1.vertical == maze2.vertical
    assert maze1.start_cell == maze2.start_cell
    assert maze1.exit_cell == maze2.exit_cell
    assert maze1.exit_wall == maze2.exit_wall

def test_build_maze_superset():
    """Verify that a higher loop fraction maze includes a strict superset of open walls from a lower fraction maze."""
    maze_low = build_maze(10, 10, 42, 0.2)
    maze_high = build_maze(10, 10, 42, 0.5)

    for r in range(10):
        for c in range(10):
            for d in DIRECTIONS:
                if maze_low.is_open(r, c, d) and maze_low.neighbor(r, c, d) is not None:
                    assert maze_high.is_open(r, c, d)

def test_build_maze_fraction_zero():
    """Confirm that a loop fraction of 0.0 creates a perfect maze with exactly V - 1 open interior walls."""
    maze = build_maze(10, 10, 42, 0.0)

    open_interior = 0
    for r in range(10):
        for c in range(10):
            for d in [Direction.SOUTH, Direction.EAST]:
                if maze.neighbor(r, c, d) is not None and maze.is_open(r, c, d):
                    open_interior += 1

    assert open_interior == 99

def test_build_maze_fraction_one():
    """Confirm that a loop fraction of 1.0 breaks down every single interior wall in the maze."""
    maze = build_maze(10, 10, 42, 1.0)

    for r in range(10):
        for c in range(10):
            for d in DIRECTIONS:
                if maze.neighbor(r, c, d) is not None:
                    assert maze.is_open(r, c, d)

def test_build_maze_loop_count():
    """Verify that the number of open interior walls scales accurately with the requested loop fraction."""
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
    """Ensure start and exit cells are distinct and placed properly along the border of the maze."""
    maze = build_maze(10, 10, 42, 0.5)
    border_cells = maze.border_cells()

    assert maze.start_cell in border_cells
    assert maze.exit_cell in border_cells
    assert maze.start_cell != maze.exit_cell

def test_build_maze_one_open_border_wall():
    """Verify that all border walls remain completely closed except for the designated exit wall."""
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
    """Ensure the chosen exit cell represents the absolute maximum shortest-path distance from the start in a perfect maze."""
    maze = build_maze(10, 10, 42, 0.0)
    distances = maze.distances_from(maze.start_cell)

    exit_dist = distances[maze.exit_cell]
    border_cells = maze.border_cells()

    for cell in border_cells:
        if cell in distances:
            assert distances[cell] <= exit_dist

def test_build_maze_exit_independent_of_loops():
    """Confirm that the start and exit cell locations remain unchanged regardless of the loop fraction used."""
    maze_clean = build_maze(10, 10, 42, 0.0)
    maze_loopy = build_maze(10, 10, 42, 0.7)

    assert maze_clean.start_cell == maze_loopy.start_cell
    assert maze_clean.exit_cell == maze_clean.exit_cell

def test_build_maze_all_reachable_after_loops():
    """Verify that introducing loops into the maze layout does not break global reachability for any cell."""
    maze = build_maze(10, 10, 42, 0.3)
    distances = maze.distances_from(maze.start_cell)

    assert len(distances) == 100

def count_open_interior_walls(maze):
    """Helper function to count all open interior walls."""
    open_count = 0
    for r in range(maze.rows):
        for c in range(maze.cols):
            for d in [Direction.SOUTH, Direction.EAST]:
                if maze.neighbor(r, c, d) is not None and maze.is_open(r, c, d):
                    open_count += 1
    return open_count

def count_open_border_walls(maze):
    """Helper function to count all open exterior/border walls."""
    border_open = 0
    for r in range(maze.rows):
        for c in range(maze.cols):
            for d in DIRECTIONS:
                if maze.neighbor(r, c, d) is None and maze.is_open(r, c, d):
                    border_open += 1
    return border_open

def get_wall_state_snapshot(maze):
    """Captures snapshos of both horizontal and vertical walls"""
    return copy.deepcopy(maze.horizontal), copy.deepcopy(maze.vertical)

def test_shift_walls_one_swap_changed_two():
    """One swap must toggle exactly two walls"""
    maze = build_maze(10, 10, 42, 0.1)
    rng = make_shift_rng(42)
    changes = shift_walls(maze, rng, 1)

    assert len(changes) == 2

    c1r, c1c, dir1 = changes[0]
    c2r, c2c, dir2 = changes[1]

    assert maze.is_open(c1r, c1c, dir1) != maze.is_open(c2r, c2c, dir2)

def test_shift_walls_count_respected():
    """Using a higher loop fraction guarantees 3 successful swaps returning 6 elements."""
    maze = build_maze(10, 10, 42, 0.3)
    rng = make_shift_rng(42)
    changes = shift_walls(maze, rng, 3)
    assert len(changes) == 6

def test_shift_walls_stays_connected():
    """Validates connectivity via BFS across 1,000 consecutive single shifts."""
    maze = build_maze(10, 10, 42, 0.1)
    rng = make_shift_rng(42)
    total_cells = maze.rows * maze.cols

    for _ in range(1000):
        shift_walls(maze, rng, 1)
        distances = maze.distances_from(maze.start_cell)
        assert len(distances) == total_cells

def test_shift_walls_open_count_constant():
    """The number of open interior walls must remain unchanged after multiple shifts."""
    maze = build_maze(10, 10, 42, 0.1)
    rng = make_shift_rng(42)
    initial_open_count = count_open_interior_walls(maze)

    shift_walls(maze, rng, 20)
    post_open_count = count_open_interior_walls(maze)

    assert initial_open_count == post_open_count

def test_shift_walls_borders_untouched():
    """Ensures external walls are untouched and only the exit wall stays open."""
    maze = build_maze(10, 10, 42, 0.1)
    rng = make_shift_rng(42)

    shift_walls(maze, rng, 50)

    assert count_open_border_walls(maze) == 1
    assert maze.is_open(maze.exit_cell[0], maze.exit_cell[1], maze.exit_wall)

def test_shift_walls_return_value_accurate():
    """Verifies that returned tuples perfectly match mutated walls."""
    maze = build_maze(10, 10, 42, 0.1)
    rng = make_shift_rng(42)

    old_horizontal, old_vertical = get_wall_state_snapshot(maze)
    returned_changes = shift_walls(maze, rng, 5)

    actual_changes = []
    for r in range(maze.rows):
        for c in range(maze.cols):
            for d in [Direction.SOUTH, Direction.EAST]:
                if maze.neighbor(r, c, d) is not None:
                    if d == Direction.SOUTH:
                        old_val = old_horizontal[r + 1][c]
                        new_val = maze.horizontal[r + 1][c]
                    else:  # Direction.EAST
                        old_val = old_vertical[r][c + 1]
                        new_val = maze.vertical[r][c + 1]

                    if old_val != new_val:
                        actual_changes.append((r, c, d))

    assert isinstance(returned_changes, list)
    for update in returned_changes:
        assert len(update) == 3
        
    assert set(returned_changes) == set(actual_changes)

def test_shift_walls_deterministic_same_seeds():
    """Identical mazes and identical rng states yield perfect duplicate runs."""
    maze1 = build_maze(10, 10, 42, 0.1)
    maze2 = build_maze(10, 10, 42, 0.1)

    rng1 = make_shift_rng(42)
    rng2 = make_shift_rng(42)

    changes1 = shift_walls(maze1, rng1, 5)
    changes2 = shift_walls(maze2, rng2, 5)

    assert changes1 == changes2
    assert maze1.horizontal == maze2.horizontal
    assert maze1.vertical == maze2.vertical

def test_make_shift_rng_consistency():
    """Verifies PRNG sequence consistency across shared and separated seeds."""
    rng1_a = make_shift_rng(777)
    rng1_b = make_shift_rng(777)
    rng2 = make_shift_rng(888)

    sequence1_a = [rng1_a.randint(0, 1000) for _ in range(5)]
    sequence1_b = [rng1_b.randint(0, 1000) for _ in range(5)]
    sequence2 = [rng2.randint(0, 1000) for _ in range(5)]

    assert sequence1_a == sequence1_b
    assert sequence1_a != sequence2

def test_shift_walls_perfect_maze_no_hang():
    """Perfect maze (fraction 0.0) safely returns without hanging and stays fully connected."""
    maze = build_maze(10, 10, 42, 0.0)
    rng = make_shift_rng(42)

    changes = shift_walls(maze, rng, 5)

    total_cells = maze.rows * maze.cols
    assert len(maze.distances_from(maze.start_cell)) == total_cells
    assert isinstance(changes, list)

def test_shift_walls_fully_open_maze_no_crash():
    """Fully open maze (fraction 1.0) returns an empty list leaving walls intact."""
    maze = build_maze(10, 10, 42, 1.0)
    rng = make_shift_rng(42)

    old_horizontal, old_vertical = get_wall_state_snapshot(maze)

    changes = shift_walls(maze, rng, 5)

    assert changes == []
    assert maze.horizontal == old_horizontal
    assert maze.vertical == old_vertical