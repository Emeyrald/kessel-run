import pygame
from kessel_run.maze import Direction

def draw_grid_line(surface, row, col, dx, dy, cell_size, offset_x, offset_y, color):
    width = max(1, cell_size // 10)
    start_point = (col * cell_size + offset_x, row * cell_size + offset_y)
    end_point = ((col + dx) * cell_size + offset_x, (row + dy) * cell_size + offset_y)
    pygame.draw.line(surface, color, start_point, end_point, width)

def draw_wall(surface, row, col, direction, cell_size, offset_x, offset_y, color):
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

    draw_grid_line(surface, row_idx, col_idx, dx, dy, cell_size, offset_x, offset_y, color)

def draw_maze(surface, maze, cell_size, offset_x, offset_y):
    for array, (dx, dy) in [(maze.horizontal, (1, 0)), (maze.vertical, (0, 1))]:
        for row_idx, row in enumerate(array):
            for col_idx, value in enumerate(row):
                if not value:
                    draw_grid_line(surface, row_idx, col_idx, dx, dy, cell_size, offset_x, offset_y, (255, 255, 255))

def draw_cell(surface, cell, color, cell_size, offset_x, offset_y, inset):
    r, c = cell
    x = offset_x + c * cell_size + inset
    y = offset_y + r * cell_size + inset
    width = cell_size - 2 * inset
    height = cell_size - 2 * inset
    surface.fill(color, rect=(x, y, width, height))
    