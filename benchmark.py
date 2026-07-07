"""
benchmark.py  --  the HONEST solver benchmark (replaces every ad-hoc comparison).

This exists because earlier comparisons in this repo were unfair (unequal budgets)
and cherry-picked (single hand-selected seeds). This harness fixes that by design:

  * EQUAL, STATED budget per solver (printed below and in BENCHMARK.md).
  * MANY seeds per cell (default 15); EVERY run is counted -- no best-of, no
    selected seed.
  * Reports mean +/- std of the optimality gap, plus % optimal and % feasible.
  * Ground truth = exact DP (the routing QUBO is a shortest path, solvable exactly).

Two studies:
  A. Reliability vs problem size   -> outputs/bench_size.png
  B. Sensitivity to penalty weight -> outputs/bench_penalty.png
Results are also written to BENCHMARK.md.

Run:
    py benchmark.py                 # full run (~20-40 min)
    py benchmark.py --quick         # small smoke test
"""

from __future__ import annotations

import argparse
import time
import types
import warnings

warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import config
import quantum_gate as qg

# ---- FIXED BUDGETS (stated up front; identical across every cell) ---------- #
BUDGET = {
    "neal": dict(num_reads=200, num_sweeps=1000),
    "tabu": dict(num_reads=200),
    "gsa":  dict(restarts=10, n_agents=100, iters=300),
    "qaoa": dict(reps=3, maxiter=200),
    "vqe":  dict(reps=2, maxiter=300),
}
CLASSICAL = ["neal", "tabu", "gsa"]
GATE = ["qaoa", "vqe"]


def make_problem(rows, cols, storms, seed, penalty_mult=10.0):
    a = types.SimpleNamespace(problem="route", rows=rows, cols=cols, storms=storms,
                              seed=seed, cruise=16.0, distance=config.DEFAULT_VOYAGE_NM,
                              ship_type="Offshore_Patrol", penalty_mult=penalty_mult)
    qubo, decode, meta, ctx = qg.build_route_problem(a)
    return qubo, decode, meta, ctx


def solve_once(solver, qubo, qp, n, decode, s):
    """One solve of `solver` at seed `s`. Returns (gap%, feasible, seconds)."""
    b = BUDGET[solver]
    t = time.perf_counter()
    if solver == "neal":
        vd = qg.run_neal(qubo, seed=s)
    elif solver == "tabu":
        vd = qg.run_tabu(qubo, seed=s)
    elif solver == "gsa":
        vd = qg.run_gsa(qubo, seed=s, n_agents=b["n_agents"],
                        iters=b["iters"], restarts=b["restarts"])
    elif solver == "qaoa":
        vd = qg.run_qaoa(qp, b["reps"], b["maxiter"], seed=s)
    elif solver == "vqe":
        vd = qg.run_vqe(qp, n, b["reps"], b["maxiter"], seed=s)
    dt = time.perf_counter() - t
    path, fuel, _ = decode(vd)
    return path, fuel, dt


def aggregate(solver, qubo, qp, n, decode, dp_fuel, seeds):
    gaps, feas, opt, times = [], 0, 0, []
    for s in seeds:
        path, fuel, dt = solve_once(solver, qubo, qp, n, decode, s)
        times.append(dt)
        if path is not None:
            feas += 1
            g = (fuel - dp_fuel) / dp_fuel * 100
            gaps.append(g)
            if abs(g) < 1e-6:
                opt += 1
    ns = len(seeds)
    return {
        "feas_pct": 100 * feas / ns,
        "opt_pct": 100 * opt / ns,
        "mean_gap": (float(np.mean(gaps)) if gaps else float("nan")),
        "std_gap": (float(np.std(gaps)) if gaps else float("nan")),
        "mean_time": float(np.mean(times)),
        "n_feasible": feas, "n": ns,
    }


