# Fleet-Level Fuel Optimization (Phase 4)

**A new problem formulation, in its own package.** Phases 1-3 (parent
directory, untouched) optimized a *single voyage* — and honestly concluded
that exact dynamic programming solves that problem outright. This package
moves to where the genuine combinatorial difficulty lives for the Indian
Coast Guard use case: **fleet operations planning**.

> *K vessels, M missions with time windows, a moving weather field.
> Which ship takes which missions, in what order, timed how — to minimize
> total fleet fuel?*

That is assignment × sequencing × routing (VRP-class, NP-hard). No DP solves
it; this is the level where a designed optimizer earns its existence.

---

## Architecture: a matheuristic (exact inner, adaptive outer)

```
            OUTER: adaptive search (ALNS)            <- heuristic, combinatorial
   assignment of missions to ships + serving order
                        |
                 asks, thousands of times
                        v
            INNER: exact voyage oracle               <- optimal, physics-driven
   time-expanded DP over (cell, slot) x speeds
   on the MOVING weather field, costed by the
   Phase-1 ML fuel model (imported read-only)
```

The outer search never wastes effort on badly-sailed voyages: every candidate
plan is priced with *provably optimal* routes and speed profiles inside it.

### The key data structure: Pareto serve tables

`serve[origin, mission, release_slot, finish_by_slot]` — minimum fuel to be
released at a location, sail to the mission, start within its window, and be
**done by** a given slot. The 4th axis carries the **fuel-vs-finish-time
trade-off**: sailing a mission slowly is cheap but can block the ship's next
window. Collapsing this axis (min-fuel only) made real instances look
infeasible — the Phase-1 fuel/time tension reappearing at fleet level is a
central finding of this package.

### The optimizer (`matheuristic.py`)

ALNS-style adaptive search (Ropke & Pisinger 2006 family), with the design
rules our Phase-2/3 benchmarks forced:

- **Feasibility-preserving representation** — plans are (assignment,
  sequence) structures, never penalty-weighted bits. There is *no penalty
  weight to tune* (the knob that wrecked BGSA and QAOA in Phase 2/3).
- **Operator portfolio** — relocate (random/worst), swap, intra-ship
  reorder, and a noisy destroy-and-repair (removes 2-3 missions, reinserts
  regret-style) that can discover coordinated multi-mission exchanges.
- **Adaptive operator weights** — selection probabilities follow recent
  success (the "adaptive" idea, deployed where it can win).
- **Reheating** — temperature restarts from the incumbent after stagnation.
- **Robust construction** — deterministic greedy, then randomized-restart
  greedy: tight-but-feasible instances where plain greedy dead-ends are real
  (seed 1 here).

### The quantum layer (`qubo_layer.py`)

The outer problem is where a QUBO is finally *natural* (discrete assignment,
~50-150 vars — beyond brute force, inside annealer reach). Two encodings were
tried; both results are kept as findings:

1. **Dispatch encoding** (mission × ship × release-slot): *structurally
   fails* — it is location-stateless, so second-wave missions are priced from
   home port and become unrepresentable; the one-hot collapses (the annealer
   prefers dropping missions to paying conflict penalties).
2. **Position encoding** (mission × ship × position, TSP-style a la Lucas
   2014): sequencing becomes representable via quadratic chain terms priced
   from the exact tables; deep-chain *timing* still cannot fit in pairwise
   terms, so decodes typically need an exact repair pass.

The measured gap between `qubo+repair` and the matheuristic is the *price of
flattening a stateful problem into a QUBO* — the quantitative argument for
the layered architecture.

---

## Files

