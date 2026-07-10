"""
qubo_layer.py -- the fleet dispatch problem as a QUBO (quantum comparison).

WHY THIS LAYER EXISTS
---------------------
The outer fleet problem (assignment + sequencing) is the level where a QUBO
is natural: discrete choices, genuine combinatorial explosion, variable
counts (~50-150) far beyond brute force yet inside annealer reach. This is
the honest quantum entry point for the project -- unlike the flat 275-var
route QUBO of Phase 2 (which DP solves exactly) or the 16-qubit gate ceiling.

TWO ENCODINGS WERE TRIED (kept in the docstring as findings):
  1. DISPATCH (mission x ship x release-slot). FAILS STRUCTURALLY here: it
     is location-stateless -- every serve is priced from the ship's HOME
     port, but second-wave missions are only reachable from a FIRST
     mission's end point, so full coverage is not even representable and
     the one-hot collapses (observed: annealer drops missions rather than
     pay conflict penalties). Also cannot carry the fuel-vs-finish Pareto
     trade-off inside one binary variable.
  2. POSITION-INDEXED (this file, TSP-style a la Lucas 2014):
     x[j, s, p] = 1  <=>  mission j is the p-th mission ship s serves.
     Chaining cost lives on QUADRATIC terms between consecutive positions,
     priced from the oracle's exact tables (end-location of the predecessor,
     released at its earliest feasible finish). Sequencing becomes
     REPRESENTABLE; timing remains approximate (a single release estimate
     per predecessor), so the decoded plan still gets an exact re-evaluation.

Hamiltonian
-----------
  H = sum_j,s   cost1[j,s]        x[j,s,1]                (first legs, exact)
    + sum_j,k,s chain[j,k,s]      x[j,s,p] x[k,s,p+1]     (chained legs)
    + P  * (each mission in exactly one slot)             (one-hot)
    + P  * (at most one mission per (ship, position))
    + P  * (no orphan positions: p+1 filled => p filled)
    + 3P * (infeasible chains forbidden)

The decoded ASSIGNMENT+ORDER is then re-evaluated EXACTLY by the Evaluator
(which resolves true timing via the Pareto tables); infeasible decodes are
reported as such. The gap between this baseline and the matheuristic is the
measured price of forcing a stateful sequencing problem into a flat QUBO.
"""

from __future__ import annotations

import sys

import numpy as np

import fleet_config as fc
import matheuristic as mh
import scenario as scen_mod

sys.path.insert(0, str(fc.PARENT_DIR))
import backends                                      # read-only (neal/tabu)

INF = float("inf")


def _first_leg_stats(scn, tables):
    """cost1[j, s] and earliest-feasible finish efin1[j, s] from home @ 0."""
    M, K = len(scn.missions), len(scn.ships)
    cost1 = np.full((M, K), INF)
    efin1 = np.full((M, K), -1, dtype=int)
    for s in scn.ships:
        sf = tables[s.ship_class]["serve_fuel"]
        home = scn.home_loc(s.id)
        for j in range(M):
            vec = sf[home, j, 0, :]
            finite = np.isfinite(vec)
            if finite.any():
                cost1[j, s.id] = float(vec[finite].min())
                efin1[j, s.id] = int(np.argmax(finite))
    return cost1, efin1


def _chain_stats(scn, tables, efin1):
    """chain[j, k, s]: min fuel to serve k from end(j), released at j's
    earliest feasible finish (approximation -- documented); INF if impossible."""
    M, K = len(scn.missions), len(scn.ships)
    T = scn.waves.shape[0]
    chain = np.full((M, M, K), INF)
    for s in scn.ships:
        sf = tables[s.ship_class]["serve_fuel"]
        for j in range(M):
            t_rel = efin1[j, s.id]
            if t_rel < 0 or t_rel >= T - 1:
                continue
            oloc = scn.end_loc(j)
            for k in range(M):
                if k == j:
                    continue
                vec = sf[oloc, k, t_rel, :]
                finite = np.isfinite(vec)
                if finite.any():
                    chain[j, k, s.id] = float(vec[finite].min())
    return chain


