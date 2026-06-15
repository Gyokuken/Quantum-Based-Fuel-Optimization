"""
qubo_route.py  --  Phase 2b: weather routing as a QUBO (the real headline).

THIS is where QUBO earns its keep. A ship must cross an ocean region from a start
port to a destination port. The region has weather (one or more storms with high
waves). The ship should pick the MINIMUM-FUEL PATH -- which may mean detouring
around storms even though it is longer.

Choosing among the combinatorially many paths is exactly the kind of problem
quantum annealers target. We formulate it as a QUBO and solve with `neal`; the
SAME QUBO could be sent to real D-Wave quantum hardware unchanged.

GRID + ENCODING (a monotone west->east path)
--------------------------------------------
* The region is a grid: n_cols columns (west->east stages) x n_rows rows
  (north-south positions). The ship occupies exactly ONE row per column and
  advances one column at a time (so the path always makes progress to the east).
* Binary variable per cell:  x[c,r] = 1  <=>  "the ship is in row r at column c".
* Each cell has a fuel cost computed by our PHASE 1 ML MODEL, using that cell's
  wave height + wind.

ENERGY  H  = sum_{c,r} cost[c,r] x[c,r]                         (fuel)
           + surcharge for diagonal (row-changing) moves        (extra distance)
           + P * sum_c (sum_r x[c,r] - 1)^2                      (one row per column)
           + P * (force start row at col 0, end row at last col)
           + P * sum  x[c,r] x[c+1,r']  for |r-r'| >= 2          (no row teleporting)

We validate the QUBO answer against an EXACT dynamic-programming solver (the
monotone grid path is a shortest-path problem), which scales to large grids.

Run:
    py qubo_route.py
    py qubo_route.py --rows 7 --cols 15 --storms 3 --seed 1 --cruise 14
    py qubo_route.py --rows 9 --cols 19 --storms 4 --ship-type Fast_Patrol
"""

from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import neal
import numpy as np
from pyqubo import Binary

import config
import optimizer


# --------------------------------------------------------------------------- #
# Weather field + per-cell fuel cost (from the Phase 1 ML model)               #
# --------------------------------------------------------------------------- #
def build_weather(n_rows, n_cols, storms=None):
    """Wave-height field (metres). `storms` is a list of tuples
    (row_centre, col_centre, amplitude, row_spread, col_spread).
    If None, a single storm sits in the centre (back-compatible default)."""
    if storms is None:
        storms = [((n_rows - 1) / 2.0, (n_cols - 1) / 2.0, 6.0, 1.0, 1.3)]
    rows = np.arange(n_rows)[:, None]
    cols = np.arange(n_cols)[None, :]
    waves = np.full((n_rows, n_cols), 1.0)            # calm-sea baseline
    for rc, cc, amp, sr, sc in storms:
        waves = waves + amp * np.exp(
            -(((rows - rc) ** 2) / (2 * sr ** 2)
              + ((cols - cc) ** 2) / (2 * sc ** 2))
        )
    return np.clip(waves, 0, 8)


def random_storms(n_rows, n_cols, n, seed=0):
    """Scatter `n` random storms across the interior of the grid."""
    rng = np.random.default_rng(seed)
    storms = []
    for _ in range(n):
        rc = rng.uniform(0, n_rows - 1)
        cc = rng.uniform(n_cols * 0.15, n_cols * 0.85)   # keep off the ports
        amp = rng.uniform(4.0, 7.0)
        sr = rng.uniform(0.8, 1.6)
        sc = rng.uniform(0.8, 2.0)
        storms.append((rc, cc, amp, sr, sc))
    return storms


def base_scenario_for(ship_type):
    """A base ship scenario for a class, using that class's typical specs."""
    spec = config.SHIP_SPECS[ship_type]
    scn = dict(config.DEFAULT_SCENARIO)
    scn["ship_type"] = ship_type
    scn["displacement_tonnes"] = float(spec["disp"][0])
    scn["engine_power_kw"] = float(spec["power"][0])
    scn["hull_coefficient"] = float(spec["hull"][0])
    scn["fuel_type"] = max(spec["fuel"], key=spec["fuel"].get)   # most likely
    return scn


