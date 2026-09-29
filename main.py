import pygame
import pygame.freetype
import random
from kessel_run.maze import Maze
from kessel_run.generation import generate
from kessel_run.vis import draw_maze

ROWS = 15
COLS = 15
CELL_SIZE = 20
MARGIN = 20
TOP_BAR = 40
FONT_SIZE = 20
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RESET_TEXT = "Press [R] to Reset"

def create_new_maze(rows, cols):
    """Generates a new maze object alongside its random seed."""
    new_maze = Maze(rows, cols)
    new_seed = random.randint(1, 1000000)
    new_rng = random.Random(new_seed)
    generate(new_maze, new_rng)
    return new_maze, new_seed

def main():
    pygame.init()

    maze, seed = create_new_maze(ROWS, COLS)

    width = maze.cols * CELL_SIZE + 2 * MARGIN
    height = TOP_BAR + maze.rows * CELL_SIZE + 2 * MARGIN
    surface = pygame.display.set_mode((width, height))
    font = pygame.freetype.SysFont("Arial", FONT_SIZE)

    text_rect = font.get_rect(RESET_TEXT)
    reset_x = width - MARGIN - text_rect.width
    text_y = (TOP_BAR - text_rect.height) / 2
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    maze, seed = create_new_maze(ROWS, COLS)

        surface.fill(BLACK)

        font.render_to(surface, (MARGIN, text_y), f"Seed: {seed}", WHITE)
        font.render_to(surface, (reset_x, text_y), RESET_TEXT, WHITE)

        draw_maze(surface, maze, CELL_SIZE, MARGIN, TOP_BAR)
        pygame.display.flip()

        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
