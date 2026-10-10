import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from kessel_run.maze import Direction
from kessel_run.robot import WallState

class Planner(ABC):
    """
    Initializes the base planner
    Subclasses should call super().__init__(belief_map, exit_cell) first.
    """
    def __init__(self, belief_map, exit_cell):
        self.belief_map = belief_map
        self.exit_cell = exit_cell

        self.current_path = []

        self.stats = {
            "replans": 0,
            "nodes_expanded": 0,
            "total_planning_time": 0, # In seconds
            "same_path_replans": 0,
        }

    @abstractmethod
    def update(self, changes):
        """
        Processes environmental map changes. 
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def next_move(self, current_cell):
        """
        Determines the next coordinate node to navigate towards.
        Must be implemented by subclasses.
        """
        pass

    def passable_neighbors(self, current_cell):
        row, col = current_cell

        for d in Direction:
            neighbor_cell = self.belief_map.neighbor(row, col, d)

            if neighbor_cell is None:
                continue

            is_passable = self.belief_map.is_passable(row, col, d)

            yield neighbor_cell, is_passable

    @contextmanager
    def time_planning(self):
        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start_time
            self.stats["total_planning_time"] += elapsed

    def _recover_no_path(self, current_cell, sensor_range):
        visible_cells = set([current_cell])
        r_start, c_start = current_cell

        for d in Direction:
            r, c = r_start, c_start
            for _ in range(sensor_range):
                if self.belief_map.get_wall(r, c, d) == WallState.CLOSED:
                    break

                next_cell = self.belief_map.neighbor(r, c, d)
                if next_cell is None:
                    break

                r, c = next_cell
                visible_cells.add((r, c))

        for r in range(self.belief_map.rows):
            for c in range(self.belief_map.cols):
                if (r, c) not in visible_cells:
                    for d in Direction:
                        if self.belief_map.get_wall(r, c, d) == WallState.CLOSED:
                            self.belief_map.set_wall(r, c, d, WallState.UNKNOWN)