| File | Role |
|------|------|
| `fleet_config.py` | Grid/time/speed discretisation, assumptions documented |
| `scenario.py` | Synthetic fleet instances: drifting storms, ships, staggered mission windows (schema mirrors real ICG data: vessel list + tasking list + gridded forecast) |
| `oracle.py` | Batched ML rate tables -> time-expanded DP -> Pareto serve tables (cached) |
| `matheuristic.py` | Evaluator (exact min-plus chaining), greedy/construct, naive SA, ALNS fixed/adaptive, exhaustive |
| `qubo_layer.py` | Position-indexed fleet QUBO -> neal -> exact repair + re-evaluation |
| `run_fleet.py` | One-command demo: solve one instance, print comparison, save plan plot |
| `benchmark_fleet.py` | Multi-instance honest benchmark (equal budget, every run counted) |

Parent-project files are imported **read-only** (`config`, `optimizer`,
`qubo_route.base_scenario_for`, `backends`); nothing outside `fleet/` is
modified.

```bash
cd fleet
py run_fleet.py --seed 0          # demo one instance end-to-end
py benchmark_fleet.py --seeds 5   # the honest comparison
```

---

## Results (5 instances, equal budget, every run counted)

Ground truth: exhaustive enumeration (20,160 plans/instance). Budget:
3,000 iterations for every annealing-style solver; 1,000 reads for the QUBO.

| Solver | Mean gap | Std | Optimal | Failed | Time |
|--------|--------:|----:|:-------:|:------:|-----:|
| greedy | +28.1% | 18.3% | 0/5 | 1 | 0.00 s |
| sa_naive | +9.5% | 6.8% | 1/5 | 0 | 0.08 s |
| alns_fixed | **+0.1%** | 0.1% | **4/5** | 0 | 0.22 s |
| **alns (ours)** | **+0.3%** | 0.7% | **4/5** | 0 | 0.40 s |
| qubo+repair | +17.4% | 25.5% | 2/5 | 0 | 2.14 s |

Per-instance rows (every seed shown, nothing curated):

```
seed 0: exact 20.36t | greedy +12.5%  sa_naive +12.5%  alns_fixed +0.0%  alns +0.0%  qubo +3.1%
seed 1: exact 21.14t | greedy   FAIL  sa_naive  +5.0%  alns_fixed +0.3%  alns +0.0%  qubo +17.1%
seed 2: exact 15.21t | greedy +59.3%  sa_naive  +9.9%  alns_fixed +0.0%  alns +0.0%  qubo +0.0%
seed 3: exact 14.57t | greedy +20.2%  sa_naive +20.2%  alns_fixed +0.0%  alns +0.0%  qubo +0.0%
seed 4: exact 15.16t | greedy +20.3%  sa_naive  +0.0%  alns_fixed +0.0%  alns +1.7%  qubo +66.7%
```

![Benchmark](outputs/fleet_benchmark.png)

**An honest nuance we keep visible:** at this instance size the *fixed*
operator portfolio matched the *adaptive* one (4/5 each; adaptive even
missed seed 4 by +1.7% where fixed found it). The data says the **operator
portfolio is what matters here**, not yet the adaptivity — adaptive weights
need larger instances (more iterations, more operator-usefulness variation)
to pay off, which is exactly the published ALNS experience. We report this
rather than claiming an adaptivity win the data does not support.

Per-instance behaviour worth naming (all visible in the benchmark output):

- **Greedy** swings wildly (optimal on easy instances, +59% on seed 2,
  outright infeasible on seed 1) — fleet fuel really is a combinatorial
  problem, not a dispatching heuristic's job.
- **Naive SA improves greedy but stalls** — a single move operator cannot
  restructure plans (e.g. it never discovers 3-mission chains on the cheap
  Interceptor).
- **ALNS (ours)** — see table; the operator portfolio + adaptivity is what
  finds the coordinated exchanges.
- **QUBO+repair** lands between greedy and ALNS and almost always needs the
  exact repair pass — consistent with the Phase-2/3 finding that flat
  penalty encodings fight the structure of constrained problems.

## Worked example plans (what the optimizer actually produces)

