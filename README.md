# Maritime Fuel Efficiency Optimization — Prototype

**Indian Coast Guard — Problem Statement 77: "Fuel consumption optimization using
AI-based tools."**

A working prototype that **predicts a ship's fuel-burn rate** from static (vessel
design) + dynamic (voyage) data, then uses a **quantum-inspired optimizer**
(simulated annealing) to recommend the **fuel-minimizing speed that still meets
the arrival deadline** — i.e. data-driven *slow steaming*. CO₂ savings are
reported too, for IMO/environmental compliance.

---

## ⭐ PROJECT STATUS — read this first (handoff for a fresh session)

This project grew well past the original single-ship prototype. Here is the whole
picture, honestly, so anyone (or a new AI session) can pick it up cold.

### The arc, phase by phase (all DONE unless noted)

| Phase | What it is | Where | Status |
|-------|-----------|-------|--------|
| **1** | Synthetic ship data (cubic fuel physics) → ML fuel-rate model (R²≈0.99) → simulated-annealing slow-steaming speed optimizer + CO₂ | root | ✅ done |
| **2a** | Speed optimization as a **QUBO** (pyqubo + neal) | `qubo_speed.py` | ✅ |
| **2b** | Weather **routing** as a QUBO (grid, storms) vs exact DP | `qubo_route.py` | ✅ |
| **2c** | Same QUBO on **gate-model QAOA + VQE** (Qiskit simulator) | `quantum_gate.py` | ✅ |
| **2d** | **GSA** (Gravitational Search Algorithm), continuous + binary | `gsa.py`, `gsa_speed.py` | ✅ |
| **2e** | **QGSO** (quantum-inspired GSA) vs GSA | `qgso.py` | ✅ |
| **HONEST BENCHMARK** | equal budget, many seeds, every run counted, mean±std | `benchmark.py` → `BENCHMARK.md` | ✅ |
| **4** | **Fleet reformulation** (K ships, M missions w/ time windows, moving weather) + our own optimizer (**ALNS matheuristic**) | `fleet/` | ✅ |
| **5** | **Quantum-classical HYBRID** (assignment QUBO + exact oracle) + ran on **real IBM quantum hardware** | `fleet/hybrid.py`, `fleet/quantum_qaoa.py` | ✅ |
| 3 | Streamlit dashboard | — | ⬜ planned, not built |

### The honest headline findings (do NOT overclaim beyond these)

1. **Single voyage is easy** — exact DP solves route+speed instantly. No optimizer (or quantum) is *needed* there; Phase 1–2 are demonstrations.
2. **On the small route QUBOs:** classical **neal / tabu win** (optimal, penalty-invariant). GSA is penalty-sensitive; **QGSO genuinely beats GSA** (more robust) but still loses to neal. QAOA/VQE (simulated) are unreliable even at 12 qubits.
3. **The real hard problem is the FLEET** (assignment × sequencing × routing, NP-hard). Our **ALNS matheuristic** beats greedy/human planning by 20–60%.
4. **The hybrid (assignment QUBO + exact oracle) is the best solver** on 10 fleet instances: **10/10 optimal**, beating ALNS (8/10). An **ablation** (`rand+exact`, random assignments + same exact scoring → 5/10) proves the QUBO earns its keep, not just the exact layer.
5. **We ran it on a REAL quantum computer** (IBM `ibm_fez`, 156-qubit, job `d9gjv53sbqfc73eoocmg`): 8-qubit instance → found the exact optimum. **BUT** this is a *"runs on real silicon end-to-end"* milestone, **NOT** a quantum performance win — at 8 qubits (16 possible assignments) the exact scorer guarantees the optimum regardless of hardware. No evidence quantum helps yet; needs larger instances.
6. **"Quantum" clarification:** QUBO is only a problem *description*. The hybrid solves it with **neal = classical** (quantum-*portable*). Real quantum = QAOA on IBM (`fleet/quantum_qaoa.py --backend ibm`). QAOA even there is approximate + noisy, so the classical exact scorer is essential (it recomputes true fuel; the QUBO is only a *pairwise shadow* of the real cost).

