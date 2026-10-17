"""
Headless A* vs D* Lite benchmark. Runs the same tick loop as main.py, minus drawing,
and writes one CSV row per (config, seed, planner).

    python benchmark.py --estimate          # time seed 0 of every config, project the full run
    python benchmark.py --seeds 5           # quick pass to sanity-check the plots
    python benchmark.py                     # full run (seeds 0-29, every sweep)
    python benchmark.py --sweep shift_count --seeds 10
"""
import argparse
import csv
import subprocess
import time
from dataclasses import dataclass, asdict, replace
from pathlib import Path

from kessel_run.generation import build_maze
from kessel_run.shifting import make_shift_rng, shift_walls
from kessel_run.robot import Robot
from kessel_run.planners.astar import AStar
from kessel_run.planners.dstar_lite import DStarLite

PLANNERS = {"astar": AStar, "dstar_lite": DStarLite}
MAX_TICKS_PER_CELL = 20
DEFAULT_OUT = Path("results") / "benchmark.csv"

@dataclass(frozen=True)
class Config:
    size: int = 50
    loop_fraction: float = 0.1
    shift_every: int = 5
    shift_count: int = 3
    sensor_range: int = 3

BASELINE = Config()

# One sweep per variable; every other field stays at BASELINE.
SWEEPS = {
    "shift_count": [1, 2, 4, 8, 16, 32],
    "shift_every": [1, 2, 5, 10, 20, 50],
    "sensor_range": [1, 2, 3, 5, 8],
    "loop_fraction": [0.0, 0.05, 0.1, 0.2, 0.4],
    "size": [25, 50, 75, 100],
}

FIELDS = [
    "commit", "dirty", "planner", "seed",
    *Config.__dataclass_fields__,
    "max_ticks", "success", "error", "ticks", "steps", "bfs_distance", "step_ratio", "stuck_ticks",
    "replans", "same_path_replans", "nodes_expanded", "planning_time_s",
    "nodes_per_replan", "time_per_replan_ms", "wall_time_s",
]

def update_planner(planner, changes, cell):
    """D* Lite needs the robot's cell to track its key modifier; A* doesn't take it."""
    if isinstance(planner, DStarLite):
        planner.update(changes, cell)
    else:
        planner.update(changes)

def run_trial(config, seed, planner_cls, max_ticks=None):
    """Race one planner through one shifting maze. The shift rng never depends on the robot,
    so every planner given the same (config, seed) faces exactly the same sequence of mazes."""
    maze = build_maze(config.size, config.size, seed, config.loop_fraction)
    shift_rng = make_shift_rng(seed)
    max_ticks = max_ticks or MAX_TICKS_PER_CELL * config.size * config.size
    bfs_distance = maze.distances_from(maze.start_cell)[maze.exit_cell]

    robot = Robot(maze.rows, maze.cols, maze.start_cell, maze.exit_cell, config.sensor_range)
    planner = planner_cls(robot.belief_map, maze.exit_cell)
    update_planner(planner, robot.sense(maze), robot.current_cell)

    ticks, steps, stuck_ticks, error = 0, 0, 0, ""
    start = time.perf_counter()

    while not robot.at_exit() and ticks < max_ticks:
        ticks += 1

        if ticks % config.shift_every == 0:
            shift_walls(maze, shift_rng, config.shift_count)

        update_planner(planner, robot.sense(maze), robot.current_cell)
        try:
            direction = planner.next_move(robot.current_cell, config.sensor_range)
            robot.move(maze, direction)
            steps += 1
            update_planner(planner, robot.sense(maze), robot.current_cell)
        except (ValueError, IndexError):
            # Same as the viewer: the robot loses this tick but the run continues.
            stuck_ticks += 1
        except RecursionError:
            error = "RecursionError"
            break

    wall_time = time.perf_counter() - start
    stats = planner.stats
    replans = stats["replans"]

    return {
        "planner": planner_cls.__name__,
        "seed": seed,
        **asdict(config),
        "max_ticks": max_ticks,
        "success": robot.at_exit(),
        "error": error,
        "ticks": ticks,
        "steps": steps,
        "bfs_distance": bfs_distance,
        "step_ratio": steps / bfs_distance if bfs_distance else "",
        "stuck_ticks": stuck_ticks,
        "replans": replans,
        "same_path_replans": stats["same_path_replans"],
        "nodes_expanded": stats["nodes_expanded"],
        "planning_time_s": stats["total_planning_time"],
        "nodes_per_replan": stats["nodes_expanded"] / replans if replans else "",
        "time_per_replan_ms": stats["total_planning_time"] * 1000 / replans if replans else "",
        "wall_time_s": wall_time,
    }

def sweep_configs(sweep_names):
    """Unique configs across the chosen sweeps. BASELINE shows up in every sweep but runs once."""
    configs = []
    for name in sweep_names:
        for value in SWEEPS[name]:
            config = replace(BASELINE, **{name: value})
            if config not in configs:
                configs.append(config)
    return configs

def git_info():
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "*.py", "requirements.txt"], capture_output=True, text=True, check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return "unknown", ""
    return commit, dirty

def format_duration(seconds):
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}h {minutes:02d}m {secs:02d}s"

def estimate(configs, n_seeds):
    """Time seed 0 of every config with both planners and multiply out."""
    total = 0.0
    for config in configs:
        elapsed = 0.0
        for planner_cls in PLANNERS.values():
            t = time.perf_counter()
            result = run_trial(config, 0, planner_cls)
            elapsed += time.perf_counter() - t
            if not result["success"]:
                print(f"  note: {planner_cls.__name__} did not finish seed 0 of {config}")
        total += elapsed * n_seeds
        print(f"{config}: {elapsed:6.2f} s per seed (both planners) -> ~{format_duration(elapsed * n_seeds)} for {n_seeds} seeds")
    print(f"\nEstimated total: ~{format_duration(total)} (seed 0 only; real seeds vary, so treat this as rough)")

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=30, help="run seeds 0..N-1 for every config (default 30)")
    parser.add_argument("--sweep", action="append", choices=SWEEPS, help="sweep to run; repeat for several (default: all)")
    parser.add_argument("--planner", action="append", choices=PLANNERS, help="planner to run; repeat for several (default: both)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"CSV path (default {DEFAULT_OUT})")
    parser.add_argument("--estimate", action="store_true", help="time seed 0 of each config and project the full run")
    args = parser.parse_args()

    configs = sweep_configs(args.sweep or list(SWEEPS))
    planners = [PLANNERS[name] for name in (args.planner or PLANNERS)]

    if args.estimate:
        estimate(configs, args.seeds)
        return

    commit, dirty = git_info()
    if dirty:
        print("warning: working tree has uncommitted changes; the commit hash won't fully describe this code")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    total = len(configs) * args.seeds * len(planners)
    done = 0
    start = time.perf_counter()

    # Sequential on purpose: parallel trials compete for the CPU and add noise to the timings.
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for config in configs:
            for seed in range(args.seeds):
                for planner_cls in planners:
                    row = run_trial(config, seed, planner_cls)
                    writer.writerow({"commit": commit, "dirty": dirty, **row})
                    f.flush()
                    done += 1
                    status = "ok" if row["success"] else "FAILED"
                    print(f"[{done}/{total}] {format_duration(time.perf_counter() - start)}  "
                          f"{row['planner']:<9} seed={seed:<3} {config}  {status}")

    print(f"\nWrote {total} rows to {args.out}")

if __name__ == "__main__":
    main()
