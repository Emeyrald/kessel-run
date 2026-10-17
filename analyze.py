"""
Reads the benchmark CSV and makes one figure per sweep: the metric per planner on the left,
the paired D* Lite / A* ratio on the right. Never reruns trials, so replotting is instant.

    python analyze.py
    python analyze.py --metric time_per_replan_ms
    python analyze.py --csv results/benchmark.csv --out docs
"""
import argparse
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullLocator

from benchmark import BASELINE, SWEEPS, DEFAULT_OUT

CONFIG_FIELDS = list(asdict(BASELINE))
PLANNERS = {"AStar": "A*", "DStarLite": "D* Lite"}

X_LABELS = {
    "shift_count": "Walls swapped per shift",
    "shift_every": "Ticks between shifts",
    "sensor_range": "Sensor range (cells)",
    "loop_fraction": "Loop fraction",
    "size": "Maze size (N × N)",
}
METRIC_LABELS = {
    "nodes_per_replan": "Nodes expanded per replan",
    "time_per_replan_ms": "Planning time per replan (ms)",
    "nodes_expanded": "Total nodes expanded",
    "planning_time_s": "Total planning time (s)",
    "replans": "Replans",
    "step_ratio": "Steps ÷ initial BFS distance",
}
LOG_X = {"shift_count", "shift_every"}
RATIO_TICKS = [0.1, 0.2, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 10]
DODGE = 0.012 # Fraction of the x-range each planner shifts sideways so error bars don't overlap

# Reference palette, light surface: slots 1-2 validated as a pair; inks and chrome from the same system.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = {"AStar": ("#2a78d6", "o"), "DStarLite": ("#eb6834", "s")}

def bootstrap_ci(values, n_boot=2000, seed=0):
    """95% percentile-bootstrap interval for the mean. Makes no normality assumption, which matters at 5-30 seeds."""
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = rng.choice(values, size=(n_boot, len(values))).mean(axis=1)
    return tuple(np.percentile(means, [2.5, 97.5]))

def sweep_rows(df, var):
    """Rows where every config field except `var` sits at BASELINE."""
    mask = np.ones(len(df), dtype=bool)
    for field, value in asdict(BASELINE).items():
        if field != var:
            mask &= np.isclose(df[field], value)
    return df[mask]

def paired(df, metric):
    """One row per (config, seed) where both planners reached the exit, one metric column per planner.
    Comparing only shared seeds keeps the comparison paired: same maze, same shifts."""
    ok = df[df["success"] & df[metric].notna()]
    wide = ok.pivot_table(index=CONFIG_FIELDS + ["seed"], columns="planner", values=metric)
    return wide.reindex(columns=list(PLANNERS)).dropna().reset_index()

def dodge(xs, var, offset):
    """Nudge a series sideways by `offset` units of DODGE, in log or linear space to match the axis."""
    xs = np.asarray(xs, dtype=float)
    if var in LOG_X:
        return xs * np.exp(offset * DODGE * np.log(xs.max() / xs.min()))
    return xs + offset * DODGE * (xs.max() - xs.min())

def style_axes(ax, var, values):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if var in LOG_X:
        ax.set_xscale("log")
    ax.set_xticks(values)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlabel(X_LABELS[var], color=INK_SECONDARY, fontsize=10)

