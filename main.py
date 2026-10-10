import pygame
import pygame.freetype
import random
from kessel_run.generation import build_maze
from kessel_run.vis import draw_maze, draw_cell, draw_wall, draw_robot, draw_belief_maze, cell_center
from kessel_run.shifting import make_shift_rng, shift_walls
from kessel_run.robot import Robot, WallState
from kessel_run.maze import Direction
from kessel_run.planners.astar import AStar

ROWS = 50
COLS = 50
TARGET_GRID_WIDTH = 600
TARGET_GRID_HEIGHT = 600
CELL_SIZE = min(TARGET_GRID_WIDTH // COLS, TARGET_GRID_HEIGHT // ROWS)
MARGIN = 20
TOP_BAR = 40
STATS_BAR = 30
BOTTOM_BAR = 25
TOP_FONT_SIZE = 20
BOTTOM_FONT_SIZE = 20
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FOG_COLOR = (15, 15, 15)
GREEN = (40, 167, 69)
RED = (220, 53, 69)
YELLOW = (255, 200, 0)
BLUE = (0, 150, 255)
CYAN = (0, 255, 255)
GRAY_DIM = (60, 60, 60) 
INSET = 3
CONTROL_TEXT = "Arrows: Move    [V] View    [R] Reset   [+/-] Loops   [SPACE] Pause"
PAUSE_TEXT = "Arrows: Move    [V] View    [R] Reset   [+/-] Loops   [SPACE] Unpause"
MAX_LOOPS = 1.0
MIN_LOOPS = 0.0
LOOP_FRACTION = 0.1
LOOP_STEP = 0.05
FRAMES_PER_TICK = 10 # 10 frames = 6 ticks per second
SHIFT_EVERY = 12 # 12 ticks = 2 seconds
SHIFT_COUNT = 3
FLASH_FRAMES = 30
SENSOR_RANGE = 3

KEY_TO_DIRECTION = {
    pygame.K_UP: Direction.NORTH,
    pygame.K_DOWN: Direction.SOUTH,
    pygame.K_LEFT: Direction.WEST,
    pygame.K_RIGHT: Direction.EAST,
}

def main():
    pygame.init()

    seed = random.randint(1, 1000000)
    loop_fraction = LOOP_FRACTION
    maze = build_maze(ROWS, COLS, seed, loop_fraction)
    shift_rng = make_shift_rng(seed)
    robot = Robot(maze.rows, maze.cols, maze.start_cell, maze.exit_cell, SENSOR_RANGE)
    initial_changes = robot.sense(maze)

    astar = AStar(robot.belief_map, maze.exit_cell)
    astar.update(initial_changes)

    top_font = pygame.freetype.SysFont("Arial", TOP_FONT_SIZE)
    bottom_font = pygame.freetype.SysFont("Arial", BOTTOM_FONT_SIZE)

    text_loop = top_font.get_rect("Loops: 100%")
    text_controls = bottom_font.get_rect(CONTROL_TEXT)

    grid_width = maze.cols * CELL_SIZE + 2 * MARGIN

    width = max(grid_width, text_controls.width + 2 * MARGIN)

    maze_offset_x = (width - (maze.cols * CELL_SIZE)) // 2
    
    loop_x = width - MARGIN - text_loop.width
    text_y = (TOP_BAR - text_loop.height) / 2

    maze_bottom_y = TOP_BAR + ROWS * CELL_SIZE + MARGIN
    stats_bar_y = maze_bottom_y
    bottom_bar_y = stats_bar_y + STATS_BAR
    height = bottom_bar_y + BOTTOM_BAR
    surface = pygame.display.set_mode((width, height))

    stats_text_y = stats_bar_y + (STATS_BAR - bottom_font.get_rect("A").height) / 2
    bottom_text_y = bottom_bar_y + (BOTTOM_BAR - text_controls.height) / 2
    bottom_text_x = (width - text_controls.width) / 2

    clock = pygame.time.Clock()
    pygame.key.set_repeat(300, 80)
    running = True
    rebuild = False
    paused = False

    view_mode = "TRUE"

    frames, ticks = 0, 0
    changed_walls = []
    flash_countdown = 0
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
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_v:
                    view_mode = "BELIEF" if view_mode == "TRUE" else "TRUE"

        if rebuild:
            maze = build_maze(ROWS, COLS, seed, loop_fraction)
            shift_rng = make_shift_rng(seed)
            robot = Robot(maze.rows, maze.cols, maze.start_cell, maze.exit_cell, SENSOR_RANGE)
            initial_changes = robot.sense(maze)
            astar = AStar(robot.belief_map, maze.exit_cell)
            astar.update(initial_changes)
            frames = 0
            ticks = 0
            changed_walls = []
            flash_countdown = 0
            rebuild = False

        if not paused:
            frames += 1
            if flash_countdown > 0:
                flash_countdown -= 1

            if frames % FRAMES_PER_TICK == 0:
                ticks += 1

                if ticks % SHIFT_EVERY == 0:
                    changed_walls = shift_walls(maze, shift_rng, SHIFT_COUNT)
                    flash_countdown = FLASH_FRAMES

                    sensory_changes = robot.sense(maze)
                    astar.update(sensory_changes)

                if not robot.at_exit():
                    try:
                        target_direction = astar.next_move(robot.current_cell, SENSOR_RANGE)
                        robot.move(maze, target_direction)

                        step_changes = robot.sense(maze)
                        astar.update(step_changes)
                    except (ValueError, IndexError) as e:
                        pass

        surface.fill(BLACK)

        top_font.render_to(surface, (MARGIN, text_y), f"Seed: {seed}    ({view_mode} VIEW)", WHITE)
        top_font.render_to(surface, (loop_x, text_y), f"Loops: {round(loop_fraction * 100)}%", WHITE)

        if paused:
            bottom_font.render_to(surface, (bottom_text_x, bottom_text_y), PAUSE_TEXT, WHITE)
        else:
            bottom_font.render_to(surface, (bottom_text_x, bottom_text_y), CONTROL_TEXT, WHITE)

        if view_mode == "TRUE":
            draw_maze(surface, maze, CELL_SIZE, maze_offset_x, TOP_BAR)

            if flash_countdown > 0:
                for (r, c, d) in changed_walls:
                    if not maze.is_open(r, c, d):
                        draw_wall(surface, r, c, d, CELL_SIZE, maze_offset_x, TOP_BAR, YELLOW)
        else:
            maze_pixel_width = COLS * CELL_SIZE
            maze_pixel_height = ROWS * CELL_SIZE
            surface.fill(
                GRAY_DIM, 
                rect=(maze_offset_x, TOP_BAR, maze_pixel_width, maze_pixel_height)
            )

            for r in range(ROWS):
                for c in range(COLS):
                    draw_cell(surface, (r, c), BLACK, CELL_SIZE, maze_offset_x, TOP_BAR, inset=1)

            draw_belief_maze(surface, robot, CELL_SIZE, maze_offset_x, TOP_BAR)

        draw_cell(surface, maze.start_cell, GREEN, CELL_SIZE, maze_offset_x, TOP_BAR, INSET)
        draw_cell(surface, maze.exit_cell, RED, CELL_SIZE, maze_offset_x, TOP_BAR, INSET)

        if view_mode == "BELIEF":
            planned_path = getattr(astar, 'current_path', None)
            if planned_path and len(planned_path) >= 2:
                path_points = [
                    cell_center(cell, CELL_SIZE, maze_offset_x, TOP_BAR)
                    for cell in planned_path
                ]
                pygame.draw.lines(surface, CYAN, False, path_points, width=4)

        draw_robot(surface, robot.current_cell, BLUE, CELL_SIZE, maze_offset_x, TOP_BAR)

        stats_string = (
            f"Replans: {astar.stats["replans"]} ({astar.stats["same_path_replans"]} same)    "
            f"Nodes: {astar.stats["nodes_expanded"]}    "
            f"Planning Time: {(astar.stats["total_planning_time"] * 1000):.2f} ms"
        )

        stats_rect = bottom_font.get_rect(stats_string)
        stats_text_x = (width - stats_rect.width) // 2
        bottom_font.render_to(surface, (stats_text_x, stats_text_y), stats_string, WHITE)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