### Publication status (my honest read)
**Not yet peer-review ready.** Synthetic data, tiny scale (M≤6 for exhaustive truth), known methods. **Strong project/report foundation.** To publish: scale up (M=12–20 + a strong baseline like OR-Tools), and run the hybrid on real hardware *at a scale where the classical scorer can't brute-force it*.

### The single most valuable next step
**Scale-up study: M=12–20, K=5**, with OR-Tools/CP-SAT as a strong baseline, and re-run hybrid vs ALNS vs `rand+exact` there. That's the experiment that reveals whether the QUBO's proposals actually beat classical at real sizes. (Real-hardware QAOA at that scale is the follow-on.)

### Working context a new session MUST know
- **Honesty is the non-negotiable ethos here.** Earlier in the project, cherry-picked seeds and unequal budgets produced misleading results; the user caught it. Everything now uses equal budgets, many seeds, ablations, and stated caveats. **Never present a cherry-picked or rigged result.**
- **Do NOT add a `Co-Authored-By: Claude` trailer to commits** in this repo (user requirement; history was rewritten once to strip it).
- **`fleet/` imports parent files read-only** — do not modify root files from fleet work.
- **IBM token** is saved in `~/.qiskit` (NOT in the repo). Real-hardware runs use the free Open plan (~10 min QPU/month) — be economical (optimize on simulator, run one circuit on hardware).
- Repo: **github.com/Gyokuken/Quantum-Based-Fuel-Optimization**, branch `main`. Push cadence: commit + push when the user asks; pushes sometimes time out — retry.
- Windows, Python 3.13. Two READMEs: **this one** (root, Phases 1–2e) and **`fleet/README.md`** (Phases 4–5, the fleet/hybrid/quantum story).

### Fastest way to see it work
```bash
py demo.py                                    # Phase 1: predict + speed optimize
py benchmark.py --fast --with-qgso            # honest solver benchmark (~20 min)
cd fleet && py run_fleet.py --seed 0          # fleet plan (map + Gantt)
cd fleet && py benchmark_fleet.py --seeds 10  # hybrid vs ALNS vs baselines
cd fleet && py quantum_qaoa.py --backend aer --ships 2 --missions 4   # QAOA (sim)
```

---

## Quick start

```bash
pip install -r requirements.txt   # numpy, pandas, scikit-learn, joblib, matplotlib
py demo.py                        # runs the whole pipeline + saves a plot
```

`demo.py` generates data → trains & compares models → optimizes speed for two
voyage scenarios → saves `outputs/voyage_fuel_vs_speed.png`.

Run stages individually:

```bash
py generate_data.py --n 10000 --seed 42                 # -> data/ship_fuel_data.csv
py train_model.py                                        # -> models/ship_fuel_model.joblib
py optimizer.py --distance 600 --deadline 80 --waves 4 --wind 30
```

---

## Why ships are different from cars (the modelling insight)

- **Cubic speed–power law.** A ship's fuel *rate* (tonnes/day) grows with the
  **cube of speed** (`power ~ displacement^(2/3) × speed³`). So minimizing fuel
  alone trivially says "go as slow as possible".
- **The real problem is constrained.** Operationally you must **arrive on time**.
  So we minimize *total voyage fuel* `= rate(speed) × distance / (24 × speed)`
  subject to a **deadline** (`speed ≥ distance / deadline`). Because the ship
  also burns a speed-independent **hotel/auxiliary load**, the total-fuel curve
  is **U-shaped** — there is an "economic speed". This is exactly the real-world
  practice of **slow steaming**.
- **Environment matters.** Sea state (wave height), wind, current
  (speed-through-water vs over-ground), and load condition all change fuel burn.

---

## What's in here