def cell_costs(pipe, base_scenario, waves, total_nm, cruise_kn):
    """Fuel (tonnes) to traverse each cell's leg, predicted by the ML model."""
    n_rows, n_cols = waves.shape
    leg_nm = total_nm / n_cols
    time_days = leg_nm / (cruise_kn * 24.0)
    cost = np.zeros_like(waves)
    for r in range(n_rows):
        for c in range(n_cols):
            scenario = {**base_scenario,
                        "wave_height_m": float(waves[r, c]),
                        # wind correlates with sea state (as in training data)
                        "wind_speed_kn": float(5 + 6 * waves[r, c])}
            rate = optimizer.predict_rate(pipe, scenario, cruise_kn)  # t/day
            cost[r, c] = rate * time_days
    return cost


# --------------------------------------------------------------------------- #
# QUBO construction + solve                                                    #
# --------------------------------------------------------------------------- #
def build_route_qubo(cost, start_row, end_row, diag_surcharge=0.10):
    """Build the routing QUBO. Returns (qubo_dict, info)."""
    n_rows, n_cols = cost.shape
    x = {(c, r): Binary(f"x_{c}_{r}")
         for c in range(n_cols) for r in range(n_rows)}
    # Penalty just needs to exceed the largest single-cell fuel cost (so breaking
    # a constraint is never worth it) -- scaling by max (not sum) keeps the energy
    # range tight, which helps neal optimise the objective finely on big grids.
    P = 10.0 * float(cost.max())

    H = 0
    # Objective: fuel cost of every occupied cell.
    for c in range(n_cols):
        for r in range(n_rows):
            H += float(cost[r, c]) * x[(c, r)]

    # Diagonal moves cover extra distance -> small surcharge (discourage zigzag).
    for c in range(n_cols - 1):
        for r in range(n_rows):
            for r2 in (r - 1, r + 1):
                if 0 <= r2 < n_rows:
                    H += diag_surcharge * float(cost[r2, c + 1]) * x[(c, r)] * x[(c + 1, r2)]

    # Constraint 1: exactly one row per column.
    for c in range(n_cols):
        H += P * (sum(x[(c, r)] for r in range(n_rows)) - 1) ** 2

    # Constraint 2: fixed start row (col 0) and end row (last col).
    for r in range(n_rows):
        if r != start_row:
            H += P * x[(0, r)]
        if r != end_row:
            H += P * x[(n_cols - 1, r)]

    # Constraint 3: no teleporting -- consecutive rows differ by at most 1.
    for c in range(n_cols - 1):
        for r in range(n_rows):
            for r2 in range(n_rows):
                if abs(r - r2) >= 2:
                    H += P * x[(c, r)] * x[(c + 1, r2)]

    model = H.compile()
    qubo, offset = model.to_qubo()
    info = {"n_vars": n_rows * n_cols, "n_qubo_terms": len(qubo), "penalty": P}
    return qubo, info


def decode_route(sample, n_rows, n_cols):
    """Turn a QUBO sample into a path (one row per column), or None if invalid."""
    path = []
    for c in range(n_cols):
        on = [r for r in range(n_rows) if sample.get(f"x_{c}_{r}", 0) == 1]
        if len(on) != 1:
            return None
        path.append(on[0])
    if any(abs(path[c] - path[c + 1]) >= 2 for c in range(n_cols - 1)):
        return None
    return path


def path_fuel(path, cost, diag_surcharge=0.10):
    """Total fuel for a path = sum of cell costs + diagonal surcharges."""
    total = sum(cost[path[c], c] for c in range(len(path)))
    for c in range(len(path) - 1):
        if path[c] != path[c + 1]:
            total += diag_surcharge * cost[path[c + 1], c + 1]
    return float(total)


