import pygame
import pygame.freetype
import random
from kessel_run.generation import build_maze
from kessel_run.vis import draw_maze, draw_cell

ROWS = 15
COLS = 15
CELL_SIZE = 20
MARGIN = 20
TOP_BAR = 40
BOTTOM_BAR = 25
TOP_FONT_SIZE = 20
BOTTOM_FONT_SIZE = 20
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (40, 167, 69)
RED = (220, 53, 69)
INSET = 3
CONTROL_TEXT = "[R] Reset   [+/-] Loops"
MAX_LOOPS = 1.0
MIN_LOOPS = 0.0
LOOP_FRACTION = 0.1
LOOP_STEP = 0.05

def main():
    pygame.init()

    seed = random.randint(1, 1000000)
    loop_fraction = LOOP_FRACTION
    maze = build_maze(ROWS, COLS, seed, loop_fraction)
    
    width = maze.cols * CELL_SIZE + 2 * MARGIN
    
    bottom_bar_y = TOP_BAR + ROWS * CELL_SIZE + MARGIN
    height = bottom_bar_y + BOTTOM_BAR
    surface = pygame.display.set_mode((width, height))
    top_font = pygame.freetype.SysFont("Arial", TOP_FONT_SIZE)
    bottom_font = pygame.freetype.SysFont("Arial", BOTTOM_FONT_SIZE)

    text_loop = top_font.get_rect("Loops: 100%")
    loop_x = width - MARGIN - text_loop.width
    text_y = (TOP_BAR - text_loop.height) / 2

    text_controls = bottom_font.get_rect(CONTROL_TEXT)
    bottom_text_y = bottom_bar_y + (BOTTOM_BAR - text_controls.height) / 2
    bottom_text_x = (width - text_controls.width) / 2

    clock = pygame.time.Clock()
    pygame.key.set_repeat(300, 80)
    running = True
    rebuild = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    seed = random.randint(1, 1000000)
                    rebuild = True
                if event.key == pygame.K_EQUALS:
                    loop_fraction = round(min(loop_fraction + LOOP_STEP, MAX_LOOPS), 2)
                    rebuild = True
                if event.key == pygame.K_MINUS:
                    loop_fraction = round(max(loop_fraction - LOOP_STEP, MIN_LOOPS), 2)
                    rebuild = True

        if rebuild:
            maze = build_maze(ROWS, COLS, seed, loop_fraction)
            rebuild = False

        surface.fill(BLACK)

        top_font.render_to(surface, (MARGIN, text_y), f"Seed: {seed}", WHITE)
        top_font.render_to(surface, (loop_x, text_y), f"Loops: {round(loop_fraction * 100)}%", WHITE)

        bottom_font.render_to(surface, (bottom_text_x, bottom_text_y), CONTROL_TEXT, WHITE)

        draw_cell(surface, maze.start_cell, GREEN, CELL_SIZE, MARGIN, TOP_BAR, INSET)
        draw_cell(surface, maze.exit_cell, RED, CELL_SIZE, MARGIN, TOP_BAR, INSET)
        draw_maze(surface, maze, CELL_SIZE, MARGIN, TOP_BAR)
        pygame.display.flip()

        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