| File | Role | Report § |
|------|------|----------|
| `config.py` | Feature schema, ship classes, voyage + emission constants | §3 |
| `generate_data.py` | Physics-based ship-voyage simulator (cubic law) | §4 |
| `train_model.py` | Linear / Random Forest / Gradient Boosting + metrics | §6 |
| `optimizer.py` | Simulated-annealing slow-steaming optimizer (+ CO₂) | §7 |
| `demo.py` | One-command end-to-end demonstration | §12 |
| `qubo_speed.py` | **Phase 2a:** speed optimization as a QUBO (pyqubo + neal) | §7 |
| `qubo_route.py` | **Phase 2b:** weather routing as a QUBO (the headline) | §7 |
| `backends.py` | Solver swap point: `neal` / `dwave` (real QPU) / `tabu` / `gsa` | §7 |
| `quantum_gate.py` | **Phase 2c:** the same QUBO on gate-model **QAOA + VQE** (Qiskit) | §7 |
| `gsa.py` | **Phase 2d:** Gravitational Search Algorithm (continuous + binary) | §7 |
| `gsa_speed.py` | **Phase 2d:** GSA vs SA vs grid on cruise speed (+ convergence plot) | §7 |
| `qgso.py` | **Phase 2e:** QGSO — quantum-inspired GSA (qubit rotation-gate update) | §7 |
| `benchmark.py` | **Honest solver benchmark** — equal budget, many seeds, mean±std | §7 |
| `audit_seeds.py` | Full seed-distribution audit (exposes any cherry-picking) | §7 |

Ship classes modeled (ICG-style patrol fleet): **Interceptor**, **Fast Patrol**,
**Offshore Patrol Vessel**. Generated at runtime: `data/`, `models/`, `outputs/`.

---

## Phase 1 results (from `py demo.py`)

**Model comparison** — predicting fuel rate (t/day), 20% held-out test + 5-fold CV:

| Model | CV R² | Test R² | MAE | RMSE | MAPE |
|-------|------:|--------:|----:|-----:|-----:|
| **Gradient Boosting** | 0.987 | **0.987** | 1.30 | 2.45 | 11.3% |
| Random Forest | 0.977 | 0.980 | 1.52 | 3.06 | 9.3% |
| Linear Regression | 0.641 | 0.648 | 9.10 | 12.97 | 354% |

The linear baseline **fails badly** (R² 0.65, MAPE 354%) — it cannot represent the
cubic law across vessels spanning ~5 to ~90 t/day. Gradient boosting nails it
(R² ≈ 0.99). This is a strong illustration of *why* nonlinear models are needed.

**Optimization** — Offshore Patrol Vessel, 600 nm leg, baseline = 18 kn service speed:

| Scenario | Optimal speed | Fuel | vs baseline | CO₂ saved |
|----------|--------------:|-----:|------------:|----------:|
| Tight schedule (40 h) | 15.0 kn (deadline-bound) | 39.9 t | **−29%** | 52.5 t |
| Relaxed schedule (90 h) | 8.4 kn (economic speed) | 18.3 t | **−68%** | 121.8 t |

In both cases simulated annealing matched the brute-force grid optimum to within
**0.01 kn**, proving it found the true optimum.

![Total voyage fuel vs speed](outputs/voyage_fuel_vs_speed.png)

*The U-shaped curve is total voyage fuel. The grey region is too slow to meet the
deadline; the optimizer (green) picks the slowest feasible speed, well below the
habitual baseline (red).*

---

## Phase 2 results — genuine "quantum-inspired" QUBO

The optimization is reformulated as a **QUBO** (Quadratic Unconstrained Binary
Optimization) — the exact Ising/binary form a **D-Wave quantum annealer** solves
natively — and solved classically with `neal`. The *same QUBO* could be submitted
to real quantum hardware unchanged; that portability is what makes it
"quantum-inspired". Constraints (pick one option, meet the deadline, no illegal
moves) are encoded as **penalty terms**, the standard QUBO technique.

**Phase 2a — speed as a QUBO** (`py qubo_speed.py`): one-hot encode candidate
speeds, solve with neal. It lands on the same speed as Phase 1's SA/grid (within
the discretization step), proving the QUBO machinery is correct.

**Phase 2b — weather routing as a QUBO** (`py qubo_route.py`): the real headline.
A ship crosses a weather field; each grid cell's fuel cost comes from the **Phase 1
ML model**. The QUBO picks the minimum-fuel path *around* the storm:

