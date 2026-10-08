from enum import Enum, auto
from kessel_run.maze import WallGrid, Direction

class WallState(Enum):
    UNKNOWN = auto()
    OPEN = auto()
    CLOSED = auto()

class BeliefMap(WallGrid):
    def __init__(self, rows, cols):
        super().__init__(WallState.UNKNOWN, rows, cols)

    def is_passable(self, row, col, direction):
        return self.get_wall(row, col, direction) != WallState.CLOSED

class Robot:
    def __init__(self, rows, cols, start_cell, exit_cell, sensor_range):
        self.current_cell = start_cell
        self.exit_cell = exit_cell
        self.belief_map = BeliefMap(rows, cols)
        self.sensor_range = sensor_range

    def _observe_cell_walls(self, maze, row, col, changed):
        for side_dir in Direction:
            true_state = WallState.OPEN if maze.is_open(row, col, side_dir) else WallState.CLOSED

            if self.belief_map.get_wall(row, col, side_dir) != true_state:
                self.belief_map.set_wall(row, col, side_dir, true_state)
                changed.append((row, col, side_dir, true_state))

    def sense(self, maze):
        """
        Senses the environment up to `sensor_range` cells ahead in all 4 directions.
        
        Sensor range interpretation: "sensor_range" defines the number of cells *ahead*
        of the robot's current position that the ray will cast into. A range of 3 means
        the robot observes its current cell, plus up to 3 cells ahead in a line.
        """
        changed = []
        r_start, c_start = self.current_cell

        self._observe_cell_walls(maze, r_start, c_start, changed)

        for d in Direction:
            r, c = r_start, c_start

            for _ in range(self.sensor_range):
                if not maze.is_open(r, c, d):
                    break

                next_cell = maze.neighbor(r, c, d)

                if next_cell is None:
                    break

                r, c = next_cell

                self._observe_cell_walls(maze, r, c, changed)

        return changed

    def move(self, maze, direction):
        """Moves the robot one cell in the given direction if the path is open."""
        r, c = self.current_cell

        if not maze.is_open(r, c, direction):
            raise ValueError("Wall should be open in order to move past it")

        next_cell = maze.neighbor(r, c, direction)
        if next_cell is None:
            raise ValueError("Move is illegal: stepping outside the grid boundaries")

        self.current_cell = next_cell

    def at_goal(self):
        return self.current_cell == self.exit_cell