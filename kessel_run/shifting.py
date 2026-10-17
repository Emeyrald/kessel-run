import random

def make_shift_rng(seed):
    return random.Random(f"{seed}-shift")

def shift_walls(maze, rng, count):
    changed_walls = []
    closed_walls = maze.closed_interior_walls()

    for _ in range(count):
        if not closed_walls:
            break

        cr, cc, cd = closed = rng.choice(closed_walls)
        a, b = (cr, cc), maze.neighbor(cr, cc, cd)
        path_walls = maze.path_walls(a, b)

        if not path_walls:
            continue

        maze.open_wall(cr, cc, cd)
        opr, opc, opd = to_close = rng.choice(path_walls)
        maze.close_wall(opr, opc, opd)

        closed_walls.remove(closed)
        closed_walls.append(to_close)
        changed_walls.extend([closed, to_close])
        
    return changed_walls