| Route | Fuel (t) | Note |
|-------|---------:|------|
| Naive straight line (through storm) | 58.3 | what a captain does by default |
| **QUBO route (neal)** | **52.7** | **−9.6%** — detours around the storm |
| Brute-force optimum | 52.7 | matches QUBO (equal fuel) ✓ |

![Weather routing](outputs/route_qubo.png)

*The QUBO (blue) routes around the high-wave storm (dark red); the naive route
(black) plows straight through it. A centred storm has two equal optima
(north/south) — the QUBO found one, brute force the other, both 52.7 t.*

### Swappable solver backends (`backends.py`)

The same QUBO can be handed to different solvers with `--backend`:

| Backend | What it is | Needs |
|---------|-----------|-------|
| `neal` (default) | Classical simulated annealing | nothing — offline |
| `tabu` | Classical Tabu search | nothing — offline |
| `dwave` | **Real D-Wave quantum annealer** via Leap | a Leap API token |

```bash
py qubo_route.py --rows 5 --cols 7 --backend tabu
py qubo_route.py --rows 5 --cols 7 --backend dwave   # needs a Leap token
```

> **Note on `dwave`:** D-Wave's free *Trial* plan now allows demos only — it no
> longer issues API tokens for submitting your own problems. Running our QUBO on a
> real annealer needs a paid/commercial or academic Leap plan. The code path is
> ready; it's a one-flag switch if/when access is granted.

### Phase 2c — the same QUBO on gate-model quantum (QAOA + VQE)

`quantum_gate.py` proves the QUBO is portable to **gate-model** quantum computers
(IBM-style), not just annealers. It converts the QUBO → an Ising Hamiltonian and
solves it with **QAOA** and **VQE** on Qiskit's free local simulator (the same
code runs on real IBM hardware via the free Open plan).

```bash
py quantum_gate.py --problem speed --levels 8          # 8 qubits
py quantum_gate.py --problem route --rows 3 --cols 4 --storms 1 --seed 2
```

| Problem | Qubits | QAOA | VQE | vs exact |
|---------|-------:|------|-----|----------|
| Speed (8 levels) | 8 | 16.0 kn ✓ | 16.0 kn ✓ | **both match exactly** |
| Route (3×4, 1 storm) | 12 | approx | within ~6% | heuristic, needs depth |

**Honest finding:** QAOA/VQE nail the small *unconstrained-ish* speed QUBO, but on
the penalty-heavy *route* QUBO (one-hot + connectivity + endpoint constraints) the
shallow variational circuits are only approximate. Annealing (neal/D-Wave) handles
these constrained QUBOs more naturally — a nice illustration that different quantum
paradigms suit different problems. Gate-model is limited to tiny grids here because
a statevector simulator costs 2^(qubits).

### Solver reliability — reported honestly (distribution over 15 seeds)

On the 3×4 route QUBO (exact optimum 61.71 t), every solver run with **15
independent seeds**, counting *every* run (no best-of, no selected seed):

| Solver | Hit optimum | Feasible | Mean gap | Worst gap |
|--------|:-----------:|:--------:|---------:|----------:|
| **neal** (annealing) | 15/15 | 15/15 | +0.0% | +0.0% |
| **GSA** (gravity, fair budget) | 15/15 | 15/15 | +0.0% | +0.0% |
| QAOA (gate-model) | 2/15 | 7/15 | +7.9% | +13.7% |
| VQE (gate-model) | 4/15 | 14/15 | +5.8% | +13.5% |

*Reproduce with* `py audit_seeds.py`.

**The honest finding:** on this constrained QUBO the classical solvers (neal, GSA,
Tabu) find the optimum on **every** seed, while gate-model **QAOA/VQE are
unreliable** — mean gap ~6–8% and they hit the optimum less than a third of the
time. That gap is real, but it must be read as a *distribution*, not a single run.

> **Correction / honesty note.** Earlier versions of this section published a
> single `--qseed 11` diagram showing QAOA/VQE at "+13.5%". That value is their
> **worst of 15 seeds** — cherry-picked to look dramatic, and it also gave GSA an
> unfair one-swarm budget that made it look broken. Both are corrected above with
> full-distribution reporting. Lesson kept in the repo on purpose: compare solvers
> over many seeds at equal budget, and report the spread.

