"""
qubo_speed.py  --  Phase 2a: speed optimization as a QUBO (quantum-inspired).

This is the *proof-of-concept* that wires up the real D-Wave toolchain. We take
the SAME speed-optimization problem that optimizer.py solves with simulated
annealing / grid search, and re-express it as a QUBO -- the exact Ising/binary
form a quantum annealer solves natively -- then solve it classically with
`neal` (D-Wave's simulated-annealing sampler).

If the QUBO answer matches our SA/grid answer, we've shown the quantum-inspired
formulation is correct. The headline use-case (route optimization, where QUBO is
genuinely necessary) is in qubo_route.py.

ENCODING (one-hot discretization)
---------------------------------
* Chop the speed range into K candidate speeds  s_0 .. s_(K-1).
* One binary variable x_i per candidate:  x_i = 1  <=>  "sail at s_i".
* Pre-compute the voyage fuel f_i for each candidate using the trained ML model
  (the model runs OUTSIDE the QUBO -- the QUBO only sees the numbers f_i).
* Objective + constraints, all as one quadratic energy to minimize:

      H  =  sum_i f_i x_i                      (minimize fuel)
          + P * (sum_i x_i - 1)^2              (pick EXACTLY one speed)
          + P * sum_{i infeasible} x_i         (forbid speeds that miss deadline)

  The two penalty terms turn a CONSTRAINED problem into the UNCONSTRAINED form
  QUBO requires. P is chosen large enough that violating a constraint is never
  worth it.

Run:
    py qubo_speed.py
    py qubo_speed.py --distance 600 --deadline 90 --levels 60
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


def build_speed_qubo(pipe, scenario, distance_nm, deadline_hours, n_levels=40):
    """Construct the QUBO. Returns (qubo_dict, speeds, fuels, feasible, info)."""
    spec = config.SHIP_SPECS[scenario["ship_type"]]
    lo, hi = config.PHYSICAL_MIN_SPEED, spec["max_speed"]

    # Candidate speeds and their pre-computed total voyage fuel (from the model).
    speeds = np.linspace(lo, hi, n_levels)
    fuels = np.array([optimizer.voyage_fuel(pipe, scenario, s, distance_nm)
                      for s in speeds])

    deadline_min_speed = distance_nm / deadline_hours
    feasible = speeds >= deadline_min_speed

    # Penalty weight: bigger than any possible fuel swing so constraints dominate.
    penalty = 5.0 * float(fuels.max())

    x = [Binary(f"x_{i}") for i in range(n_levels)]
    H = sum(float(fuels[i]) * x[i] for i in range(n_levels))          # objective
    H += penalty * (sum(x) - 1) ** 2                                  # one-hot
    H += penalty * sum((0.0 if feasible[i] else 1.0) * x[i]           # deadline
                       for i in range(n_levels))

    model = H.compile()
    qubo, offset = model.to_qubo()
    info = {"n_vars": n_levels, "n_qubo_terms": len(qubo),
            "penalty": penalty, "deadline_min_speed": deadline_min_speed}
    return qubo, speeds, fuels, feasible, info


def solve_speed_qubo(qubo, speeds, fuels, num_reads=200, seed=42):
    """Solve the QUBO with neal; decode the one-hot result back to a speed."""
    sampler = neal.SimulatedAnnealingSampler()
    sampleset = sampler.sample_qubo(qubo, num_reads=num_reads, seed=seed)
    best = sampleset.first.sample

    selected = [i for i in range(len(speeds)) if best.get(f"x_{i}", 0) == 1]
    valid_one_hot = len(selected) == 1
    if selected:
        # If (rarely) more than one bit is set, take the cheapest selected.
        i = min(selected, key=lambda j: fuels[j])
    else:
        i = int(np.argmin(fuels))  # fallback; shouldn't happen with good penalty
    return {
        "speed": float(speeds[i]),
        "fuel": float(fuels[i]),
        "n_selected": len(selected),
        "valid_one_hot": valid_one_hot,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Speed optimization via QUBO + neal.")
    p.add_argument("--distance", type=float, default=config.DEFAULT_VOYAGE_NM)
    p.add_argument("--deadline", type=float, default=config.DEFAULT_DEADLINE_HOURS)
    p.add_argument("--levels", type=int, default=40, help="speed discretization")
    args = p.parse_args()

    scenario = dict(config.DEFAULT_SCENARIO)
    pipe = optimizer.load_model()

    # --- QUBO (quantum-inspired) ------------------------------------------ #
    qubo, speeds, fuels, feasible, info = build_speed_qubo(
        pipe, scenario, args.distance, args.deadline, args.levels
    )
    qres = solve_speed_qubo(qubo, speeds, fuels)

    # --- Reference answers from Phase 1 (SA + brute-force grid) ------------ #
    ref = optimizer.optimize_speed(pipe, scenario, args.distance, args.deadline)

    print("Speed optimization: QUBO vs classical baselines")
    print(f"  Voyage: {args.distance:.0f} nm, deadline {args.deadline:.0f} h "
          f"(min speed {info['deadline_min_speed']:.1f} kn)")
    print(f"  QUBO size: {info['n_vars']} binary vars, "
          f"{info['n_qubo_terms']} quadratic terms, penalty {info['penalty']:.0f}")
    print(f"  Speed resolution: {(speeds[1] - speeds[0]):.2f} kn between levels")
    print()
    print(f"  {'Method':<22}{'speed (kn)':>12}{'fuel (t)':>12}")
    print(f"  {'QUBO (neal)':<22}{qres['speed']:>12.2f}{qres['fuel']:>12.2f}")
    print(f"  {'Simulated annealing':<22}{ref['opt_speed']:>12.2f}{ref['opt_fuel']:>12.2f}")
    print(f"  {'Brute-force grid':<22}{ref['grid_speed']:>12.2f}{ref['grid_fuel']:>12.2f}")
    print()
    print(f"  One-hot constraint satisfied: {qres['valid_one_hot']} "
          f"({qres['n_selected']} speed selected)")
    gap = abs(qres["speed"] - ref["grid_speed"])
    print(f"  QUBO vs grid speed gap: {gap:.2f} kn "
          f"(within the {(speeds[1] - speeds[0]):.2f} kn discretization => correct)")

    # --- Plot --------------------------------------------------------------- #
    fig, ax = plt.subplots(figsize=(10, 5.5))

    # Fuel curve
    ax.plot(speeds, fuels, "-", color="#888888", lw=2, label="Voyage fuel curve")

    # Shade infeasible region (too slow for deadline)
    min_spd = info["deadline_min_speed"]
    ax.axvspan(speeds[0], min_spd, color="red", alpha=0.10, label="Too slow (misses deadline)")
    ax.axvline(min_spd, color="red", ls="--", lw=1, alpha=0.6)

    # Mark the three methods
    ax.plot(qres["speed"], qres["fuel"], "D", color="#1f77b4", ms=12, zorder=5,
            label=f"QUBO (neal): {qres['speed']:.1f} kn, {qres['fuel']:.1f} t")
    ax.plot(ref["opt_speed"], ref["opt_fuel"], "s", color="#ff7f0e", ms=11, zorder=5,
            label=f"Simulated annealing: {ref['opt_speed']:.1f} kn, {ref['opt_fuel']:.1f} t")
    ax.plot(ref["grid_speed"], ref["grid_fuel"], "^", color="#2ca02c", ms=11, zorder=5,
            label=f"Grid search: {ref['grid_speed']:.1f} kn, {ref['grid_fuel']:.1f} t")

    # Baseline service speed
    baseline_spd = config.SHIP_SPECS[scenario["ship_type"]]["service_speed"]
    baseline_fuel = optimizer.voyage_fuel(pipe, scenario, baseline_spd, args.distance)
    ax.axvline(baseline_spd, color="crimson", ls=":", lw=1.5, alpha=0.7)
    ax.plot(baseline_spd, baseline_fuel, "x", color="crimson", ms=12, mew=2.5, zorder=5,
            label=f"Baseline ({baseline_spd:.0f} kn): {baseline_fuel:.1f} t")

    ax.set_xlabel("Speed (knots)")
    ax.set_ylabel("Total voyage fuel (tonnes)")
    ax.set_title(f"Speed QUBO: {args.distance:.0f} nm, {args.deadline:.0f} h deadline — "
                 f"{scenario['ship_type'].replace('_', ' ')}")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.OUTPUTS_DIR / f"speed_qubo_{args.distance:.0f}nm_{args.deadline:.0f}h.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"\n  Saved plot -> {out}")


if __name__ == "__main__":
    main()
