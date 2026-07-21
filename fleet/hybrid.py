"""
hybrid.py -- the QUANTUM-CLASSICAL HYBRID optimizer (Phase 5).

Same two-layer architecture as the ALNS matheuristic, but the OUTER combinatorial
decision is made by a QUBO (quantum-portable) instead of a classical search:

    OUTER  (this file)  : a QUBO decides WHICH SHIP GETS WHICH MISSIONS.
                          Solved with neal now; the identical QUBO runs on a real
                          quantum annealer / QAOA by swapping the backend.
    INNER  (oracle.py + matheuristic.Evaluator, unchanged) : for any assignment,
                          the EXACT cheapest ordering + route + speed + timing.

Why a QUBO can only do the ASSIGNMENT (not the whole plan): a QUBO objective is
pairwise (quadratic), but a ship's true bundle cost is STATEFUL -- it depends on
the order, weather, and timing of the whole chain. So the QUBO uses solo + exact
PAIRWISE costs as an approximation; the quantum sampler returns many candidate
assignments; and the classical oracle then scores each EXACTLY (best ordering per
ship) and keeps the real winner. Quantum proposes, classical verifies.

This is the honest way to employ a quantum technique here: it plugs in at the one
layer that is naturally a QUBO, and its result is judged by the same exact
evaluator the ALNS version uses -- a fair, apples-to-apples comparison.
"""

from __future__ import annotations

import itertools

import neal
import numpy as np

import matheuristic as mh
import scenario as scen_mod

INF = float("inf")


# --------------------------------------------------------------------------- #
# Exact per-ship bundle cost (best ordering) -- the inner oracle's evaluation  #
# --------------------------------------------------------------------------- #
def best_bundle(ev: mh.Evaluator, ship: scen_mod.Ship, missions):
    """(fuel, best_ordering) for a ship serving an UNORDERED set of missions,
    optimally ordered. Small bundles are enumerated exactly; large ones fall
    back to greedy insertion (rare -- a ship rarely holds >7 missions)."""
    missions = tuple(missions)
    if not missions:
        return 0.0, ()
    if len(missions) <= 7:
        best, arg = INF, None
        for perm in itertools.permutations(missions):
            f, _ = ev.ship_cost(ship, perm)
            if f < best:
                best, arg = f, perm
        return best, (arg or ())
    # greedy-insertion fallback for big bundles
    seq = []
    for j in missions:
        best, pos = INF, 0
        for p in range(len(seq) + 1):
            f, _ = ev.ship_cost(ship, tuple(seq[:p] + [j] + seq[p:]))
            if f < best:
                best, pos = f, p
        seq.insert(pos, j)
    f, _ = ev.ship_cost(ship, tuple(seq))
    return f, tuple(seq)


# --------------------------------------------------------------------------- #
# Build the assignment QUBO                                                    #
# --------------------------------------------------------------------------- #
def build_assignment_qubo(ev: mh.Evaluator, penalty=None):
    """Binary x[s,j] = ship s serves mission j.

    objective   = sum_sj  solo[s,j] x[s,j]                       (solo costs)
                + sum_s sum_{j<k} extra[s,j,k] x[s,j] x[s,k]      (exact pair extra)
    constraint  = P * sum_j ( sum_s x[s,j] - 1 )^2               (each mission once)
    """
    scn = ev.scn
    K, M = len(scn.ships), len(scn.missions)

    solo = np.full((K, M), INF)
    for si, s in enumerate(scn.ships):
        for j in range(M):
            solo[si, j] = ev.ship_cost(s, (j,))[0]

    finite = solo[np.isfinite(solo)]
    if penalty is None:
        penalty = 5.0 * (float(finite.max()) * M if finite.size else 100.0)

    qubo: dict[tuple[str, str], float] = {}

    def add(a, b, c):
        key = (a, b) if a <= b else (b, a)
        qubo[key] = qubo.get(key, 0.0) + c

    # solo (linear) -- infeasible ship/mission gets a big positive cost (avoided)
    for si in range(K):
        for j in range(M):
            v = f"x_{si}_{j}"
            add(v, v, float(solo[si, j]) if np.isfinite(solo[si, j])
                else 3.0 * penalty)

    # exact pairwise bundle interaction on the same ship. An INFEASIBLE pair
    # (the two missions cannot both be served by this ship) gets a big penalty
    # so the QUBO avoids co-assigning them. (Higher-order overloads -- a bundle
    # of 3+ that is jointly infeasible while every pair is fine -- are invisible
    # to a pairwise QUBO; those are handled by classical repair after sampling.)
    for si, s in enumerate(scn.ships):
        for j in range(M):
            for k in range(j + 1, M):
                if np.isfinite(solo[si, j]) and np.isfinite(solo[si, k]):
                    fb, _ = best_bundle(ev, s, (j, k))
                    extra = (fb - solo[si, j] - solo[si, k]
                             if np.isfinite(fb) else penalty)
                    add(f"x_{si}_{j}", f"x_{si}_{k}", float(extra))

    # one-hot per mission: P*(sum_s x - 1)^2 -> linear -P each, quadratic +2P pairs
    for j in range(M):
        vs = [f"x_{si}_{j}" for si in range(K)]
        for v in vs:
            add(v, v, -penalty)
        for a in range(K):
            for b in range(a + 1, K):
                add(vs[a], vs[b], 2.0 * penalty)

    return qubo, solo, penalty


