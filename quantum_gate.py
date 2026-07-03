"""
quantum_gate.py  --  Phase 2c: the SAME QUBO on GATE-MODEL quantum algorithms,
                     WITH a head-to-head comparison (paths/speeds + metrics + plot).

Phase 2a/2b solved our QUBOs with neal (classical annealing) -- the form a
D-Wave *annealer* uses. This file proves the other half of the story: the very
same QUBO also runs on **gate-model** quantum computers (IBM-style) via the two
standard variational algorithms:

  * QAOA  -- Quantum Approximate Optimization Algorithm (purpose-built for QUBO)
  * VQE   -- Variational Quantum Eigensolver (general ground-state finder)

Both convert the QUBO -> an Ising Hamiltonian (s = 2x - 1) and find its lowest-
energy state with a parameterised quantum circuit + a classical optimiser in the
loop. We run on Qiskit's local statevector simulator (FREE, offline). The same
code runs on real IBM hardware by swapping the sampler for a Runtime backend.

WHAT THIS SCRIPT SHOWS
----------------------
  * the speed / path each solver chose (drawn on one comparison plot)
  * metrics:  fuel, optimality gap vs exact, feasibility, SUCCESS RATE over
    repeated runs (QAOA/VQE are stochastic), and wall-clock time

  ** Gate-model on a simulator uses ONE QUBIT PER BINARY VARIABLE, cost ~ 2^qubits.
     Keep problems SMALL (<= ~16 qubits): few speed levels or a tiny route grid. **

Run:
    py quantum_gate.py --problem speed --levels 8 --trials 5
    py quantum_gate.py --problem route --rows 3 --cols 4 --storms 1 --seed 2 --trials 5
"""

from __future__ import annotations

import argparse
import time
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from qiskit.circuit.library import TwoLocal
from qiskit.primitives import StatevectorSampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_algorithms import QAOA, SamplingVQE, NumPyMinimumEigensolver
from qiskit_algorithms.optimizers import COBYLA
from qiskit_algorithms.utils import algorithm_globals
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

import backends
import config
import gsa
import optimizer
import qubo_route
import qubo_speed


# --------------------------------------------------------------------------- #
# QUBO dict  ->  Qiskit QuadraticProgram                                       #
# --------------------------------------------------------------------------- #
def qubo_to_qp(qubo, name="fuel_qubo"):
    """Convert a pyqubo QUBO dict {(vi,vj): coef} into a Qiskit QuadraticProgram.
    Diagonal (vi==vj) -> linear (x^2 = x for binaries); off-diagonal -> quadratic."""
    varnames = sorted({v for k in qubo for v in k})
    qp = QuadraticProgram(name)
    for v in varnames:
        qp.binary_var(v)
    linear, quadratic = {}, {}
    for (i, j), c in qubo.items():
        if i == j:
            linear[i] = linear.get(i, 0.0) + c
        else:
            quadratic[(i, j)] = quadratic.get((i, j), 0.0) + c
    qp.minimize(linear=linear, quadratic=quadratic)
    return qp


# --------------------------------------------------------------------------- #
# Solvers (each returns a {varname: 0/1} dict so decode() is uniform)          #
# --------------------------------------------------------------------------- #
def _pm_sampler(seed=None):
    # Seeding the sampler (shot RNG) + algorithm_globals (COBYLA start point)
    # makes each gate-model run fully reproducible, independent of call order.
    return (generate_preset_pass_manager(optimization_level=1, backend=AerSimulator()),
            StatevectorSampler(seed=seed))


def run_exact(qp):
    res = MinimumEigenOptimizer(NumPyMinimumEigensolver()).solve(qp)
    return res.variables_dict


def run_neal(qubo, seed=42):
    sampler, _, _ = backends.make_sampler("neal")
    ss = backends.sample_qubo(sampler, "neal", qubo, num_reads=200, seed=seed)
    return {k: int(v) for k, v in dict(ss.first.sample).items()}


def run_gsa(qubo, seed=0):
    """Binary Gravitational Search Algorithm on the QUBO (classical metaheuristic)."""
    sample, _e, _h = gsa.bgsa_qubo(qubo, n_agents=80, iters=200, seed=seed)
    return sample


def run_qaoa(qp, reps, maxiter, seed=42):
    algorithm_globals.random_seed = seed
    pm, sampler = _pm_sampler(seed)
    qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=maxiter),
                reps=reps, transpiler=pm)
    return MinimumEigenOptimizer(qaoa).solve(qp).variables_dict