---

## Phase 2d — a different optimizer family: Gravitational Search (GSA)

Every solver above is either *annealing* (SA/neal/D-Wave) or *gate-model*
(QAOA/VQE). **GSA** (Rashedi et al., 2009) is a third family — a **swarm
metaheuristic** where each candidate solution is a "mass" and better solutions
gravitationally attract the swarm (`F = G·M_i·M_j / R`). The gravitational
constant `G` shrinks over time, giving the same explore→exploit arc SA gets from
cooling. We added it in two forms:

- **Continuous GSA** (`gsa.gsa_minimize`) — GSA's natural domain, used on the
  **cruise-speed** problem (`gsa_speed.py`).
- **Binary GSA / BGSA** (`gsa.bgsa_qubo`, Rashedi 2010) — maps GSA to 0/1 space via
  a `|tanh(v)|` transfer function, so it solves the **QUBO** as a `--backend gsa`.

**Speed (continuous, GSA's home turf):** `py gsa_speed.py`

| Method | Speed (40 h) | Fuel | Speed (90 h) | Fuel |
|--------|-------------:|-----:|-------------:|-----:|
| **GSA** | 15.03 kn | 39.90 t | 8.40 kn | 18.27 t |
| Simulated annealing | 15.03 kn | 39.90 t | 8.40 kn | 18.27 t |
| Grid (exact) | 15.02 kn | 39.92 t | 8.39 kn | 18.29 t |

GSA **matches SA and the exact grid** on speed. The convergence plot
(`outputs/gsa_speed_*.png`) shows the swarm's mean fuel starting scattered (a
spike to ~85 t) then collapsing onto the optimum by ~iteration 20 as "gravity"
pulls the agents together.

**QUBO (binary) — the authoritative comparison is `benchmark.py`** (equal fixed
budget, many seeds, every run counted, mean ± std). Full results in
[`BENCHMARK.md`](BENCHMARK.md); the two studies (10 seeds each):

**Study A — reliability vs size** (`outputs/bench_size.png`), % optimal / mean gap:

| Vars | neal | tabu | GSA | QGSO |
|-----:|------|------|-----|------|
| 12 | 100% | 100% | 100% | 100% |
| 20 | 100% | 100% | 100% | 100% |
| 24 | 100% | 100% | 0%, +6.1% | **60%, +0.7%** |
| 30 | 100% | 100% | 0%, 70% feas, +17.0% | **0%, 100% feas, +3.5%** |
| 42 | 70%, +0.1% | 100% | fails (0% feas) | fails (0% feas) |

**Study B — penalty-weight sensitivity** (24 vars, `outputs/bench_penalty.png`), mean gap:

| Penalty P | neal | tabu | GSA | QGSO |
|----------:|------|------|-----|------|
| 1× | 100% | 100% | infeasible | **60% opt, +0.7%** |
| 2× | 100% | 100% | +3.7% | **+0.5%** |
| 3× | 100% | 100% | +6.3% | **+2.3%** |
| 5× | 100% | 100% | +4.4% | **+1.3%** |
| 10× | 100% | 100% | +6.1% | **+0.7%** |
| 20× | 100% | 100% | +7.4% | **+1.4%** |

![Reliability vs size](outputs/bench_size.png)
![Penalty sensitivity](outputs/bench_penalty.png)

**Honest finding:** **neal and tabu win outright** — optimal and penalty-invariant
at every size (only neal wobbles once, 70% optimal at 42 vars but still +0.1%).
Both **GSA and QGSO** degrade with size and collapse at 42 vars, and neither
matches the classical annealers. Gate-model QAOA/VQE (15-seed `audit_seeds.py`)
are unreliable even at 12 vars.

### Does the *quantum-inspired* twist help? QGSO vs GSA (`qgso.py`)

`qgso.py` implements **QGSO** — quantum-inspired GSA: each agent is a register of
**qubits** (angle θ, P(bit=1)=sin²θ) that live in superposition and are *measured*
each iteration; the gravitational pull drives a **quantum rotation gate** instead
of BGSA's bit-flip. Benchmarked at **identical budget** to GSA (same restarts,
agents, iterations — only the update rule differs):