def plot_sweep(df, var, metric, out_dir):
    wide = paired(sweep_rows(df, var), metric)
    if wide.empty:
        print(f"{var}: no seeds where both planners succeeded, skipping")
        return

    xs = sorted(wide[var].unique())
    fig, (ax_abs, ax_ratio) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)

    # Left: each planner's metric, mean and 95% CI over shared seeds
    all_values = []
    for offset, (planner, name) in zip((-1, 1), PLANNERS.items()):
        color, marker = SERIES[planner]
        means, lows, highs = [], [], []
        for x in xs:
            values = wide.loc[wide[var] == x, planner]
            lo, hi = bootstrap_ci(values)
            means.append(values.mean())
            lows.append(lo)
            highs.append(hi)
        means = np.array(means)
        yerr = np.array([means - np.array(lows), np.array(highs) - means])
        x_plot = dodge(xs, var, offset)
        ax_abs.errorbar(x_plot, means, yerr=np.nan_to_num(yerr), color=color, marker=marker, markersize=6,
                        linewidth=2, capsize=3, elinewidth=1, markeredgecolor=SURFACE, label=name, zorder=3)
        ax_abs.annotate(name, (x_plot[-1], means[-1]), xytext=(8, 0), textcoords="offset points",
                        va="center", fontsize=9, color=INK_SECONDARY)
        all_values.extend(means)

    style_axes(ax_abs, var, xs)
    positive = [v for v in all_values if v > 0]
    if positive and max(positive) / min(positive) > 30:
        ax_abs.set_yscale("log")
    ax_abs.set_ylabel(METRIC_LABELS.get(metric, metric), color=INK_SECONDARY, fontsize=10)
    ax_abs.set_title("Per planner (mean, 95% CI)", color=INK, fontsize=10, loc="left")
    ax_abs.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, loc="best")

    # Right: paired ratio per seed, geometric mean (the right average for ratios) and 95% CI
    ratios, lows, highs = [], [], []
    for x in xs:
        group = wide[(wide[var] == x) & (wide["AStar"] > 0) & (wide["DStarLite"] > 0)]
        log_ratio = np.log(group["DStarLite"] / group["AStar"])
        lo, hi = bootstrap_ci(log_ratio)
        ratios.append(np.exp(log_ratio.mean()))
        lows.append(np.exp(lo))
        highs.append(np.exp(hi))
    ratios = np.array(ratios)
    yerr = np.array([ratios - np.array(lows), np.array(highs) - ratios])

    ax_ratio.axhline(1, color=INK_MUTED, linewidth=1, linestyle="--", zorder=1)
    ax_ratio.errorbar(xs, ratios, yerr=np.nan_to_num(yerr), color=INK_SECONDARY, marker="o", markersize=6,
                      linewidth=2, capsize=3, elinewidth=1, markeredgecolor=SURFACE, zorder=3)
    style_axes(ax_ratio, var, xs)
    ax_ratio.set_yscale("log")
    span = [v for v in [*lows, *highs, *ratios] if np.isfinite(v) and v > 0]
    lo_lim, hi_lim = min(span + [1]) / 1.3, max(span + [1]) * 1.3
    ax_ratio.set_ylim(lo_lim, hi_lim)
    ax_ratio.set_yticks([t for t in RATIO_TICKS if lo_lim <= t <= hi_lim])
    ax_ratio.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax_ratio.yaxis.set_minor_locator(NullLocator())
    ax_ratio.set_ylabel("D* Lite ÷ A*", color=INK_SECONDARY, fontsize=10)
    ax_ratio.set_title("Ratio, paired by seed (geometric mean, 95% CI)", color=INK, fontsize=10, loc="left")
    ax_ratio.text(0.99, 0.03, "below 1: D* Lite does less", transform=ax_ratio.transAxes,
                  ha="right", va="bottom", fontsize=8, color=INK_MUTED)
    ax_ratio.text(0.99, 0.97, "above 1: A* does less", transform=ax_ratio.transAxes,
                  ha="right", va="top", fontsize=8, color=INK_MUTED)

    n_seeds = wide.groupby(var).size()
    seeds_text = f"{n_seeds.min()}" if n_seeds.min() == n_seeds.max() else f"{n_seeds.min()}-{n_seeds.max()}"
    baseline = ", ".join(f"{k}={v}" for k, v in asdict(BASELINE).items() if k != var)
    x_label = X_LABELS[var]
    fig.suptitle(f"{METRIC_LABELS.get(metric, metric)} vs {x_label[0].lower() + x_label[1:]}",
                 x=0.01, y=0.975, ha="left", color=INK, fontsize=12, fontweight="bold")
    fig.text(0.01, 0.9, f"Others at baseline ({baseline}); {seeds_text} paired seeds per point",
             ha="left", color=INK_MUTED, fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.9))

    path = out_dir / f"sweep_{var}_{metric}.png"
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {path}")

def summary(df, metric):
    """Every run, including failures: success rate, path quality, and the metric per sweep point."""
    tables = []
    for var in SWEEPS:
        rows = sweep_rows(df, var)
        table = rows.groupby([var, "planner"]).agg(
            runs=("success", "size"),
            success_rate=("success", "mean"),
            step_ratio=("step_ratio", "mean"),
            stuck_ticks=("stuck_ticks", "mean"),
            metric_mean=(metric, "mean"),
            metric_median=(metric, "median"),
        ).reset_index().rename(columns={var: "value"})
        table.insert(0, "sweep", var)
        tables.append(table)
    return pd.concat(tables, ignore_index=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", type=Path, default=DEFAULT_OUT, help=f"benchmark CSV (default {DEFAULT_OUT})")
    parser.add_argument("--out", type=Path, default=Path("results"), help="folder for PNGs and summary.csv (default results)")
    parser.add_argument("--metric", default="nodes_per_replan", choices=METRIC_LABELS, help="y-axis metric (default nodes_per_replan)")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    df["success"] = df["success"].astype(bool)

    commits = df["commit"].unique()
    print(f"{len(df)} rows from commit(s): {', '.join(c[:10] for c in commits)}")
    if len(commits) > 1:
        print("warning: rows come from more than one commit")
    if df["dirty"].astype(str).eq("True").any():
        print("warning: some rows were produced with uncommitted changes")

    args.out.mkdir(parents=True, exist_ok=True)
    for var in SWEEPS:
        plot_sweep(df, var, args.metric, args.out)

    table = summary(df, args.metric)
    table_path = args.out / f"summary_{args.metric}.csv"
    table.to_csv(table_path, index=False)
    with pd.option_context("display.width", 140, "display.max_rows", 200, "display.float_format", "{:.3f}".format):
        print(table.to_string(index=False))
    print(f"wrote {table_path}")

if __name__ == "__main__":
    main()
