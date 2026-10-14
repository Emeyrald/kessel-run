import heapq
import copy
from collections import defaultdict
from kessel_run.planners.base import Planner
from kessel_run.robot import WallState
from kessel_run.maze import Direction

class DStarLite(Planner):
    def __init__(self, belief_map, exit_cell):
        super().__init__(belief_map, exit_cell)
        self.s_start = None
        self.s_last = None
        self.g = defaultdict(lambda: float("inf"))
        self.rhs = defaultdict(lambda: float("inf"))
        self.km = 0.0
        self.queue = []
        self.open_set = set()

        self.rhs[exit_cell] = 0.0
        heapq.heappush(self.queue, (self.calculate_key(self.exit_cell), exit_cell))
        self.open_set.add(exit_cell)

    def heuristic(self, cell1, cell2):
        if cell1 is None or cell2 is None:
            return 0
        r1, c1 = cell1
        r2, c2 = cell2
        return abs(r1 - r2) + abs(c1 - c2)

    def calculate_key(self, cell):
        start_cell = self.s_start if self.s_start is not None else cell
        k2 = min(self.g[cell], self.rhs[cell])
        k1 = k2 + self.heuristic(cell, start_cell) + self.km
    
        return (k1, k2)

    def update_vertex(self, cell):
        if cell != self.exit_cell:
            possible_scores = []

            passable_neighbors = self.passable_neighbors(cell)
            for neighbor, is_passable in passable_neighbors:
                if is_passable:
                    possible_scores.append(self.g[neighbor] + 1)

            self.rhs[cell] = min(possible_scores) if possible_scores else float("inf")

        if cell in self.open_set:
            self.open_set.remove(cell)

        if self.g[cell] != self.rhs[cell]:
            self.open_set.add(cell)
            key = self.calculate_key(cell)
            heapq.heappush(self.queue, (key, cell))

    def compute_shortest_path(self):
        old_path = copy.copy(self.current_path) if hasattr(self, "current_path") else []
        did_work = False

        while self.queue and (self.queue[0][0] < self.calculate_key(self.s_start) or self.rhs[self.s_start] != self.g[self.s_start]):
            did_work = True
            k_old, cell = heapq.heappop(self.queue)

            if cell not in self.open_set:
                continue

            k_new = self.calculate_key(cell)
            if k_old < k_new:
                heapq.heappush(self.queue, (k_new, cell))
                continue

            self.open_set.remove(cell)
            self.stats["nodes_expanded"] += 1

            if self.g[cell] > self.rhs[cell]:
                self.g[cell] = self.rhs[cell]
                for neighbor, _ in self.passable_neighbors(cell):
                    self.update_vertex(neighbor)
            else:
                self.g[cell] = float("inf")
                self.update_vertex(cell)
                for neighbor, _ in self.passable_neighbors(cell):
                    self.update_vertex(neighbor)

        if did_work:
            self.stats["replans"] += 1
            new_path = self.reconstruct_path(self.s_start) if self.s_start is not None else []
            if old_path and old_path == new_path:
                self.stats["same_path_replans"] += 1

    def reconstruct_path(self, current_cell):
        total_path = [current_cell]

        while current_cell != self.exit_cell:
            best_next = None
            min_cost = float("inf")

            for neighbor, is_passable in self.passable_neighbors(current_cell):
                if is_passable:
                    total_cost = self.g[neighbor] + 1
                    if total_cost < min_cost:
                        min_cost = total_cost
                        best_next = neighbor

            if best_next is None or min_cost == float("inf"):
                break

            current_cell = best_next
            total_path.append(current_cell)

        return total_path
    
    def update(self, changes):
        with self.time_planning():
            for r, c, d, old_state, new_state in changes:
                neighbor = self.belief_map.neighbor(r, c, d)
                if neighbor is None:
                    continue

                current_cell = (r, c)

                self.update_vertex(current_cell)
                self.update_vertex(neighbor)

            self.compute_shortest_path()

    def next_move(self, current_cell, sensor_range):
        self.s_start = current_cell
        if self.s_last is None:
            self.s_last = self.s_start
            self.compute_shortest_path()
        else:
            self.km += self.heuristic(self.s_last, self.s_start)
            self.s_last = self.s_start

        self.current_path = self.reconstruct_path(current_cell)

        if len(self.current_path) < 2:
            with self.time_planning():
                self._recover_no_path(current_cell, sensor_range)
                
                for r in range(self.belief_map.rows):
                    for c in range(self.belief_map.cols):
                        self.update_vertex((r, c))
                
                self.compute_shortest_path()
            self.current_path = self.reconstruct_path(current_cell)

        if len(self.current_path) < 2:
            raise ValueError("No valid path to the exit cell exists")

        next_cell = self.current_path[1]

        dr = next_cell[0] - current_cell[0]
        dc = next_cell[1] - current_cell[1]

        move_direction = Direction((dr, dc))
        return move_direction