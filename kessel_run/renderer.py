import pygame
from kessel_run.maze import Direction
from kessel_run.robot import WallState

class Renderer:
    WHITE = (255, 255, 255)    
    def __init__(self, surface, cell_size, offset_x, offset_y):
        self.surface = surface
        self.cell_size = cell_size
        self.offset_x = offset_x
        self.offset_y = offset_y

    def _draw_grid_line(self, row, col, dx, dy, color):
        width = max(1, self.cell_size // 10)
        start_point = (col * self.cell_size + self.offset_x, row * self.cell_size + self.offset_y)
        end_point = ((col + dx) * self.cell_size + self.offset_x, (row + dy) * self.cell_size + self.offset_y)
        pygame.draw.line(self.surface, color, start_point, end_point, width)

    def draw_wall(self, row, col, direction, color):
        dx, dy = 0, 0
        row_idx, col_idx = row, col
        match direction:
            case Direction.NORTH:
                dx = 1
            case Direction.SOUTH:
                row_idx += 1
                dx = 1
            case Direction.WEST:
                dy = 1
            case Direction.EAST:
                col_idx += 1
                dy = 1
            case _:
                raise ValueError(f"Invalid direction: {direction!r}")
        self._draw_grid_line(row_idx, col_idx, dx, dy, color)

    def draw_maze(self, maze):
        for array, (dx, dy) in [(maze.horizontal, (1, 0)), (maze.vertical, (0, 1))]:
            for row_idx, row in enumerate(array):
                for col_idx, value in enumerate(row):
                    if not value:
                        self._draw_grid_line(row_idx, col_idx, dx, dy, self.WHITE)

    def draw_cell(self, cell, color, inset):
        r, c = cell
        x = self.offset_x + c * self.cell_size + inset
        y = self.offset_y + r * self.cell_size + inset
        width = self.cell_size - 2 * inset
        height = self.cell_size - 2 * inset
        self.surface.fill(color, rect=(x, y, width, height))

    def cell_center(self, cell):
        r, c = cell
        center_x = self.offset_x + (c * self.cell_size) + (self.cell_size // 2)
        center_y = self.offset_y + (r * self.cell_size) + (self.cell_size // 2)
        return (center_x, center_y)

    def draw_robot(self, cell, color, radius_ratio=0.35):
        center = self.cell_center(cell)

        radius = int(self.cell_size * radius_ratio)

        pygame.draw.circle(self.surface, color, center, radius)

    def draw_belief_maze(self, robot):
        belief_map = robot.belief_map
        for array, (dx, dy) in [(belief_map.horizontal, (1, 0)), (belief_map.vertical, (0, 1))]:
            for row_idx, row in enumerate(array):
                for col_idx, state in enumerate(row):
                    if state == WallState.CLOSED:
                        self._draw_grid_line(row_idx, col_idx, dx, dy, self.WHITE)