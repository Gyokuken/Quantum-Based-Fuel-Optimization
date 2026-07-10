"""
run_fleet.py -- end-to-end fleet demo (Phase 4).

Pipeline: scenario -> exact voyage oracle tables -> all solvers -> plot.

Solvers compared (equal search budget where applicable):
  greedy        cheapest-insertion dispatcher       (human-planner baseline)
  sa_naive      single-operator SA                  (plain metaheuristic)
  alns_fixed    operator portfolio, uniform weights (ablation)
  alns          adaptive portfolio                  (THE optimizer)
  qubo+repair   position-indexed QUBO via neal      (quantum-layer baseline)
  exhaustive    exact enumeration                   (ground truth, small M)

Run:
    py run_fleet.py --seed 0
    py run_fleet.py --seed 3 --iters 5000
"""

from __future__ import annotations

import argparse
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import fleet_config as fc
import matheuristic as mh
import oracle
import qubo_layer as ql
import scenario as scen_mod


SHIP_COLORS = ["#1f77b4", "#E8772E", "#16A34A", "#7C3AED", "#D62728"]


def plot_plan(scn, ev, plan, title, out):
    """Two panels: (left) weather mid-horizon + mission legs coloured by the
    ship serving them; (right) release->finish spans per ship (Gantt-ish)."""
    T = scn.waves.shape[0]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.5),
                                   gridspec_kw={"width_ratios": [1.5, 1.0]})

    mid = T // 2
    im = ax1.imshow(scn.waves[mid], origin="lower", aspect="auto",
                    cmap="YlOrRd", vmin=0, vmax=8,
                    extent=[-0.5, fc.N_COLS - 0.5, -0.5, fc.N_ROWS - 0.5])
    fig.colorbar(im, ax=ax1, label=f"Wave height (m) at slot {mid}")

    owner = {j: sid for sid, seq in plan.items() for j in seq}
    for j, m in enumerate(scn.missions):
        sid = owner.get(j)
        col = SHIP_COLORS[sid % len(SHIP_COLORS)] if sid is not None else "gray"
        ax1.annotate("", xy=(m.end[1], m.end[0]),
                     xytext=(m.start[1], m.start[0]),
                     arrowprops=dict(arrowstyle="-|>", lw=2.2, color=col))
        ax1.text(m.start[1], m.start[0] + 0.25, m.name, fontsize=9,
                 color=col, fontweight="bold")
    for i, s in enumerate(scn.ships):
        ax1.plot(s.home[1], s.home[0], marker="*", ms=18,
                 color=SHIP_COLORS[i % len(SHIP_COLORS)], mec="black",
                 label=f"{s.name} ({s.ship_class})")
    ax1.set_title("Mission legs coloured by assigned ship")
    ax1.set_xlabel("Column (west -> east)")
    ax1.set_ylabel("Row (south -> north)")
    ax1.legend(loc="upper left", fontsize=8)

    # right: release->finish spans per ship (from exact prefix evaluation)
    yticks, ylabels = [], []
    for i, s in enumerate(scn.ships):
        seq = plan[s.id]
        col = SHIP_COLORS[i % len(SHIP_COLORS)]
        y = len(scn.ships) - 1 - i
        yticks.append(y)
        ylabels.append(s.name)
        rel = 0
        for L in range(1, len(seq) + 1):
            _, fin = ev.ship_cost(s, tuple(seq[:L]))
            j = seq[L - 1]
            m = scn.missions[j]
            ax2.barh(y, fin - rel, left=rel, height=0.5, color=col,
                     alpha=0.75, edgecolor="black", lw=0.6)
            ax2.text((rel + fin) / 2, y, m.name, ha="center", va="center",
                     fontsize=9, color="white", fontweight="bold")
            ax2.plot([m.es, m.ls], [y - 0.38, y - 0.38], color=col, lw=2,
                     alpha=0.5)
            rel = fin
    ax2.set_yticks(yticks)
    ax2.set_yticklabels(ylabels)
    ax2.set_xlabel("Slot (release -> finish spans; thin bar = start window)")
    ax2.set_xlim(0, T)
    ax2.set_title("Schedule (exact timings from the oracle)")
    ax2.grid(True, axis="x", alpha=0.3)

    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    fc.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description="Fleet fuel optimization demo.")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ships", type=int, default=fc.DEFAULT_N_SHIPS)
    p.add_argument("--missions", type=int, default=fc.DEFAULT_N_MISSIONS)
    p.add_argument("--iters", type=int, default=3000)
    p.add_argument("--num-reads", type=int, default=1000)
    args = p.parse_args()

    print(f"Fleet demo -- seed {args.seed}: {args.ships} ships, "
          f"{args.missions} missions, {fc.N_ROWS}x{fc.N_COLS} grid, "
          f"{fc.HORIZON_SLOTS} slots")
    scn = scen_mod.build_scenario(args.seed, n_ships=args.ships,
                                  n_missions=args.missions)
    t0 = time.perf_counter()
    tabs = oracle.get_tables(scn)
    print(f"  oracle tables ready in {time.perf_counter() - t0:.1f}s\n")
    ev = mh.Evaluator(scn, tabs)

    rows = []

    t0 = time.perf_counter()
    g = mh.greedy(ev)
    gf = ev.total(g) if g else float("inf")
    rows.append(("greedy", gf, time.perf_counter() - t0))
    if g is None and mh.construct(ev, seed=args.seed) is None:
        print("  No feasible plan found even with randomized construction -- "
              "instance appears infeasible; try another seed.")
        return

    t0 = time.perf_counter()
    _, f_sa = mh.sa_naive(ev, n_iters=args.iters, seed=args.seed + 1)
    rows.append(("sa_naive", f_sa, time.perf_counter() - t0))

    t0 = time.perf_counter()
    _, f_fx = mh.alns(ev, n_iters=args.iters, seed=args.seed + 1,
                      adaptive=False)
    rows.append(("alns_fixed", f_fx, time.perf_counter() - t0))

    t0 = time.perf_counter()
    best_plan, f_al = mh.alns(ev, n_iters=args.iters, seed=args.seed + 1,
                              adaptive=True)
    rows.append(("alns (ours)", f_al, time.perf_counter() - t0))

    t0 = time.perf_counter()
    q = ql.solve_fleet_qubo(scn, tabs, ev, num_reads=args.num_reads,
                            seed=42)
    rows.append((f"qubo+repair", q["true_fuel"], time.perf_counter() - t0))

    exact_f = None
    if args.missions <= 6:
        t0 = time.perf_counter()
        pe, fe, n_plans = mh.exhaustive(ev)
        exact_f = fe
        rows.append((f"exhaustive ({n_plans:,})", fe,
                     time.perf_counter() - t0))

    print(f"  {'solver':<22}{'fuel (t)':>10}{'gap':>9}{'time':>9}")
    print("  " + "-" * 52)
    for name, f, dt in rows:
        gap = ("    -" if exact_f is None or not np.isfinite(f)
               else f"{(f - exact_f) / exact_f * 100:+.1f}%")
        fs = f"{f:10.2f}" if np.isfinite(f) else "       INF"
        print(f"  {name:<22}{fs}{gap:>9}{dt:>8.2f}s")
    if not q["raw_feasible"]:
        print("  note: qubo decode needed exact repair "
              f"({q['reason']}) -- flat encodings cannot carry chained timing")

    print("\n  Best plan (alns):")
    print(mh.describe_plan(ev, best_plan))

    out = fc.OUTPUTS_DIR / f"fleet_plan_seed{args.seed}.png"
    plot_plan(scn, ev, best_plan,
              f"Fleet plan, seed {args.seed} -- ALNS total "
              f"{f_al:.2f} t" + (f" (exact {exact_f:.2f} t)" if exact_f else ""),
              out)
    print(f"\n  Saved plot -> {out}")


if __name__ == "__main__":
    main()
