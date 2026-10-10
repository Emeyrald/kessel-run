import random

MAX_ATTEMPTS = 100

def make_shift_rng(seed):
    return random.Random(f"{seed}-shift")

def shift_walls(maze, rng, count):
    changed_walls = []

    closed_walls = maze.closed_interior_walls()
    open_walls = maze.open_interior_walls()

    for _ in range(count):
        if not closed_walls or not open_walls:
            return changed_walls

        for _ in range(MAX_ATTEMPTS):
            closed_choice = rng.choice(closed_walls)
            open_choice = rng.choice(open_walls)

            cr, cc, cd = closed_choice
            opr, opc, opd = open_choice

            op_neighbor = maze.neighbor(opr, opc, opd)
            if op_neighbor is None:
                continue

            maze.open_wall(cr, cc, cd)

            if maze.are_connected((opr, opc), op_neighbor, open_choice):
                maze.close_wall(opr, opc, opd)

                closed_walls.remove(closed_choice)
                open_walls.append(closed_choice)

                open_walls.remove(open_choice)
                closed_walls.append(open_choice)

                changed_walls.extend([closed_choice, open_choice])

                break
            else:
                maze.close_wall(cr, cc, cd)

    return changed_walls
    