def run_vqe(qp, n_qubits, reps, maxiter, seed=42):
    algorithm_globals.random_seed = seed
    pm, sampler = _pm_sampler(seed)
    ansatz = pm.run(TwoLocal(n_qubits, "ry", "cz", reps=reps, entanglement="linear"))
    vqe = SamplingVQE(sampler=sampler, ansatz=ansatz, optimizer=COBYLA(maxiter=maxiter))
    return MinimumEigenOptimizer(vqe).solve(qp).variables_dict


# --------------------------------------------------------------------------- #
# Evaluate a solver over `trials` runs -> metrics record                       #
# --------------------------------------------------------------------------- #
def evaluate(label, run_once, decode, exact_fuel, trials):
    """Run a solver `trials` times; collect feasibility, quality, success, time."""
    feasible = 0
    successes = 0          # matched the exact optimum
    fuels = []
    best_fuel = float("inf")
    best_sol = None
    best_str = "-"
    t0 = time.perf_counter()
    for i in range(trials):
        sol, fuel, s = decode(run_once(i))
        if sol is not None and fuel == fuel:          # feasible & not NaN
            feasible += 1
            fuels.append(fuel)
            if exact_fuel == exact_fuel and abs(fuel - exact_fuel) < 1e-6:
                successes += 1
            if fuel < best_fuel:
                best_fuel, best_sol, best_str = fuel, sol, s
    avg_time = (time.perf_counter() - t0) / trials

    gap = (float("nan") if best_fuel == float("inf") or exact_fuel != exact_fuel
           else (best_fuel - exact_fuel) / exact_fuel * 100)
    return {
        "label": label,
        "trials": trials,
        "feasible": feasible,
        "successes": successes,
        "best_fuel": (best_fuel if best_fuel != float("inf") else float("nan")),
        "mean_fuel": (float(np.mean(fuels)) if fuels else float("nan")),
        "gap": gap,
        "avg_time": avg_time,
        "best_sol": best_sol,
        "best_str": best_str,
    }


# --------------------------------------------------------------------------- #
# Problem builders                                                             #
# --------------------------------------------------------------------------- #
def build_speed_problem(args):
    scenario = dict(config.DEFAULT_SCENARIO)
    pipe = optimizer.load_model()
    qubo, speeds, fuels, feasible, info = qubo_speed.build_speed_qubo(
        pipe, scenario, args.distance, args.deadline, args.levels)

    def decode(var_dict):
        sel = [i for i in range(len(speeds)) if round(var_dict.get(f"x_{i}", 0)) == 1]
        if len(sel) != 1:
            return None, float("nan"), f"invalid one-hot ({len(sel)} set)"
        i = sel[0]
        return float(speeds[i]), float(fuels[i]), f"{speeds[i]:.2f} kn"

    ctx = {"speeds": speeds, "fuels": fuels,
           "min_speed": info["deadline_min_speed"]}
    meta = {"kind": "speed", "n_qubits": args.levels,
            "title": f"SPEED - {args.levels} levels, {args.distance:.0f} nm, "
                     f"{args.deadline:.0f} h deadline", "unit": "fuel (t)"}
    return qubo, decode, meta, ctx


def build_route_problem(args):
    base = qubo_route.base_scenario_for(args.ship_type)
    pipe = optimizer.load_model()
    storms = (qubo_route.random_storms(args.rows, args.cols, args.storms, args.seed)
              if args.storms > 0 else None)
    waves = qubo_route.build_weather(args.rows, args.cols, storms)
    cost = qubo_route.cell_costs(pipe, base, waves, args.distance, args.cruise)
    start_row = end_row = args.rows // 2
    qubo, info = qubo_route.build_route_qubo(cost, start_row, end_row)

    def decode(var_dict):
        sample = {k: int(round(v)) for k, v in var_dict.items()}
        path = qubo_route.decode_route(sample, args.rows, args.cols)
        if path is None:
            return None, float("nan"), "invalid path"
        return path, qubo_route.path_fuel(path, cost), str(path)

    naive = [int(round(start_row + (end_row - start_row) * c / (args.cols - 1)))
             for c in range(args.cols)]
    ctx = {"cost": cost, "waves": waves, "start_row": start_row,
           "end_row": end_row, "naive": naive,
           "naive_fuel": qubo_route.path_fuel(naive, cost)}
    meta = {"kind": "route", "n_qubits": args.rows * args.cols,
            "title": f"ROUTE - {args.rows}x{args.cols} grid, "
                     f"{args.storms or 1} storm(s)", "unit": "fuel (t)"}
    return qubo, decode, meta, ctx


