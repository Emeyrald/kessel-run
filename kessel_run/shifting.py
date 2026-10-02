import random

MAX_ATTEMPTS = 100

def make_shift_rng(seed):
    return random.Random(f"{seed}-shift")

def shift_walls(maze, rng, count):
    changed_walls = []

    for _ in range(count):
        closed_walls = maze.closed_interior_walls()
        open_walls = maze.open_interior_walls()
        if not closed_walls or not open_walls:
            return changed_walls

        for _ in range(MAX_ATTEMPTS):
            cr, cc, cd = rng.choice(closed_walls)
            opr, opc, opd = rng.choice(open_walls)

            maze.open_wall(cr, cc, cd)
            maze.close_wall(opr, opc, opd)

            distances = maze.distances_from(maze.start_cell)
            if len(distances) != maze.rows * maze.cols:
                maze.close_wall(cr, cc, cd)
                maze.open_wall(opr, opc, opd)
            else:
                changed_walls.append((cr, cc, cd))
                changed_walls.append((opr, opc, opd))
                break

    return changed_walls
    