# --------------------------------------------------------------------------- #
# Decode + exact score                                                         #
# --------------------------------------------------------------------------- #
def decode_assignment(sample, ev: mh.Evaluator):
    """Turn a QUBO sample into a valid COMPLETE assignment {ship_id: [missions]}.
    Missions left unassigned or double-assigned are repaired to the cheapest
    feasible solo ship (classical repair of the quantum proposal)."""
    scn = ev.scn
    K, M = len(scn.ships), len(scn.missions)
    assign = {s.id: [] for s in scn.ships}
    for j in range(M):
        chosen = [si for si in range(K) if sample.get(f"x_{si}_{j}", 0) == 1]
        if len(chosen) == 1:
            si = chosen[0]
        else:
            cands = sorted((ev.ship_cost(scn.ships[si], (j,))[0], si)
                           for si in range(K))
            si = cands[0][1]
        assign[scn.ships[si].id].append(j)
    return assign


def _feasible(ev, assign):
    return all(best_bundle(ev, s, assign[s.id])[0] < INF for s in ev.scn.ships)


def exact_score(ev: mh.Evaluator, assign):
    """Exact total fuel + ordered plan. If a ship's bundle is time-INFEASIBLE
    (the QUBO overloaded it), REPAIR minimally: repeatedly move one mission off
    an infeasible ship to the cheapest feasible other ship, until feasible.
    This is the classical half of 'quantum proposes, classical repairs+scores'."""
    assign = {s.id: list(assign[s.id]) for s in ev.scn.ships}
    ships = ev.scn.ships
    for _ in range(4 * len(ev.scn.missions) + 1):
        bad = next((s for s in ships
                    if best_bundle(ev, s, assign[s.id])[0] == INF), None)
        if bad is None:
            break
        # cheapest feasible relocation of one mission off the overloaded ship
        best, mv = INF, None
        for j in list(assign[bad.id]):
            rest = [x for x in assign[bad.id] if x != j]
            fr, _ = best_bundle(ev, bad, rest)
            for s2 in ships:
                if s2.id == bad.id:
                    continue
                f2, _ = best_bundle(ev, s2, assign[s2.id] + [j])
                if f2 < INF and fr < INF and f2 + fr < best:
                    best, mv = f2 + fr, (j, s2.id, rest)
        if mv is None:
            return INF, None
        j, s2id, rest = mv
        assign[bad.id] = rest
        assign[s2id].append(j)
    else:
        return INF, None

    plan, tot = {}, 0.0
    for s in ships:
        f, order = best_bundle(ev, s, assign[s.id])
        if f == INF:
            return INF, None
        plan[s.id] = list(order)
        tot += f
    return tot, plan


# --------------------------------------------------------------------------- #
# The hybrid solver                                                            #
# --------------------------------------------------------------------------- #
def solve_hybrid(ev: mh.Evaluator, num_reads=200, topk=25, seed=0,
                 sampler=None):
    """QUBO (quantum-portable) proposes assignments; oracle scores them exactly.

    `sampler` defaults to neal; pass any dimod-style sampler (e.g. a real
    D-Wave/QAOA sampler) to run the SAME QUBO on quantum hardware.
    Returns (best_plan, best_fuel, info).
    """
    qubo, solo, P = build_assignment_qubo(ev)
    if sampler is None:
        sampler = neal.SimulatedAnnealingSampler()
    ss = sampler.sample_qubo(qubo, num_reads=num_reads, seed=seed)

    best_plan, best_f, scored, seen = None, INF, 0, set()
    for rec in ss.data(["sample", "energy"], sorted_by="energy"):
        assign = decode_assignment(rec.sample, ev)
        key = tuple(tuple(sorted(assign[s.id])) for s in ev.scn.ships)
        if key in seen:
            continue
        seen.add(key)
        f, plan = exact_score(ev, assign)
        if f < best_f:
            best_f, best_plan = f, plan
        scored += 1
        if scored >= topk:
            break
    info = {"n_qubo_vars": len(ev.scn.ships) * len(ev.scn.missions),
            "penalty": P, "assignments_scored": scored}
    return best_plan, best_f, info


def solve_random_baseline(ev: mh.Evaluator, n_samples=25, seed=0):
    """ABLATION: identical exact scoring as the hybrid, but assignments are
    drawn UNIFORMLY AT RANDOM instead of from the QUBO. If this matches the
    hybrid, the QUBO is NOT adding value at this scale -- the decomposition
    (exact per-ship ordering + small assignment space) is doing the work.
    This is the honest control that isolates the quantum layer's contribution."""
    rng = np.random.default_rng(seed)
    scn = ev.scn
    K, M = len(scn.ships), len(scn.missions)
    best_plan, best_f, seen, tries = None, INF, set(), 0
    while len(seen) < n_samples and tries < n_samples * 30:
        tries += 1
        assign = {s.id: [] for s in scn.ships}
        for j in range(M):
            assign[scn.ships[int(rng.integers(K))].id].append(j)
        key = tuple(tuple(sorted(assign[s.id])) for s in scn.ships)
        if key in seen:
            continue
        seen.add(key)
        f, plan = exact_score(ev, assign)
        if f < best_f:
            best_f, best_plan = f, plan
    return best_plan, best_f


if __name__ == "__main__":
    import oracle
    scn = scen_mod.build_scenario(0)
    tabs = oracle.get_tables(scn, verbose=False)
    ev = mh.Evaluator(scn, tabs)
    plan, f, info = solve_hybrid(ev, num_reads=200, seed=1)
    pe, fe, _ = mh.exhaustive(ev)
    print(f"hybrid (QUBO+oracle): {f:.2f} t   "
          f"({info['n_qubo_vars']} QUBO vars, "
          f"{info['assignments_scored']} assignments scored exactly)")
    print(f"exhaustive optimum  : {fe:.2f} t   gap {(f-fe)/fe*100:+.2f}%")
    if plan is not None:
        print(mh.describe_plan(ev, plan))
    else:
        print("  (no feasible assignment found)")