# --------------------------------------------------------------------------- #
# Study A: reliability vs problem size                                         #
# --------------------------------------------------------------------------- #
def study_size(sizes, n_seeds, max_qubits, storms):
    seeds = list(range(n_seeds))
    results = {}          # (n_vars) -> {solver: agg}
    order = []
    print(f"\n=== STUDY A: reliability vs size ({n_seeds} seeds, equal budget) ===")
    for rows, cols in sizes:
        qubo, decode, meta, ctx = make_problem(rows, cols, storms, seed=3)
        qp = qg.qubo_to_qp(qubo)
        n = meta["n_qubits"]
        dp = ctx["dp_fuel"]
        order.append((n, f"{rows}x{cols}"))
        results[n] = {}
        solvers = CLASSICAL + ([s for s in GATE] if n <= max_qubits else [])
        for solver in solvers:
            r = aggregate(solver, qubo, qp, n, decode, dp, seeds)
            results[n][solver] = r
            print(f"  {rows}x{cols} n={n:<3} {solver:<5} "
                  f"opt {r['opt_pct']:>3.0f}%  feas {r['feas_pct']:>3.0f}%  "
                  f"gap {r['mean_gap']:+.1f}+-{r['std_gap']:.1f}%  {r['mean_time']:.2f}s")
    return results, order


# --------------------------------------------------------------------------- #
# Study B: sensitivity to penalty weight                                       #
# --------------------------------------------------------------------------- #
def study_penalty(rows, cols, storms, mults, n_seeds):
    seeds = list(range(n_seeds))
    results = {}          # penalty_mult -> {solver: agg}
    print(f"\n=== STUDY B: penalty sweep on {rows}x{cols} ({n_seeds} seeds) ===")
    for pm in mults:
        qubo, decode, meta, ctx = make_problem(rows, cols, storms, seed=3, penalty_mult=pm)
        qp = qg.qubo_to_qp(qubo)
        n = meta["n_qubits"]
        dp = ctx["dp_fuel"]
        results[pm] = {}
        for solver in CLASSICAL:
            r = aggregate(solver, qubo, qp, n, decode, dp, seeds)
            results[pm][solver] = r
            print(f"  P={pm:>4}x  {solver:<5} opt {r['opt_pct']:>3.0f}%  "
                  f"feas {r['feas_pct']:>3.0f}%  gap {r['mean_gap']:+.1f}+-{r['std_gap']:.1f}%")
    return results


# --------------------------------------------------------------------------- #
# Plots + markdown                                                             #
# --------------------------------------------------------------------------- #
COLORS = {"neal": "#1f77b4", "tabu": "#0891B2", "gsa": "#7C3AED",
          "qaoa": "#E8772E", "vqe": "#D62728"}