# --------------------------------------------------------------------------- #
# Exact validation via dynamic programming (shortest path on the grid)         #
# --------------------------------------------------------------------------- #
def exact_best_dp(cost, start_row, end_row, diag_surcharge=0.10):
    """Exact minimum-fuel monotone path via DP. O(rows*cols) -- scales to any grid."""
    n_rows, n_cols = cost.shape
    INF = float("inf")
    dp = [[INF] * n_rows for _ in range(n_cols)]
    back = [[-1] * n_rows for _ in range(n_cols)]
    dp[0][start_row] = float(cost[start_row, 0])

    for c in range(1, n_cols):
        for r in range(n_rows):
            best, bp = INF, -1
            for rp in (r - 1, r, r + 1):
                if 0 <= rp < n_rows and dp[c - 1][rp] < INF:
                    trans = diag_surcharge * float(cost[r, c]) if rp != r else 0.0
                    val = dp[c - 1][rp] + float(cost[r, c]) + trans
                    if val < best:
                        best, bp = val, rp
            dp[c][r], back[c][r] = best, bp

    total = dp[n_cols - 1][end_row]
    if total == INF:
        return None, INF
    path, r = [end_row], end_row
    for c in range(n_cols - 1, 0, -1):
        r = back[c][r]
        path.append(r)
    path.reverse()
    return path, float(total)