![GSA vs QGSO](outputs/bench_gsa_vs_qgso.png)

**QGSO genuinely and consistently beats plain GSA** on this constrained QUBO:

- **Far less penalty-sensitive** — GSA's gap swings +3.7% → +7.4% across penalty
  weights and goes fully *infeasible* at P=1×; **QGSO stays within +0.5% → +2.3%
  and feasible at every P**, including P=1×. This is the clearest win — the
  superposition/rotation-gate update sidesteps the penalty knife-edge that wrecks
  BGSA.
- **More reliable at mid-size** — at 24 vars GSA is 0% optimal (+6.1%) vs QGSO
  60% optimal (+0.7%); at 30 vars GSA drops to 70% feasible (+17%) while QGSO
  holds 100% feasible (+3.5%).
- **But not a leap past the tier** — QGSO still trails neal/tabu (which are 0%
  everywhere), and it does *not* rescue the 42-var collapse (both fail). So the
  quantum-inspired twist is a real, measured improvement *within* the swarm-
  metaheuristic tier, not a jump past the classical winners.

This is the honest answer to "is QGSO any good?": **yes, meaningfully better than
the GSA it's built on — same compute, smoother and far more penalty-robust search —
but classical annealing still wins this problem.**

> **Honesty note (kept on purpose).** Earlier versions overstated GSA's weakness
> two ways: an **unfair budget** (one swarm vs neal's 200 reads) and a
> **cherry-picked worst-of-N** diagram (both GSA "+26%" and a QAOA/VQE "+13.5%"
> single-seed plot). All removed. The lesson, enforced by `benchmark.py`: equal
> budget, many seeds, report the spread — never a hand-picked run.

> **GSA vs QGSA?** We implemented **canonical GSA** first because it has one
> agreed definition (Rashedi 2009) and is the baseline any "quantum-inspired GSA"
> must beat. *Quantum GSA (QGSA)* is a classical algorithmic twist (quantum-inspired
> position updates), not real quantum hardware — a sensible *next* experiment once
> the GSA baseline is in place, but not a new hardware story like D-Wave/QAOA.

---

## Feasibility study — which solver to use, and why

We have **six** ways to solve the optimization, spanning exact / classical /
quantum. They are *not* interchangeable — each wins in a different regime. The
choice is driven by four questions: **how big is the problem, how hard are the
constraints, how reliable must the answer be, and what hardware can we access.**

### Measured head-to-head (`quantum_gate.py`, 5 trials each, same QUBO)

| Solver | Paradigm | Best fuel | Success rate | Time/run | Practical size ceiling |
|--------|----------|----------:|:------------:|---------:|------------------------|
| **neal** | Classical annealing (SA) | optimum | **5/5** speed, **5/5** route | **~0.05 s** | hundreds of vars (we run 275) |
| Tabu | Classical metaheuristic | optimum | reliable | ~0.1 s | hundreds of vars |
| GSA (fair budget) | Classical swarm (gravity) | optimum | 5/5 speed, 5/5 route ≤30 vars | ~25 s | competitive to ~35 vars, slips beyond |
| QAOA | Gate-model quantum | optimum | 3/5 speed, **0–2/5** route | ~3–9 s | ~16 qubits on a laptop sim |
| VQE | Gate-model quantum | optimum | 4/5 speed, **1/5** route | ~6–30 s | ~16 qubits on a laptop sim |
| NumPy eigensolver | Exact (brute force) | optimum | 1/1 | <0.05 s | ≤ ~18 vars (2ⁿ blow-up) |
| Exact DP | Exact (grid structure) | optimum | 1/1 | instant | any grid (route only) |

*Success rate = fraction of repeated runs that hit the exact optimum.* All solvers
*can* reach the optimum (best-of-N gap ≈ 0%); they differ in **reliability** and
**speed** — and that gap widens on the constraint-heavy route QUBO.

### Decision guide

| If you need… | Use | Why |
|--------------|-----|-----|
| The **production answer** at our real grid sizes (35–275 vars) | **neal** | fast, 100% reliable here, scales to hundreds of variables |
| To **validate** that the optimizer is correct | Exact **DP** (route) / **NumPy** (speed) | provably optimal reference |
| A classical **second opinion** | Tabu / GSA | different heuristics; GSA is also the native choice for the *continuous* speed problem |
| To optimize a **continuous** variable directly (speed) | **GSA** or SA | no discretization needed; GSA matches SA/grid on speed |
| To **demonstrate quantum portability** (gate-model) | QAOA / VQE on a *small* instance | the same QUBO runs on IBM-style hardware |
| Real **quantum annealing at scale** | D-Wave Advantage (`--backend dwave`) | 5000+ qubits can embed our 275-var QUBO — *needs paid/academic Leap access* |

### Scaling feasibility (why size decides the quantum question)

- **Our problem scale:** 5×7 = 35 binary vars; 11×25 = **275** binary vars.
- **Gate-model (QAOA/VQE):** one qubit per variable. On a laptop simulator the
  cost is 2ⁿ, so ~16–18 qubits is the ceiling. Real gate QPUs exist (IBM ~127+
  qubits) but are **noisy**, and deep QAOA on 275 *constrained* variables is **not
  feasible today**. Gate-model here is a *small-scale proof of portability*, not a
  production solver.
- **Quantum annealing (D-Wave):** Advantage has **5000+ qubits** with sparse
  connectivity; minor-embedding a 275-variable QUBO is feasible. So at our scale,
  **annealing is the only quantum route that is feasible today** — which is exactly
  why we formulated everything as a QUBO/Ising.
- **Classical annealing (neal):** solves 275 vars in well under a second at 100%
  reliability in our tests — **the practical choice right now**.

### Verdict

> **Today:** ship with **neal** (classical annealing on the QUBO); validate against
> **exact DP**. neal is the fastest *and* most reliable on these constrained fuel
> QUBOs. **Quantum is kept ready, not relied upon:** the identical QUBO runs on a
> real D-Wave annealer (one flag) if academic access is granted, and on gate-model
> QAOA/VQE for small instances. **As gate-model hardware matures** (more qubits,
> lower noise, error correction), QAOA/VQE become candidates for larger instances —
> and because the problem is already a QUBO, **no re-modelling is needed** to adopt
> them. That portability is the core design decision of this project.

---

## The story for the demo (30 seconds)

> *"We simulate Coast Guard voyage data from real naval-architecture physics —
> the cubic speed–power law. A gradient-boosting model rediscovers it from noisy
> data at R² ≈ 0.99. Then a quantum-inspired annealer recommends the slowest
> speed that still meets the mission deadline — cutting fuel up to ~30% on a tight
> schedule and far more when the schedule allows, with the CO₂ savings reported
> for IMO compliance. We verify the annealer found the true optimum against brute
> force."*

**Honest caveats** (good to state up front): the physics coefficients are
plausible but not calibrated to a specific vessel; data is synthetic; the QUBO is
solved on a *classical* annealer (`neal`), not real quantum hardware — but the
formulation is hardware-portable.

---

## Roadmap

- **Phase 1 — DONE:** synthetic ship data → fuel-rate model (R² ≈ 0.99) →
  slow-steaming SA optimizer with deadline + CO₂, one-command demo + plot.
- **Phase 2 — DONE:** genuine **QUBO** optimizers (PyQUBO + dwave-neal) for both
  speed (2a) and **weather routing** (2b), validated against brute force. The same
  QUBOs are portable to real D-Wave quantum hardware.
- **Phase 3 — Dashboard:** Streamlit UI — pick ship + conditions + voyage,
  see predicted fuel, click "Optimize", get the recommended speed/route + savings.

### Possible Phase 2+ extensions
- Multi-segment speed profile (a speed per leg under a total-time deadline).
- Joint speed **and** route optimization in one QUBO.
- Genetic-algorithm optimizer for a three-way comparison (SA vs GA vs QUBO).
- Retrain the model on a real public dataset (e.g. FuelCast) to show transfer.
