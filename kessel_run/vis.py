import pygame

def draw_maze(surface, maze, cell_size, offset_x, offset_y):
    width = max(1, cell_size // 10)
    for array, (dx, dy) in [(maze.horizontal, (1, 0)), (maze.vertical, (0, 1))]:
        for row_idx, row in enumerate(array):
            for col_idx, value in enumerate(row):
                if not value:
                    start_point = (col_idx * cell_size + offset_x, row_idx * cell_size + offset_y)
                    end_point = ((col_idx + dx) * cell_size + offset_x, (row_idx + dy) * cell_size + offset_y)
                    pygame.draw.line(surface, (255, 255, 255), start_point, end_point, width)

def draw_cell(surface, cell, color, cell_size, offset_x, offset_y, inset):
    r, c = cell
    x = offset_x + c * cell_size + inset
    y = offset_y + r * cell_size + inset
    width = cell_size - 2 * inset
    height = cell_size - 2 * inset
    surface.fill(color, rect=(x, y, width, height))
    