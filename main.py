import argparse
import imageio
import pygame
import pygame.freetype
import random
from kessel_run.generation import build_maze
from kessel_run.renderer import Renderer
from kessel_run.shifting import make_shift_rng, shift_walls
from kessel_run.robot import Robot, WallState
from kessel_run.maze import Direction
from kessel_run.planners.astar import AStar
from kessel_run.planners.dstar_lite import DStarLite

ROWS = 50
COLS = 50

TARGET_GRID_WIDTH = 400
TARGET_GRID_HEIGHT = 400

MARGIN = 20
TOP_BAR = 40
STATS_BAR = 80
BOTTOM_BAR = 25
TOP_FONT_SIZE = 20
BOTTOM_FONT_SIZE = 20
LINE_HEIGHT = 18

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FOG_COLOR = (15, 15, 15)
GREEN = (40, 167, 69)
RED = (220, 53, 69)
YELLOW = (255, 200, 0)
BLUE = (0, 150, 255)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
GRAY_DIM = (60, 60, 60) 
INSET = 2

CONTROL_TEXT = "Arrows: Move    [V] View    [R] Reset   [+/-] Loops   [SPACE] Pause"
PAUSE_TEXT = "Arrows: Move    [V] View    [R] Reset   [+/-] Loops   [SPACE] Unpause"
MAX_LOOPS = 1.0
MIN_LOOPS = 0.0
LOOP_FRACTION = 0.1
LOOP_STEP = 0.05
FRAMES_PER_TICK = 10 # 10 frames = 6 ticks per second
SHIFT_EVERY = 12 # 12 ticks = 2 seconds
SHIFT_COUNT = 8
FLASH_FRAMES = 30
SENSOR_RANGE = 5

RECORD_FPS = 10 # One GIF frame per tick, played a little faster than live
RECORD_SCALE = 0.6 # Keeps the GIF under GitHub's README width
RECORD_MAX_FRAMES = 600
RECORD_HOLD_FRAMES = 15 # Hold the finish for 1.5 seconds before looping

KEY_TO_DIRECTION = {
    pygame.K_UP: Direction.NORTH,
    pygame.K_DOWN: Direction.SOUTH,
    pygame.K_LEFT: Direction.WEST,
    pygame.K_RIGHT: Direction.EAST,
}

def capture_frame(surface):
    width, height = surface.get_size()
    scaled = pygame.transform.smoothscale(surface, (int(width * RECORD_SCALE), int(height * RECORD_SCALE)))
    return pygame.surfarray.array3d(scaled).swapaxes(0, 1)

def save_gif(path, frames):
    frames = frames + [frames[-1]] * RECORD_HOLD_FRAMES
    imageio.mimsave(path, frames, duration=1000 / RECORD_FPS, loop=0)
    print(f"Saved {len(frames)} frames to {path}")