# --------------------------------------------------------------------------- #
# Plot                                                                         #
# --------------------------------------------------------------------------- #
def plot_routes(waves, naive_path, qubo_path, start_row, path_label, out):
    n_rows, n_cols = waves.shape
    plt.figure(figsize=(min(14, 1.0 * n_cols + 2), min(8, 0.8 * n_rows + 2)))
    im = plt.imshow(waves, origin="lower", aspect="auto", cmap="YlOrRd",
                    extent=[-0.5, n_cols - 0.5, -0.5, n_rows - 0.5], vmin=1, vmax=8)
    plt.colorbar(im, label="Wave height (m)")

    cols = list(range(n_cols))
    plt.plot(cols, naive_path, "o--", color="black", lw=2,
             label="Naive straight route")
    plt.plot(cols, qubo_path, "o-", color="#1f77b4", lw=2.5, label=path_label)
    plt.scatter([0, n_cols - 1], [start_row, qubo_path[-1]], s=220,
                marker="*", color="lime", edgecolor="black", zorder=5,
                label="Start / End port")

    plt.title("Weather routing: QUBO finds the minimum-fuel path around the storms")
    plt.xlabel("Stage (west -> east)")
    plt.ylabel("Track (south -> north)")
    plt.legend(loc="upper right")
    plt.tight_layout()
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=120)
    plt.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Weather routing via QUBO + neal.")
    p.add_argument("--rows", type=int, default=5)
    p.add_argument("--cols", type=int, default=7)
    p.add_argument("--cruise", type=float, default=16.0, help="cruise speed (kn)")
    p.add_argument("--distance", type=float, default=config.DEFAULT_VOYAGE_NM)
    p.add_argument("--storms", type=int, default=0,
                   help="number of random storms (0 = one centred storm)")
    p.add_argument("--seed", type=int, default=0, help="random storm seed")
    p.add_argument("--ship-type", default=config.DEFAULT_SCENARIO["ship_type"],
                   choices=list(config.SHIP_SPECS.keys()))
    p.add_argument("--num-reads", type=int, default=None,
                   help="neal samples (default scales with grid size)")
    p.add_argument("--sweeps", type=int, default=1000,
                   help="neal annealing sweeps per read (more = better quality)")
    p.add_argument("--start-row", type=int, default=None,
                   help="start port latitude band (default: middle)")
    p.add_argument("--end-row", type=int, default=None,
                   help="end port latitude band (default: middle)")
    args = p.parse_args()

    n_rows, n_cols = args.rows, args.cols
    start_row = args.start_row if args.start_row is not None else n_rows // 2
    end_row = args.end_row if args.end_row is not None else n_rows // 2
    base = base_scenario_for(args.ship_type)
    pipe = optimizer.load_model()

    if args.storms > 0:
        storms = random_storms(n_rows, n_cols, args.storms, args.seed)
    else:
        storms = None
    waves = build_weather(n_rows, n_cols, storms)
    cost = cell_costs(pipe, base, waves, args.distance, args.cruise)

    # --- QUBO (quantum-inspired) ------------------------------------------ #
    qubo, info = build_route_qubo(cost, start_row, end_row)
    num_reads = args.num_reads if args.num_reads else max(500, 150 * n_cols)
    sampler = neal.SimulatedAnnealingSampler()
    sampleset = sampler.sample_qubo(qubo, num_reads=num_reads,
                                    num_sweeps=args.sweeps, seed=42)
    qubo_path = decode_route(sampleset.first.sample, n_rows, n_cols)

    # --- Validation (exact DP) + naive baseline --------------------------- #
    dp_path, dp_fuel = exact_best_dp(cost, start_row, end_row)
    # Naive baseline: the straight rhumb line from start to end (ignores weather).
    naive_path = [int(round(start_row + (end_row - start_row) * c / (n_cols - 1)))
                  for c in range(n_cols)]
    naive_fuel = path_fuel(naive_path, cost)

    print("Weather routing: QUBO vs exact DP vs naive straight line")
    print(f"  Ship: {args.ship_type}  |  cruise {args.cruise:.0f} kn  |  "
          f"{args.distance:.0f} nm  |  storms: "
          f"{args.storms if args.storms else '1 (centred)'} (seed {args.seed})")
    print(f"  Grid: {n_rows} rows x {n_cols} cols  ({info['n_vars']} binary vars, "
          f"{info['n_qubo_terms']} QUBO terms, {num_reads} neal reads)")
    print(f"  Sea state: waves {waves.min():.1f}-{waves.max():.1f} m\n")

    if qubo_path is None:
        print("  QUBO returned an INVALID path (penalty/reads too low).")
        qubo_fuel, qubo_path, label = float("nan"), naive_path, "QUBO (invalid)"
    else:
        qubo_fuel, label = path_fuel(qubo_path, cost), "QUBO route (neal)"

    print(f"  {'Method':<24}{'fuel (t)':>10}   path (rows by stage)")
    print(f"  {'Naive straight':<24}{naive_fuel:>10.2f}   {naive_path}")
    print(f"  {'QUBO (neal)':<24}{qubo_fuel:>10.2f}   {qubo_path}")
    print(f"  {'Exact optimum (DP)':<24}{dp_fuel:>10.2f}   {dp_path}")
    print()
    saving = (naive_fuel - qubo_fuel) / naive_fuel * 100
    opt_gap = (qubo_fuel - dp_fuel) / dp_fuel * 100 if dp_fuel else float("nan")
    print(f"  Fuel saved by routing : {saving:.1f}%  "
          f"({naive_fuel - qubo_fuel:.2f} t per leg)")
    if abs(qubo_fuel - dp_fuel) < 1e-6:
        verdict = "YES (found the exact optimum)"
    elif qubo_path == dp_path:
        verdict = "YES (identical path)"
    else:
        verdict = f"within {opt_gap:.2f}% of exact (neal is heuristic)"
    print(f"  QUBO optimal? {verdict}")

    out = config.OUTPUTS_DIR / (f"route_qubo_{n_rows}x{n_cols}_s{args.storms}"
                                f"_seed{args.seed}_r{start_row}-{end_row}.png")
    plot_routes(waves, naive_path, qubo_path, start_row, label, out)
    print(f"\n  Saved plot -> {out}")


if __name__ == "__main__":
    main()
