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