def plot_size(results, order, out):
    ns = [n for n, _ in order]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    for solver in CLASSICAL + GATE:
        xs, ys, es, fs = [], [], [], []
        for n in ns:
            if solver in results[n]:
                r = results[n][solver]
                xs.append(n); ys.append(r["mean_gap"]); es.append(r["std_gap"])
                fs.append(r["feas_pct"])
        if xs:
            ax1.errorbar(xs, ys, yerr=es, marker="o", capsize=3, lw=2,
                         color=COLORS[solver], label=solver)
            ax2.plot(xs, fs, marker="o", lw=2, color=COLORS[solver], label=solver)
    ax1.axhline(0, color="green", ls="--", lw=1, label="optimum")
    ax1.set_xlabel("QUBO size (binary variables)")
    ax1.set_ylabel("Optimality gap % (mean +/- std over seeds)")
    ax1.set_title("Solution quality vs size")
    ax1.legend(fontsize=9); ax1.grid(True, alpha=0.3)
    ax2.set_xlabel("QUBO size (binary variables)")
    ax2.set_ylabel("Feasibility % (valid runs / seeds)")
    ax2.set_title("Constraint satisfaction vs size")
    ax2.legend(fontsize=9); ax2.grid(True, alpha=0.3)
    fig.suptitle("Honest benchmark: solver reliability vs problem size "
                 "(equal budget, all seeds counted)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def plot_penalty(results, rows, cols, out):
    mults = sorted(results.keys())
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for solver in CLASSICAL:
        ys = [results[pm][solver]["mean_gap"] for pm in mults]
        es = [results[pm][solver]["std_gap"] for pm in mults]
        ax.errorbar(mults, ys, yerr=es, marker="o", capsize=3, lw=2,
                    color=COLORS[solver], label=solver)
    ax.axhline(0, color="green", ls="--", lw=1, label="optimum")
    ax.set_xlabel("Penalty weight multiplier  (P = mult x max cell cost)")
    ax.set_ylabel("Optimality gap % (mean +/- std)")
    ax.set_title(f"Sensitivity to penalty weight ({rows}x{cols} route QUBO)")
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def write_markdown(size_res, size_order, pen_res, pen_grid, n_seeds, n_seeds_b, path):
    L = []
    L.append("# Honest Solver Benchmark\n")
    L.append("Generated by `benchmark.py`. Every solver gets an **equal, fixed "
             "budget**; **every seed is counted** (no best-of, no cherry-picking); "
             "results are **mean ± std** over seeds. Ground truth = exact DP.\n")
    L.append("## Budgets (identical across all cells)\n")
    for k, v in BUDGET.items():
        L.append(f"- **{k}**: {v}")
    L.append("")
    L.append(f"## Study A — reliability vs size ({n_seeds} seeds)\n")
    L.append("| Grid | Vars | Solver | % optimal | % feasible | Mean gap ± std | Time/solve |")
    L.append("|------|-----:|--------|:---------:|:----------:|:--------------:|-----------:|")
    for n, label in size_order:
        for solver in CLASSICAL + GATE:
            if solver in size_res[n]:
                r = size_res[n][solver]
                L.append(f"| {label} | {n} | {solver} | {r['opt_pct']:.0f}% | "
                         f"{r['feas_pct']:.0f}% | {r['mean_gap']:+.1f} ± {r['std_gap']:.1f}% | "
                         f"{r['mean_time']:.2f} s |")
    L.append("")
    L.append(f"## Study B — penalty-weight sensitivity on {pen_grid} ({n_seeds_b} seeds)\n")
    L.append("| Penalty ×max | Solver | % optimal | % feasible | Mean gap ± std |")
    L.append("|-------------:|--------|:---------:|:----------:|:--------------:|")
    for pm in sorted(pen_res.keys()):
        for solver in CLASSICAL:
            r = pen_res[pm][solver]
            L.append(f"| {pm}× | {solver} | {r['opt_pct']:.0f}% | {r['feas_pct']:.0f}% | "
                     f"{r['mean_gap']:+.1f} ± {r['std_gap']:.1f}% |")
    L.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def main() -> None:
    p = argparse.ArgumentParser(description="Honest, fair, multi-seed solver benchmark.")
    p.add_argument("--seeds", type=int, default=15, help="seeds for Study A")
    p.add_argument("--seeds-b", type=int, default=10, help="seeds for Study B")
    p.add_argument("--max-qubits", type=int, default=16,
                   help="run QAOA/VQE only at or below this size")
    p.add_argument("--storms", type=int, default=2)
    p.add_argument("--gsa-restarts", type=int, default=0,
                   help="override GSA restart budget (0 = use default 10)")
    p.add_argument("--quick", action="store_true", help="tiny smoke-test config")
    p.add_argument("--fast", action="store_true",
                   help="~10 min: fewer sizes/seeds, lighter GSA, skip slow "
                        "gate-model (cite audit_seeds.py instead)")
    args = p.parse_args()

    if args.gsa_restarts:
        BUDGET["gsa"]["restarts"] = args.gsa_restarts

    if args.quick:
        sizes = [(3, 4), (4, 4), (4, 6)]
        mults = [1, 5, 20]
        args.seeds, args.seeds_b = 4, 3
    elif args.fast:
        sizes = [(3, 4), (4, 5), (5, 6), (6, 7)]      # 12, 20, 30, 42 vars
        mults = [1, 2, 5, 10, 20]
        args.seeds, args.seeds_b = 8, 6
        args.max_qubits = 0                           # skip gate-model (use audit)
        BUDGET["gsa"]["restarts"] = args.gsa_restarts or 6
    else:
        sizes = [(3, 4), (4, 4), (4, 5), (4, 6), (5, 6), (5, 7), (6, 7)]
        mults = [1, 2, 3, 5, 10, 20]

    print("Budgets (equal across every cell):")
    for k, v in BUDGET.items():
        print(f"  {k:<5} {v}")

    t0 = time.perf_counter()
    size_res, size_order = study_size(sizes, args.seeds, args.max_qubits, args.storms)
    pen_grid = "4x6"
    pen_res = study_penalty(4, 6, args.storms, mults, args.seeds_b)

    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    plot_size(size_res, size_order, config.OUTPUTS_DIR / "bench_size.png")
    plot_penalty(pen_res, 4, 6, config.OUTPUTS_DIR / "bench_penalty.png")
    write_markdown(size_res, size_order, pen_res, pen_grid,
                   args.seeds, args.seeds_b, "BENCHMARK.md")

    print(f"\nDone in {(time.perf_counter()-t0)/60:.1f} min.")
    print("  -> outputs/bench_size.png, outputs/bench_penalty.png, BENCHMARK.md")


if __name__ == "__main__":
    main()