def build_position_qubo(scn, tables, max_pos=3, penalty_mult=3.0):
    """Position-indexed QUBO. Returns (qubo, var->key map, info)."""
    M, K = len(scn.missions), len(scn.ships)
    cost1, efin1 = _first_leg_stats(scn, tables)
    chain = _chain_stats(scn, tables, efin1)

    finite_costs = [c for c in cost1.ravel() if np.isfinite(c)]
    finite_costs += [c for c in chain.ravel() if np.isfinite(c)]
    cmax = max(finite_costs) if finite_costs else 1.0
    P = penalty_mult * cmax * max_pos

    # variables: (j, s, p) -- p=0 first position. Skip provably useless vars
    # (p=0 with INF first-leg cost).
    keys = []
    for j in range(M):
        for s in range(K):
            if np.isfinite(cost1[j, s]):
                keys.append((j, s, 0))
            for p in range(1, max_pos):
                keys.append((j, s, p))
    name = {k: f"x_{k[0]}_{k[1]}_{k[2]}" for k in keys}
    kset = set(keys)
    qubo = {}

    def add(a, b, v):
        key = (a, b) if a <= b else (b, a)
        qubo[key] = qubo.get(key, 0.0) + v

    # one-hot per mission: P(sum x - 1)^2
    for j in range(M):
        group = [k for k in keys if k[0] == j]
        for k in group:
            add(name[k], name[k], -P)
        for a in range(len(group)):
            for b in range(a + 1, len(group)):
                add(name[group[a]], name[group[b]], 2.0 * P)

    # at most one mission per (ship, position)
    for s in range(K):
        for p in range(max_pos):
            group = [k for k in keys if k[1] == s and k[2] == p]
            for a in range(len(group)):
                for b in range(a + 1, len(group)):
                    add(name[group[a]], name[group[b]], 2.0 * P)

    # first-leg costs
    for (j, s, p) in keys:
        if p == 0:
            add(name[(j, s, 0)], name[(j, s, 0)], cost1[j, s])

    # stacking + chained costs between consecutive positions
    for s in range(K):
        for p in range(1, max_pos):
            here = [k for k in keys if k[1] == s and k[2] == p]
            prev = [k for k in keys if k[1] == s and k[2] == p - 1]
            for k2 in here:
                add(name[k2], name[k2], P)           # orphan penalty ...
                for k1 in prev:
                    j1, j2 = k1[0], k2[0]
                    if j1 == j2:
                        continue
                    c = chain[j1, j2, s]
                    if np.isfinite(c):
                        # ... cancelled by a real predecessor, plus true cost
                        add(name[k1], name[k2], c - P)
                    else:
                        add(name[k1], name[k2], 2.0 * P)   # forbidden chain

    info = {"n_vars": len(keys), "n_terms": len(qubo), "penalty": P,
            "max_pos": max_pos, "offset": P * M}
    return qubo, {v: k for k, v in name.items()}, info


def solve_fleet_qubo(scn, tables, ev: mh.Evaluator, num_reads=1000,
                     backend="neal", seed=42, max_pos=3):
    """Solve the position QUBO, decode, exact re-evaluation. Honest output."""
    qubo, rev, info = build_position_qubo(scn, tables, max_pos=max_pos)
    sampler, label, _ = backends.make_sampler(backend)
    ss = backends.sample_qubo(sampler, backend, qubo, num_reads=num_reads,
                              seed=seed)
    best = ss.first.sample

    chosen = [rev[v] for v, val in best.items() if val == 1 and v in rev]
    seen = {}
    for (j, s, p) in chosen:
        seen.setdefault(j, []).append((s, p))
    M = len(scn.missions)
    if len(seen) != M or any(len(v) != 1 for v in seen.values()):
        return {"feasible": False, "true_fuel": INF, "info": info,
                "label": label, "reason": "one-hot violated"}

    plan = {s.id: [] for s in scn.ships}
    for j in range(M):
        s, p = seen[j][0]
        plan[s].append((p, j))
    for sid in plan:
        seq = sorted(plan[sid])
        # orphan check: positions must be contiguous from 0
        if [p for p, _ in seq] != list(range(len(seq))):
            return {"feasible": False, "true_fuel": INF, "info": info,
                    "label": label, "reason": "orphan position"}
        plan[sid] = [j for _, j in seq]

    raw_fuel = ev.total(plan)
    raw_feasible = bool(np.isfinite(raw_fuel))

    # ---- light exact repair (standard practice for QUBO decodes) ---------- #
    # The pairwise chain terms price a position-p release with a position-1
    # finish estimate, so deep chains can be timing-infeasible in truth.
    # Repair 1: exact best permutation per ship. Repair 2: greedily relocate
    # missions off any still-infeasible ship. How much repair the QUBO needs
    # is itself a reported finding.
    import itertools
    ships_by_id = {s.id: s for s in scn.ships}
    if not raw_feasible:
        for sid, seq in plan.items():
            if len(seq) >= 2:
                bf, bp = INF, seq
                for perm in itertools.permutations(seq):
                    f, _ = ev.ship_cost(ships_by_id[sid], perm)
                    if f < bf:
                        bf, bp = f, list(perm)
                plan[sid] = bp
    if not np.isfinite(ev.total(plan)):
        moved = True
        while moved and not np.isfinite(ev.total(plan)):
            moved = False
            for sid in list(plan.keys()):
                f, _ = ev.ship_cost(ships_by_id[sid], tuple(plan[sid]))
                if f < INF or not plan[sid]:
                    continue
                j = plan[sid].pop()                 # take last mission off
                best, arg = INF, None
                for s2 in scn.ships:
                    for pos in range(len(plan[s2.id]) + 1):
                        cand = plan[s2.id][:pos] + [j] + plan[s2.id][pos:]
                        cf, _ = ev.ship_cost(s2, tuple(cand))
                        if cf < INF:
                            base, _ = ev.ship_cost(s2, tuple(plan[s2.id]))
                            d = cf - (0.0 if base == INF else base)
                            if d < best:
                                best, arg = d, (s2.id, pos)
                if arg is None:
                    plan[sid].append(j)             # give up on this one
                else:
                    plan[arg[0]].insert(arg[1], j)
                    moved = True

    true_fuel = ev.total(plan)
    return {"feasible": bool(np.isfinite(true_fuel)), "plan": plan,
            "true_fuel": float(true_fuel), "raw_feasible": raw_feasible,
            "raw_fuel": (float(raw_fuel) if raw_feasible else INF),
            "info": info, "label": label,
            "reason": "ok" if raw_feasible else
                      ("repaired" if np.isfinite(true_fuel) else
                       "unrepairable")}
