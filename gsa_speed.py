"""
gsa_speed.py  --  Phase 2d: Gravitational Search Algorithm on the SPEED problem.

GSA is natively a CONTINUOUS optimiser, so the slow-steaming speed decision is its
natural home (unlike the binary route QUBO, where GSA struggles). This script
pits GSA head-to-head against our Phase 1 simulated annealing and the brute-force
grid, and draws GSA's swarm CONVERGENCE curve (best fuel vs iteration) -- the
gravitational analogue of SA's cooling.

Run:
    py gsa_speed.py
    py gsa_speed.py --distance 600 --deadline 90
"""

from __future__ import annotations

import argparse
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
import gsa
import optimizer


def batched_voyage_fuel(pipe, scenario, speeds, distance_nm):
    """Voyage fuel for an array of speeds in ONE ML predict call (fast)."""
    speeds = np.asarray(speeds, dtype=float).ravel()
    rows = [{**scenario, config.DECISION_VAR: float(s)} for s in speeds]
    X = pd.DataFrame(rows)[config.FEATURE_COLUMNS]
    rate = pipe.predict(X)                            # tonnes/day, vectorised
    time_days = distance_nm / (speeds * 24.0)
    return rate * time_days


def run_case(pipe, scenario, distance, deadline, seed=0):
    min_spd = distance / deadline
    spec = config.SHIP_SPECS[scenario["ship_type"]]
    lo = max(config.PHYSICAL_MIN_SPEED, min_spd)
    hi = spec["max_speed"]

    # Vectorised objective with a deadline penalty (GSA sees one array per step).
    def obj_batch(Xmat):
        s = np.asarray(Xmat, dtype=float).ravel()
        fuel = batched_voyage_fuel(pipe, scenario, s, distance)
        fuel = fuel + 1000.0 * np.maximum(0.0, min_spd - s)   # deadline penalty
        return fuel

    t = time.perf_counter()
    bx, bf, hist = gsa.gsa_minimize(obj_batch, [(lo, hi)], n_agents=20,
                                    iters=100, seed=seed, vectorized=True)
    gsa_time = time.perf_counter() - t

    ref = optimizer.optimize_speed(pipe, scenario, distance, deadline, seed=seed)
    return {
        "min_spd": min_spd, "lo": lo, "hi": hi,
        "gsa_speed": float(bx[0]), "gsa_fuel": float(bf), "gsa_time": gsa_time,
        "gsa_hist": hist,
        "sa_speed": ref["opt_speed"], "sa_fuel": ref["opt_fuel"],
        "grid_speed": ref["grid_speed"], "grid_fuel": ref["grid_fuel"],
        "baseline_speed": ref["baseline_speed"], "baseline_fuel": ref["baseline_fuel"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="GSA vs SA vs grid on cruise speed.")
    p.add_argument("--distance", type=float, default=config.DEFAULT_VOYAGE_NM)
    p.add_argument("--deadline", type=float, default=config.DEFAULT_DEADLINE_HOURS)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    scenario = dict(config.DEFAULT_SCENARIO)
    pipe = optimizer.load_model()
    r = run_case(pipe, scenario, args.distance, args.deadline, args.seed)

    print("Speed optimization: Gravitational Search Algorithm vs classical baselines")
    print(f"  Voyage {args.distance:.0f} nm, deadline {args.deadline:.0f} h "
          f"(min feasible speed {r['min_spd']:.1f} kn)\n")
    print(f"  {'Method':<26}{'speed (kn)':>11}{'fuel (t)':>10}")
    print(f"  {'GSA (gravitational)':<26}{r['gsa_speed']:>11.2f}{r['gsa_fuel']:>10.2f}")
    print(f"  {'Simulated annealing':<26}{r['sa_speed']:>11.2f}{r['sa_fuel']:>10.2f}")
    print(f"  {'Brute-force grid':<26}{r['grid_speed']:>11.2f}{r['grid_fuel']:>10.2f}")
    print(f"  {'Baseline (service)':<26}{r['baseline_speed']:>11.2f}{r['baseline_fuel']:>10.2f}")
    print()
    gap = abs(r["gsa_speed"] - r["grid_speed"])
    print(f"  GSA vs grid speed gap: {gap:.3f} kn  ->  "
          f"{'MATCH (GSA found the optimum)' if gap < 0.3 else 'close'}")
    print(f"  GSA wall-clock: {r['gsa_time']:.2f} s (20 agents x 100 iterations)")

    # --- Plot: convergence curve + the U-curve with each method's pick ------ #
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Left: GSA convergence -- swarm MEAN collapses toward the BEST under gravity
    ax1.plot(r["gsa_hist"]["mean"], color="#A78BFA", lw=2,
             label="Swarm mean fuel (all agents)")
    ax1.plot(r["gsa_hist"]["best"], color="#7C3AED", lw=2.5,
             label="Best agent so far")
    ax1.axhline(r["grid_fuel"], color="#16A34A", ls="--", lw=1.5,
                label=f"Grid optimum ({r['grid_fuel']:.1f} t)")
    ax1.set_xlabel("GSA iteration")
    ax1.set_ylabel("Voyage fuel (t)")
    ax1.set_title("GSA convergence: the swarm settles under 'gravity'")
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Right: fuel-vs-speed U-curve with each method's chosen speed
    speeds = np.linspace(r["lo"], r["hi"], 120)
    fuels = batched_voyage_fuel(pipe, scenario, speeds, args.distance)
    ax2.plot(speeds, fuels, "-", color="#bbbbbb", lw=1.5, label="Voyage fuel curve")
    ax2.axvspan(config.PHYSICAL_MIN_SPEED, r["min_spd"], color="red", alpha=0.08,
                label="Too slow (misses deadline)")
    ax2.plot(r["gsa_speed"], r["gsa_fuel"], "D", color="#7C3AED", ms=13, mec="black",
             label=f"GSA: {r['gsa_speed']:.1f} kn", zorder=5)
    ax2.plot(r["sa_speed"], r["sa_fuel"], "s", color="#ff7f0e", ms=11, mec="black",
             label=f"SA: {r['sa_speed']:.1f} kn", zorder=4)
    ax2.plot(r["grid_speed"], r["grid_fuel"], "^", color="#16A34A", ms=11, mec="black",
             label=f"Grid: {r['grid_speed']:.1f} kn", zorder=4)
    ax2.set_xlabel("Speed (knots)")
    ax2.set_ylabel("Total voyage fuel (t)")
    ax2.set_title("All three optimizers land on the economic speed")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.3)

    fig.suptitle(f"Gravitational Search Algorithm on cruise speed "
                 f"({args.distance:.0f} nm, {args.deadline:.0f} h deadline)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.OUTPUTS_DIR / f"gsa_speed_{args.distance:.0f}nm_{args.deadline:.0f}h.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"\n  Saved plot -> {out}")


if __name__ == "__main__":
    main()