# --------------------------------------------------------------------------- #
# Comparison plots                                                            #
# --------------------------------------------------------------------------- #
STYLE = {                       # consistent colours/markers per solver
    "Exact":  ("#16A34A", "*", 22),
    "neal":   ("#1f77b4", "o", 12),
    "GSA":    ("#7C3AED", "v", 11),
    "QAOA":   ("#E8772E", "D", 11),
    "VQE":    ("#D62728", "s", 10),
}


def _style_for(label):
    for key, v in STYLE.items():
        if label.startswith(key):
            return v
    return ("#666666", "x", 10)


def plot_speed_comparison(ctx, records, meta, out):
    speeds, fuels = ctx["speeds"], ctx["fuels"]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(speeds, fuels, "-", color="#bbbbbb", lw=1.5, zorder=1,
            label="Candidate speeds (QUBO levels)")
    ax.scatter(speeds, fuels, color="#dddddd", s=30, zorder=1)
    ax.axvspan(speeds[0], ctx["min_speed"], color="red", alpha=0.08,
               label="Too slow (misses deadline)")

    for r in records:
        if r["best_sol"] is None:
            continue
        color, marker, size = _style_for(r["label"])
        ax.plot(r["best_sol"], r["best_fuel"], marker=marker, color=color,
                ms=size, mec="black", mew=0.8, ls="none", zorder=5,
                label=f"{r['label']}: {r['best_str']}, {r['best_fuel']:.1f} t")

    ax.set_xlabel("Speed (knots)")
    ax.set_ylabel("Total voyage fuel (tonnes)")
    ax.set_title(f"Solver comparison — {meta['title']}")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def plot_route_comparison(ctx, records, meta, out):
    waves = ctx["waves"]
    n_rows, n_cols = waves.shape
    cols = list(range(n_cols))
    fig, ax = plt.subplots(figsize=(max(7, 1.1 * n_cols), max(4.5, 1.0 * n_rows)))
    im = ax.imshow(waves, origin="lower", aspect="auto", cmap="YlOrRd",
                   extent=[-0.5, n_cols - 0.5, -0.5, n_rows - 0.5], vmin=1, vmax=8)
    fig.colorbar(im, ax=ax, label="Wave height (m)")

    # naive reference
    ax.plot(cols, ctx["naive"], "--", color="black", lw=1.5, alpha=0.7,
            label=f"Naive straight ({ctx['naive_fuel']:.1f} t)")

    # each solver's path, with a tiny vertical offset so overlaps stay visible
    offset = -0.12
    for r in records:
        if r["best_sol"] is None:
            continue
        color, marker, _ = _style_for(r["label"])
        gap_txt = ("" if r["label"].startswith("Exact")
                   else f", +{r['gap']:.0f}%" if r["gap"] == r["gap"] and r["gap"] > 0.05
                   else ", optimal")
        ax.plot(cols, [p + offset for p in r["best_sol"]], marker=marker,
                color=color, lw=2.2, ms=8, mec="black", mew=0.5, alpha=0.95,
                label=f"{r['label']} ({r['best_fuel']:.1f} t{gap_txt})")
        offset += 0.08

    ax.scatter([0, n_cols - 1], [ctx["start_row"], ctx["end_row"]], s=240,
               marker="*", color="lime", edgecolor="black", zorder=6,
               label="Start / End port")
    ax.set_xlabel("Stage (west → east)")
    ax.set_ylabel("Track (south → north)")
    ax.set_title(f"Solver comparison — {meta['title']}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12),
              ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> None:
    p = argparse.ArgumentParser(
        description="Compare annealing (neal) vs gate-model (QAOA/VQE) on one QUBO.")
    p.add_argument("--problem", choices=["speed", "route"], default="speed")
    p.add_argument("--trials", type=int, default=5,
                   help="repeat runs to measure success rate (QAOA/VQE are stochastic)")
    # speed
    p.add_argument("--levels", type=int, default=8)
    p.add_argument("--distance", type=float, default=config.DEFAULT_VOYAGE_NM)
    p.add_argument("--deadline", type=float, default=config.DEFAULT_DEADLINE_HOURS)
    # route
    p.add_argument("--rows", type=int, default=3)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--storms", type=int, default=0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--cruise", type=float, default=16.0)
    p.add_argument("--ship-type", default=config.DEFAULT_SCENARIO["ship_type"],
                   choices=list(config.SHIP_SPECS.keys()))
    # effort
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--maxiter", type=int, default=200)
    p.add_argument("--qseed", type=int, default=42,
                   help="seed for QAOA/VQE reproducibility (deterministic runs)")
    args = p.parse_args()

    # Make the gate-model runs reproducible so a divergence is stable for slides.
    algorithm_globals.random_seed = args.qseed

    if args.problem == "speed":
        qubo, decode, meta, ctx = build_speed_problem(args)
    else:
        qubo, decode, meta, ctx = build_route_problem(args)

    n = meta["n_qubits"]
    n_vars = len({v for k in qubo for v in k})
    print(f"Solver comparison  --  {meta['title']}")
    print(f"  QUBO: {n_vars} variables => {n} qubits on the simulator "
          f"({2**n:,} amplitudes)   |   {args.trials} trial(s) each")
    if n > 16:
        print(f"  WARNING: {n} qubits is large for a statevector simulator "
              f"-- slow / memory-heavy.")
    print()

    qp = qubo_to_qp(qubo)

    # Exact reference first (so we can score gaps + success) ----------------- #
    exact_rec = evaluate("Exact (NumPy)", lambda i: run_exact(qp), decode,
                         float("nan"), trials=1)
    exact_fuel = exact_rec["best_fuel"]
    exact_rec["gap"] = 0.0
    exact_rec["successes"] = exact_rec["trials"] = 1

    # Each trial gets its own seed (qseed + i) so multi-trial stats vary and a
    # single trial (i=0) is exactly reproducible at qseed.
    records = [exact_rec]
    records.append(evaluate("neal (anneal)", lambda i: run_neal(qubo, seed=42 + i),
                            decode, exact_fuel, args.trials))
    records.append(evaluate("GSA (gravity)", lambda i: run_gsa(qubo, seed=args.qseed + i),
                            decode, exact_fuel, args.trials))
    records.append(evaluate(
        "QAOA", lambda i: run_qaoa(qp, args.reps, args.maxiter, seed=args.qseed + i),
        decode, exact_fuel, args.trials))
    records.append(evaluate(
        "VQE", lambda i: run_vqe(qp, n, max(1, args.reps - 1), args.maxiter + 100,
                                 seed=args.qseed + i),
        decode, exact_fuel, args.trials))

    # --- Metrics table ----------------------------------------------------- #
    print("  COMPARISON METRICS")
    print(f"  {'Method':<16}{'best fuel':>10}{'gap %':>8}{'feasible':>10}"
          f"{'success':>9}{'time/run':>10}   best solution")
    print("  " + "-" * 92)
    for r in records:
        fuel_s = f"{r['best_fuel']:.2f}" if r["best_fuel"] == r["best_fuel"] else "n/a"
        gap_s = "-" if r["label"].startswith("Exact") else (
            f"{r['gap']:+.1f}" if r["gap"] == r["gap"] else "n/a")
        feas_s = f"{r['feasible']}/{r['trials']}"
        succ_s = f"{r['successes']}/{r['trials']}"
        print(f"  {r['label']:<16}{fuel_s:>10}{gap_s:>8}{feas_s:>10}"
              f"{succ_s:>9}{r['avg_time']:>9.2f}s   {r['best_str']}")
    print()
    print("  Legend: gap % = best fuel vs exact optimum | feasible = valid "
          "solutions / trials |\n          success = runs that hit the exact "
          "optimum / trials")

    # --- Comparison plot --------------------------------------------------- #
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"_q{args.qseed}" + ("_single" if args.trials == 1 else f"_t{args.trials}")
    if args.trials == 1:
        meta["title"] += f"  (single reproducible run, qseed={args.qseed})"
    if meta["kind"] == "speed":
        out = config.OUTPUTS_DIR / f"compare_speed_L{args.levels}{tag}.png"
        plot_speed_comparison(ctx, records, meta, out)
    else:
        out = config.OUTPUTS_DIR / (f"compare_route_{args.rows}x{args.cols}"
                                    f"_s{args.storms}_seed{args.seed}{tag}.png")
        plot_route_comparison(ctx, records, meta, out)
    print(f"\n  Saved comparison plot -> {out}")
    print("\n  Takeaway: same QUBO, three solvers. neal (annealing) is fast and "
          "reliable on\n  constrained QUBOs; QAOA/VQE (gate-model) match on small "
          "problems but need more\n  circuit depth as constraints grow -- the "
          "honest state of the art.")


if __name__ == "__main__":
    main()