`run_fleet.py` saves a two-panel plot per instance. **How to read them:**

- **Left — the map.** Background is the region's wave field at mid-horizon
  (pale yellow = calm, dark red = storm core). ★ stars on the west edge are
  the three ships' home ports. Each arrow is a mission leg (start → end),
  coloured by the ship the optimizer assigned it to.
- **Right — the schedule (Gantt).** Each thick bar is a mission occupying its
  ship from `release → finish` slot; consecutive bars on one row are that
  ship's serving order. The thin bar under each row is that mission's allowed
  **start window** `[es, ls]`. Bars are drawn from the *true backtracked
  schedule* (the timeline that actually achieves the optimum), so bar
  boundaries are the real hand-off times, not a per-mission approximation.

Every title shows `ALNS total` next to `exact` — they match, i.e. the
optimizer hit the enumerated optimum on these instances.

### Seed 0 — a clean 3-ship split (20.36 t)

![Fleet plan seed 0](outputs/fleet_plan_seed0.png)

The cheap **Interceptor (green)** absorbs a 3-mission chain M4 → M2 → M3
(hand-offs at slots 15 and 24), the **Fast Patrol (orange)** takes M0 → M1
(hand-off at 18 — it must finish M0 by 18 so M1 still starts inside its
window, which is exactly the timing the corrected Gantt now shows), and the
big **Offshore Patrol (blue)** takes the single lonely M5. Balanced load, no
ship overworked.

### Seed 1 — the instance greedy *fails*, ALNS solves (21.14 t)

![Fleet plan seed 1](outputs/fleet_plan_seed1.png)

This is the headline case. Greedy cheapest-insertion **dead-ends here** (it
paints itself into a corner and cannot place the last mission — the `FAIL` in
the results table), yet ALNS finds a fully feasible optimal plan. The
Interceptor runs a tight three-mission chain M0 → M4 → M3 (hand-offs at 13 and
20) threading between the two storm cores, while Fast Patrol takes M1 → M5 and
Offshore Patrol covers M2. It is the concrete proof that fleet fuel planning is
a genuine combinatorial problem, not something a dispatch rule handles.

### Seed 2 — the counter-intuitive optimum: leave a ship in port (15.21 t)

![Fleet plan seed 2](outputs/fleet_plan_seed2.png)

The **Offshore Patrol row is empty** — the optimizer deployed only two of the
three ships. With all six missions clustered east of a strong central storm,
loading Fast Patrol (M0 → M2 → M5) and the Interceptor (M4 → M3 → M1) with
three missions each is cheaper than ever sailing the heavy, thirsty OPV out of
port. "Don't deploy that ship" is a fleet-level decision a per-voyage optimizer
literally cannot express, and a human planner tasked with "use your assets"
would routinely miss. This single plot is the clearest argument for optimizing
at the fleet level.

## Honest limitations (v1)

- Synthetic instances; physics coefficients inherited from Phase 1
  (plausible, not calibrated). The scenario schema is deliberately shaped so
  real vessel/tasking/forecast data can drop in.
- Slot quantisation (1 h) caps effective transit speed at one cell per slot
  — fast ships gain fuel efficiency but not schedule time; finer slots would
  fix this at ~linear table cost.
- Waiting is free only at stations (anchorage assumption); no loitering
  costs mid-ocean, no return-home leg, single region-wide current.
- Missions are point-to-point patrol legs; area-coverage patrols, refuelling
  and crew constraints are future work.
- Exhaustive ground truth limits benchmark instances to M<=6; larger
  instances need best-known references instead.

## Where this goes next

- Scale study: M=10-15, K=5 (beyond exhaustive; ALNS vs QUBO at real sizes).
- The hierarchical-quantum idea, now placed correctly: coarse fleet
  assignment as a small QUBO on hardware, exact/classical refinement below.
- Real data drop-in: IMD/INCOIS gridded forecasts + actual vessel lists.
