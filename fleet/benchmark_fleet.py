"""
benchmark_fleet.py -- honest multi-instance benchmark for the fleet layer.

Methodology (inherited from the Phase-3 lessons, non-negotiable):
  * EVERY instance counted -- no cherry-picked seeds; infeasible instances
    and solver failures are reported, not hidden.
  * Equal budget: all annealing-style solvers get the SAME iteration count;
    the QUBO gets a stated read budget.
  * Ground truth: exhaustive enumeration (instances kept small enough).
  * Reported: per-instance optimality gap, mean +/- std across instances,
    how often each solver hits the exact optimum, and wall time.

Run:
    py benchmark_fleet.py --seeds 5 --iters 3000
"""

from __future__ import annotations

import argparse
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import fleet_config as fc
import hybrid as hyb
import matheuristic as mh
import oracle
import qubo_layer as ql
import scenario as scen_mod


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--iters", type=int, default=3000)
    p.add_argument("--num-reads", type=int, default=1000)
    args = p.parse_args()

    solvers = ["greedy", "sa_naive", "alns_fixed", "alns",
               "rand+exact", "hybrid", "qubo+repair"]
    gaps = {s: [] for s in solvers}      # per-instance gap % (nan = failed)
    hits = {s: 0 for s in solvers}
    times = {s: [] for s in solvers}
    n_valid = 0

    print(f"Fleet benchmark: {args.seeds} instances, equal budget "
          f"(iters={args.iters}, qubo reads={args.num_reads})\n")

    for seed in range(args.seeds):
        scn = scen_mod.build_scenario(seed)
        tabs = oracle.get_tables(scn, verbose=False)
        ev = mh.Evaluator(scn, tabs)

        pe, fe, _ = mh.exhaustive(ev)
        if pe is None or not np.isfinite(fe):
            print(f"  seed {seed}: instance INFEASIBLE by exhaustive check "
                  f"-- excluded (reported, not hidden)")
            continue
        n_valid += 1

        results = {}
        t0 = time.perf_counter()
        g = mh.greedy(ev)
        results["greedy"] = ev.total(g) if g else float("inf")
        times["greedy"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        _, f = mh.sa_naive(ev, n_iters=args.iters, seed=seed + 1)
        results["sa_naive"] = f
        times["sa_naive"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        _, f = mh.alns(ev, n_iters=args.iters, seed=seed + 1, adaptive=False)
        results["alns_fixed"] = f
        times["alns_fixed"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        _, f = mh.alns(ev, n_iters=args.iters, seed=seed + 1, adaptive=True)
        results["alns"] = f
        times["alns"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        _, rf = hyb.solve_random_baseline(ev, n_samples=25, seed=seed + 1)
        results["rand+exact"] = rf
        times["rand+exact"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        _, hf, _ = hyb.solve_hybrid(ev, num_reads=args.num_reads, seed=42)
        results["hybrid"] = hf
        times["hybrid"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        q = ql.solve_fleet_qubo(scn, tabs, ev, num_reads=args.num_reads,
                                seed=42)
        results["qubo+repair"] = q["true_fuel"]
        times["qubo+repair"].append(time.perf_counter() - t0)

        line = f"  seed {seed}: exact {fe:6.2f}t | "
        for s in solvers:
            f = results[s]
            if np.isfinite(f):
                gap = (f - fe) / fe * 100
                gaps[s].append(gap)
                if gap < 1e-6:
                    hits[s] += 1
                line += f"{s} {gap:+5.1f}%  "
            else:
                gaps[s].append(float("nan"))
                line += f"{s}  FAIL  "
        print(line)

    if n_valid == 0:
        print("No valid instances.")
        return

    print(f"\n  {'solver':<14}{'mean gap':>10}{'std':>8}{'optimal':>10}"
          f"{'failed':>9}{'time':>9}")
    print("  " + "-" * 62)
    summary = {}
    for s in solvers:
        arr = np.array(gaps[s], dtype=float)
        ok = arr[np.isfinite(arr)]
        n_fail = int(np.sum(~np.isfinite(arr)))
        mg = ok.mean() if len(ok) else float("nan")
        sg = ok.std() if len(ok) else float("nan")
        summary[s] = (mg, sg, hits[s], n_fail)
        print(f"  {s:<14}{mg:>+9.1f}%{sg:>7.1f}%"
              f"{hits[s]:>6}/{n_valid:<4}{n_fail:>6}"
              f"{np.mean(times[s]):>8.2f}s")

    # ---- plot ------------------------------------------------------------- #
    fig, ax = plt.subplots(figsize=(9, 5))
    xs = np.arange(len(solvers))
    means = [summary[s][0] for s in solvers]
    stds = [summary[s][1] for s in solvers]
    colors = ["#9CA3AF", "#6B7280", "#60A5FA", "#1f77b4",
              "#94A3B8", "#7C3AED", "#E8772E"]
    bars = ax.bar(xs, means, yerr=stds, capsize=5, color=colors,
                  edgecolor="black", lw=0.8)
    for i, s in enumerate(solvers):
        mg, sg, h, nf = summary[s]
        note = f"{h}/{n_valid} optimal"
        if nf:
            note += f"\n{nf} failed"
        ax.text(i, max(0.3, means[i] + stds[i] + 0.6), note, ha="center",
                fontsize=9)
    ax.axhline(0, color="#16A34A", ls="--", lw=1.5, label="exact optimum")
    ax.set_xticks(xs)
    ax.set_xticklabels(solvers)
    ax.set_ylabel("Optimality gap % (mean +/- std across instances)")
    ax.set_title(f"Fleet solvers on {n_valid} instances -- equal budget, "
                 f"every run counted")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = fc.OUTPUTS_DIR / "fleet_benchmark.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"\n  Saved plot -> {out}")


if __name__ == "__main__":
    main()