def main(rows=ROWS, cols=COLS, seed=None, record_path=None):
    pygame.init()

    if seed is None:
        seed = random.randint(1, 1000000)
    loop_fraction = LOOP_FRACTION
    cell_size = min(TARGET_GRID_WIDTH // cols, TARGET_GRID_HEIGHT // rows)

    maze = build_maze(rows, cols, seed, loop_fraction)
    shift_rng = make_shift_rng(seed)

    astar_robot = Robot(maze.rows, maze.cols, maze.start_cell, maze.exit_cell, SENSOR_RANGE)
    dstar_robot = Robot(maze.rows, maze.cols, maze.start_cell, maze.exit_cell, SENSOR_RANGE)

    initial_changes = astar_robot.sense(maze)
    astar = AStar(astar_robot.belief_map, maze.exit_cell)
    astar.update(initial_changes)

    dstar_lite = DStarLite(dstar_robot.belief_map, maze.exit_cell)
    dstar_lite.update(initial_changes, dstar_robot.current_cell)

    top_font = pygame.freetype.SysFont("Arial", TOP_FONT_SIZE)
    bottom_font = pygame.freetype.SysFont("Arial", BOTTOM_FONT_SIZE)

    grid_pixel_width = cols * cell_size
    grid_pixel_height = rows * cell_size

    left_offset_x = MARGIN
    mid_offset_x = left_offset_x + grid_pixel_width + MARGIN
    right_offset_x = mid_offset_x + grid_pixel_width + MARGIN

    width = right_offset_x + grid_pixel_width + MARGIN
    text_loop = top_font.get_rect("Loops: 100%")
    loop_x = width - MARGIN - text_loop.width
    text_y = (TOP_BAR - text_loop.height) / 2

    maze_bottom_y = TOP_BAR + grid_pixel_height + MARGIN
    stats_bar_y = maze_bottom_y
    bottom_bar_y = stats_bar_y + STATS_BAR
    height = bottom_bar_y + BOTTOM_BAR

    surface = pygame.display.set_mode((width, height))
    bottom_text_y = bottom_bar_y + (BOTTOM_BAR - bottom_font.get_rect(CONTROL_TEXT).height) / 2
    bottom_text_x = (width - bottom_font.get_rect(CONTROL_TEXT).width) / 2

    renderer_left = Renderer(surface, cell_size, left_offset_x, TOP_BAR)
    renderer_mid = Renderer(surface, cell_size, mid_offset_x, TOP_BAR)
    renderer_right = Renderer(surface, cell_size, right_offset_x, TOP_BAR)

    clock = pygame.time.Clock()
    pygame.key.set_repeat(300, 80)

    running = True
    rebuild = False
    paused = False

    frames, ticks = 0, 0
    changed_walls = []
    flash_countdown = 0
    recorded_frames = []

    while running:
        tick_this_frame = False

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

        if rebuild:
            maze = build_maze(rows, cols, seed, loop_fraction)
            shift_rng = make_shift_rng(seed)
            astar_robot = Robot(maze.rows, maze.cols, maze.start_cell, maze.exit_cell, SENSOR_RANGE)
            dstar_robot = Robot(maze.rows, maze.cols, maze.start_cell, maze.exit_cell, SENSOR_RANGE)
            initial_changes = astar_robot.sense(maze)
            astar = AStar(astar_robot.belief_map, maze.exit_cell)
            astar.update(initial_changes)
            dstar_lite = DStarLite(dstar_robot.belief_map, maze.exit_cell)
            dstar_lite.update(initial_changes, dstar_robot.current_cell)
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
                tick_this_frame = True

                if ticks % SHIFT_EVERY == 0:
                    changed_walls = shift_walls(maze, shift_rng, SHIFT_COUNT)
                    flash_countdown = FLASH_FRAMES

                if not astar_robot.at_exit():
                    astar_changes = astar_robot.sense(maze)
                    astar.update(astar_changes)
                    try:
                        target_direction = astar.next_move(astar_robot.current_cell, SENSOR_RANGE)
                        astar_robot.move(maze, target_direction)

                        step_changes = astar_robot.sense(maze)
                        astar.update(step_changes)
                    except (ValueError, IndexError) as e:
                        pass

                
                if not dstar_robot.at_exit():
                    dstar_changes = dstar_robot.sense(maze)
                    dstar_lite.update(dstar_changes, dstar_robot.current_cell)
                    try:
                        target_direction = dstar_lite.next_move(dstar_robot.current_cell, SENSOR_RANGE)
                        dstar_robot.move(maze, target_direction)

                        step_changes = dstar_robot.sense(maze)
                        dstar_lite.update(step_changes, dstar_robot.current_cell)
                    except (ValueError, IndexError) as e:
                        pass

        surface.fill(BLACK)

        top_font.render_to(surface, (MARGIN, text_y), f"Seed: {seed}", WHITE)
        top_font.render_to(surface, (loop_x, text_y), f"Loops: {round(loop_fraction * 100)}%", WHITE)

        if paused:
            bottom_font.render_to(surface, (bottom_text_x, bottom_text_y), PAUSE_TEXT, WHITE)
        else:
            bottom_font.render_to(surface, (bottom_text_x, bottom_text_y), CONTROL_TEXT, WHITE)

        # Draw A* belief maze
        surface.fill(GRAY_DIM, rect=(left_offset_x, TOP_BAR, grid_pixel_width, grid_pixel_height))
        for r in range(rows):
            for c in range(cols):
                renderer_left.draw_cell((r, c), BLACK, inset=1)

        renderer_left.draw_belief_maze(astar_robot)

        renderer_left.draw_cell(maze.start_cell, GREEN, INSET)
        renderer_left.draw_cell(maze.exit_cell, RED, INSET)

        planned_path_astar = getattr(astar, 'current_path', None)
        if planned_path_astar and len(planned_path_astar) >= 2:
            path_points = [renderer_left.cell_center(cell) for cell in planned_path_astar]
            pygame.draw.lines(surface, CYAN, False, path_points, width=4)

        renderer_left.draw_robot(astar_robot.current_cell, BLUE)

        # Draw true maze
        renderer_mid.draw_maze(maze)
        if flash_countdown > 0:
            for (r, c, d) in changed_walls:
                if not maze.is_open(r, c, d):
                    renderer_mid.draw_wall(r, c, d, YELLOW)

        renderer_mid.draw_cell(maze.start_cell, GREEN, INSET)
        renderer_mid.draw_cell(maze.exit_cell, RED, INSET)

        renderer_mid.draw_robot(astar_robot.current_cell, BLUE)
        renderer_mid.draw_robot(dstar_robot.current_cell, MAGENTA)
        
        # Draw D* Lite belief maze
        surface.fill(GRAY_DIM, rect=(right_offset_x, TOP_BAR, grid_pixel_width, grid_pixel_height))
        for r in range(rows):
            for c in range(cols):
                renderer_right.draw_cell((r, c), BLACK, inset=1)

        renderer_right.draw_belief_maze(dstar_robot)

        renderer_right.draw_cell(maze.start_cell, GREEN, INSET)
        renderer_right.draw_cell(maze.exit_cell, RED, INSET)

        planned_path_dstar = getattr(dstar_lite, 'current_path', None)
        if planned_path_dstar and len(planned_path_dstar) >= 2:
            path_points = [renderer_right.cell_center(cell) for cell in planned_path_dstar]
            pygame.draw.lines(surface, YELLOW, False, path_points, width=4)

        renderer_right.draw_robot(dstar_robot.current_cell, MAGENTA)

        # Left Layout
        bottom_font.render_to(surface, (left_offset_x, stats_bar_y + 2), "A* BELIEF MAP", CYAN)
        astar_line1 = f"Replans: {astar.stats['replans']} ({astar.stats['same_path_replans']} same)"
        astar_line2 = f"Nodes: {astar.stats['nodes_expanded']}"
        astar_line3 = f"Planning Time: {(astar.stats['total_planning_time'] * 1000):.2f} ms"
        bottom_font.render_to(surface, (left_offset_x, stats_bar_y + 2 + LINE_HEIGHT), astar_line1, WHITE)
        bottom_font.render_to(surface, (left_offset_x, stats_bar_y + 2 + LINE_HEIGHT * 2), astar_line2, WHITE)
        bottom_font.render_to(surface, (left_offset_x, stats_bar_y + 2 + LINE_HEIGHT * 3), astar_line3, WHITE)
        
        # Middle Layout
        mid_label = "TRUE MAZE"
        mid_rect = bottom_font.get_rect(mid_label)
        bottom_font.render_to(surface, (mid_offset_x + (grid_pixel_width - mid_rect.width) // 2, stats_bar_y + 2), mid_label, WHITE)
        
        # Right Layout
        dstar_title = "D* LITE BELIEF MAP"
        dstar_rect = bottom_font.get_rect(dstar_title)
        bottom_font.render_to(surface, (right_offset_x + grid_pixel_width - dstar_rect.width, stats_bar_y + 2), dstar_title, YELLOW)
        dstar_line1 = f"Replans: {dstar_lite.stats['replans']} ({dstar_lite.stats['same_path_replans']} same)"
        dstar_line2 = f"Nodes: {dstar_lite.stats['nodes_expanded']}"
        dstar_line3 = f"Planning Time: {(dstar_lite.stats['total_planning_time'] * 1000):.2f} ms"
        bottom_font.render_to(surface, (right_offset_x + grid_pixel_width - bottom_font.get_rect(dstar_line1).width, stats_bar_y + 2 + LINE_HEIGHT), dstar_line1, WHITE)
        bottom_font.render_to(surface, (right_offset_x + grid_pixel_width - bottom_font.get_rect(dstar_line2).width, stats_bar_y + 2 + LINE_HEIGHT * 2), dstar_line2, WHITE)
        bottom_font.render_to(surface, (right_offset_x + grid_pixel_width - bottom_font.get_rect(dstar_line3).width, stats_bar_y + 2 + LINE_HEIGHT * 3), dstar_line3, WHITE)

        if record_path and tick_this_frame:
            recorded_frames.append(capture_frame(surface))
            race_over = astar_robot.at_exit() and dstar_robot.at_exit()
            if race_over or len(recorded_frames) >= RECORD_MAX_FRAMES:
                running = False

        pygame.display.flip()
        clock.tick(60)

    if record_path and recorded_frames:
        save_gif(record_path, recorded_frames)

    pygame.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Watch A* and D* Lite race through a shifting maze.")
    parser.add_argument("--size", type=int, default=ROWS, help=f"maze is SIZE x SIZE (default {ROWS})")
    parser.add_argument("--seed", type=int, help="maze seed (default: random)")
    parser.add_argument("--record", metavar="PATH", help="save the race as a GIF, then quit once both robots finish")
    args = parser.parse_args()
    main(args.size, args.size, args.seed, args.record)
