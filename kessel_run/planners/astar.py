import heapq
from kessel_run.planners.base import Planner
from kessel_run.robot import WallState
from kessel_run.maze import Direction

class AStar(Planner):
    def __init__(self, belief_map, exit_cell):
        super().__init__(belief_map, exit_cell)
        self._replan_pending = False
        self.current_path = []
        self.path_edges = set()

    def update(self, changes):
        for r, c, d, old_state, new_state in changes:
            neighbor = self.belief_map.neighbor(r, c, d)
            if neighbor is None:
                continue

            current_cell = (r, c)
            edge = frozenset([current_cell, neighbor])

            if new_state == WallState.CLOSED and edge in self.path_edges:
                self._replan_pending = True
            elif old_state == WallState.CLOSED and new_state == WallState.OPEN:
                self._replan_pending = True
    
    def next_move(self, current_cell, sensor_range):
        if self.current_path and self.current_path[0] != current_cell:
            self._replan_pending = True

        if self._replan_pending or not self.current_path:
            with self.time_planning():
                old_path = self.current_path
                self._search(current_cell, sensor_range)

                self.stats["replans"] += 1
                if old_path == self.current_path:
                    self.stats["same_path_replans"] += 1

        if len(self.current_path) < 2:
            raise ValueError("No next cell available along the path.")
        
        next_cell = self.current_path[1]
        dr = next_cell[0] - current_cell[0]
        dc = next_cell[1] - current_cell[1]
        move_direction = Direction((dr, dc))

        self._replan_pending = False
        self.current_path.pop(0)
        
        return move_direction

    def reconstruct_path(self, came_from, current_cell):
        total_path = [current_cell]

        while current_cell in came_from and came_from[current_cell] is not None:
            current_cell = came_from[current_cell]
            total_path.append(current_cell)

        total_path.reverse()
        return total_path

    def _search(self, current_cell, sensor_range):
        exit_cell = self.exit_cell
        belief_map = self.belief_map
        open_set = []
        heapq.heapify(open_set)

        sr, sc = current_cell
        er, ec = exit_cell
        h_score = abs(sr - er) + abs(sc - ec)
        f_score = h_score
        heapq.heappush(open_set, (f_score, h_score, current_cell))

        g_score = {current_cell: 0}
        came_from = {current_cell: None}

        closed_set = set()

        while open_set:
            f_score, h_score, cell = heapq.heappop(open_set)

            if cell in closed_set:
                continue

            closed_set.add(cell)
            self.stats["nodes_expanded"] += 1

            if cell == exit_cell:
                new_path = self.reconstruct_path(came_from, cell)

                self.current_path = new_path
                self.path_edges = set()
                for i in range(len(new_path) - 1):
                    u = new_path[i]
                    v = new_path[i + 1]
                    self.path_edges.add(frozenset([u, v]))

                return new_path

            passable_neighbors = self.passable_neighbors(cell)
            for neighbor, is_passable in passable_neighbors:
                if not is_passable:
                    continue

                tentative_g_score = g_score[cell] + 1

                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = cell
                    g_score[neighbor] = tentative_g_score

                    nr, nc = neighbor
                    h_score = abs(nr - er) + abs(nc - ec)
                    f_score = tentative_g_score + h_score

                    heapq.heappush(open_set, (f_score, h_score, neighbor))

        self._recover_no_path(current_cell, sensor_range)
        return self._search(current_cell, sensor_range)
