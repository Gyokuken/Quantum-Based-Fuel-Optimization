"""
oracle.py -- the EXACT voyage oracle (Phase 4, layer 1).

CONCEPT
-------
The fleet optimizer never routes a ship itself. Every time it wants to know
"what does it cost ship s to serve mission j departing origin o at slot t0?",
it asks THIS oracle, which answers with the PROVABLY OPTIMAL route + speed
profile under the moving weather field. That is the matheuristic design:
heuristic search outside, exact dynamic programming inside.

THE TIME-EXPANDED DP
--------------------
State: (row, col, slot). Action: move to one of 8 neighbour cells at one of
the ship's discrete speeds. A move takes round(dist/speed) slots (min 1) and
burns  rate(ship, conditions at destination at DEPARTURE slot, speed)
      x true_leg_hours / 24   tonnes  (fuel uses TRUE duration; only arrival
times are quantised). Because every action strictly advances time, the state
graph is a DAG ordered by t -- so a single forward sweep over slots computes
the exact minimum-fuel cost to EVERY (cell, slot) reachable from the origin.
No heap, no heuristic, no approximation at this layer.

The per-(class, slot, cell, speed) fuel RATES come from the Phase-1 ML model
(imported read-only from the parent project), evaluated in ONE batched
predict call and cached.

TABLES the fleet layer consumes
-------------------------------
  serve_fuel[o, j, t0, tf]  min fuel for: released at location o at slot t0,
                            sail to mission j's start (waiting at anchor is
                            free), START the leg within j's window, and be
                            FINISHED BY slot tf (cumulative-min over tf).

The 4th axis is the crucial one: it keeps the whole FUEL-vs-FINISH-TIME
Pareto frontier, because serving a mission slowly (cheap, finishes late) can
block the ship's next mission window. Collapsing to min-fuel-only makes many
good sequences look infeasible -- the Phase-1 fuel/time trade-off reappears
at fleet level, and the tables must carry it.
"""

from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd

import fleet_config as fc
import scenario as scen_mod

sys.path.insert(0, str(fc.PARENT_DIR))
import config as parent_config                      # read-only
import optimizer as parent_optimizer                # read-only (load_model)
import qubo_route as parent_qubo_route              # read-only (base_scenario_for)

INF = np.inf


# --------------------------------------------------------------------------- #
# Fuel-rate tables from the Phase-1 ML model (one batched predict)             #
# --------------------------------------------------------------------------- #
def build_rate_tables(scn: scen_mod.Scenario, pipe=None, verbose=True):
    """rates[class_name] = array [T, R, C, V] of fuel rates (tonnes/day)."""
    if pipe is None:
        pipe = parent_optimizer.load_model()
    T, R, C = scn.waves.shape
    classes = sorted({s.ship_class for s in scn.ships})
    speeds_by_class = {s.ship_class: s.speeds for s in scn.ships}

    frames = []
    for cls in classes:
        base = parent_qubo_route.base_scenario_for(cls)
        V = speeds_by_class[cls]
        # meshgrid of (t, r, c, v)
        tt, rr, cc, vv = np.meshgrid(np.arange(T), np.arange(R), np.arange(C),
                                     np.arange(len(V)), indexing="ij")
        w = scn.waves[tt, rr, cc].ravel()
        df = pd.DataFrame({
            "displacement_tonnes": base["displacement_tonnes"],
            "engine_power_kw": base["engine_power_kw"],
            "hull_coefficient": base["hull_coefficient"],
            "speed_knots": V[vv.ravel()],
            "wave_height_m": w,
            "wind_speed_kn": 5.0 + 6.0 * w,          # training correlation
            "current_speed_kn": scn.current_kn,
            "ship_type": base["ship_type"],
            "fuel_type": base["fuel_type"],
            "load_condition": base["load_condition"],
        })
        frames.append((cls, df, (T, R, C, len(V))))

    rates = {}
    t0 = time.perf_counter()
    for cls, df, shape in frames:
        pred = pipe.predict(df[parent_config.FEATURE_COLUMNS])
        rates[cls] = pred.reshape(shape)
    if verbose:
        n = sum(len(df) for _, df, _ in frames)
        print(f"  rate tables: {n:,} ML predictions in "
              f"{time.perf_counter() - t0:.1f}s")
    return rates


# --------------------------------------------------------------------------- #
# Time-expanded DP (exact reachability from one origin/slot)                   #
# --------------------------------------------------------------------------- #
def reach_dp(rates_cls, speeds, origin, t0, track=False):
    """Min-fuel to every (r, c, t) from `origin` at slot t0. Exact (DAG DP).

    rates_cls: [T, R, C, V] fuel rates for this ship class.
    Returns fuel[R, C, T]  (and backpointers if track=True).
    """
    T, R, C, V = rates_cls.shape
    fuel = np.full((R, C, T), INF)
    fuel[origin[0], origin[1], t0] = 0.0
    if track:
        # encode predecessor as (prev_r, prev_c, prev_t) int16 arrays
        prev = np.full((R, C, T, 3), -1, dtype=np.int16)

    # Pre-compute per-move slot-costs: dt[move, v], hours[move, v]
    dts, hrs = [], []
    for (dr, dc, dist) in fc.MOVES:
        h = dist / speeds                            # true hours per speed
        dt = np.maximum(1, np.round(h / fc.SLOT_HOURS).astype(int))
        dts.append(dt)
        hrs.append(h)

    for t in range(t0, T - 1):
        layer = fuel[:, :, t]
        if not np.isfinite(layer).any():
            continue
        for mi, (dr, dc, dist) in enumerate(fc.MOVES):
            # source block -> destination block (vectorised shift)
            src_r = slice(max(0, -dr), R - max(0, dr))
            src_c = slice(max(0, -dc), C - max(0, dc))
            dst_r = slice(max(0, dr), R + min(0, dr))
            dst_c = slice(max(0, dc), C + min(0, dc))
            src = layer[src_r, src_c]
            if not np.isfinite(src).any():
                continue
            for v in range(V):
                t2 = t + dts[mi][v]
                if t2 >= T:
                    continue
                # leg fuel from conditions at DESTINATION cell, DEPARTURE slot
                leg = rates_cls[t, dst_r, dst_c, v] * (hrs[mi][v] / 24.0)
                cand = src + leg
                dest = fuel[dst_r, dst_c, t2]
                better = cand < dest
                if better.any():
                    dest[better] = cand[better]
                    fuel[dst_r, dst_c, t2] = dest
                    if track:
                        blk = prev[dst_r, dst_c, t2]
                        rr, cc = np.nonzero(better)
                        # convert block-relative indices to absolute
                        abs_r = rr + (dst_r.start or 0)
                        abs_c = cc + (dst_c.start or 0)
                        blk[rr, cc, 0] = abs_r - dr
                        blk[rr, cc, 1] = abs_c - dc
                        blk[rr, cc, 2] = t
                        prev[dst_r, dst_c, t2] = blk

    return (fuel, prev) if track else fuel


def trace_path(prev, cell, t):
    """Reconstruct [(r, c, t), ...] from backpointers, origin first."""
    path = [(cell[0], cell[1], t)]
    r, c = cell
    while True:
        pr, pc, pt = prev[r, c, t]
        if pr < 0:
            break
        path.append((int(pr), int(pc), int(pt)))
        r, c, t = int(pr), int(pc), int(pt)
    return path[::-1]


# --------------------------------------------------------------------------- #
# Serve tables: cost[origin_loc, mission, departure_slot]                      #
# --------------------------------------------------------------------------- #
def build_serve_tables(scn: scen_mod.Scenario, rates, verbose=True):
    """For every ship class: serve_fuel / serve_finish [n_locs, M, T].

    serve(o, j, t0) = min fuel to: be released at location o at slot t0,
    optionally WAIT at anchor (free -- stations only), sail to S_j, wait at
    S_j if early, start the patrol leg within [es, ls], sail it optimally.

    Exactness: for each origin we run one single-departure DP per departure
    slot t_dep; free waiting at the origin is then the exact suffix-min over
    t_dep >= t0. Free waiting at S_j is the cumulative-min over arrival slots.
    The mission leg is its own DP per start slot. All three pieces are exact,
    so the fold is exact.

    Origins are only locations ships can actually be released from: their
    home ports and mission END points (never mission starts).
    """
    T, R, C = scn.waves.shape
    locs = scn.locations()
    n_locs, M = len(locs), len(scn.missions)
    K = len(scn.ships)
    origin_ids = list(range(K)) + [scn.end_loc(j) for j in range(M)]
    classes = sorted({s.ship_class for s in scn.ships})
    speeds_by_class = {s.ship_class: s.speeds for s in scn.ships}

    tables = {}
    t_start = time.perf_counter()
    for cls in classes:
        rc = rates[cls]
        speeds = speeds_by_class[cls]

        # ---- mission-leg Pareto table: mleg[j, ts, tf] -------------------- #
        # min fuel to fly leg j starting exactly at ts and be DONE BY tf
        mleg = np.full((M, T, T), INF)
        for j, m in enumerate(scn.missions):
            for ts in range(m.es, min(m.ls, T - 2) + 1):
                f = reach_dp(rc, speeds, m.start, ts)
                arr = np.where(np.isfinite(f[m.end[0], m.end[1], :]),
                               f[m.end[0], m.end[1], :], INF)
                mleg[j, ts] = np.minimum.accumulate(arr)   # done-by fold

        # ---- positioning + exact double fold -> serve[o, j, t0, tf] ------- #
        sfuel = np.full((n_locs, M, T, T), np.float32(INF), dtype=np.float32)
        for o in origin_ids:
            ocell = locs[o]
            # B[j, t_dep, ts]: min fuel sitting at S_j at slot ts having
            # departed o exactly at t_dep (cum-min over arrivals <= ts).
            B = np.full((M, T, T), INF)
            for t_dep in range(T - 1):
                f = reach_dp(rc, speeds, ocell, t_dep)
                for j, m in enumerate(scn.missions):
                    arr = np.where(np.isfinite(f[m.start[0], m.start[1], :]),
                                   f[m.start[0], m.start[1], :], INF)
                    B[j, t_dep] = np.minimum.accumulate(arr)
            # free wait at origin: departing later is always allowed
            Bsuf = np.minimum.accumulate(B[:, ::-1, :], axis=1)[:, ::-1, :]
            for j, m in enumerate(scn.missions):
                ts_lo, ts_hi = m.es, min(m.ls, T - 2)
                if ts_hi < ts_lo:
                    continue
                # serve[t0, tf] = min over ts of Bsuf[j, t0, ts] + mleg[j, ts, tf]
                pos = Bsuf[j, :, ts_lo:ts_hi + 1]          # [T, W]
                leg = mleg[j, ts_lo:ts_hi + 1, :]          # [W, T]
                tot = pos[:, :, None] + leg[None, :, :]    # [T, W, T]
                sfuel[o, j] = tot.min(axis=1).astype(np.float32)

        tables[cls] = {"serve_fuel": sfuel}
        if verbose:
            print(f"  serve tables [{cls}]: {len(origin_ids)} origins x "
                  f"{M} missions x {T} slots  "
                  f"({time.perf_counter() - t_start:.1f}s cumulative)")
    return tables


# --------------------------------------------------------------------------- #
# Cache wrapper                                                                #
# --------------------------------------------------------------------------- #
def get_tables(scn: scen_mod.Scenario, verbose=True):
    """Build (or load cached) serve tables for a scenario."""
    fc.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    cache = (fc.OUTPUTS_DIR /
             f"tables_seed{scn.seed}_{scen_mod.scenario_hash(scn)}.npz")
    classes = sorted({s.ship_class for s in scn.ships})
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        try:
            tables = {cls: {"serve_fuel": z[f"{cls}__serve_fuel"]}
                      for cls in classes}
            if verbose:
                print(f"  loaded cached tables -> {cache.name}")
            return tables
        except KeyError:
            pass

    rates = build_rate_tables(scn, verbose=verbose)
    tables = build_serve_tables(scn, rates, verbose=verbose)
    flat = {f"{cls}__serve_fuel": tb["serve_fuel"]
            for cls, tb in tables.items()}
    np.savez_compressed(cache, **flat)
    if verbose:
        print(f"  cached -> {cache.name}")
    return tables


if __name__ == "__main__":
    scn = scen_mod.build_scenario(0)
    tabs = get_tables(scn)
    T = scn.waves.shape[0]
    # sanity: unconstrained min fuel (t0=0, finish by horizon) per ship/mission
    for j, m in enumerate(scn.missions):
        feas = []
        for s in scn.ships:
            f = tabs[s.ship_class]["serve_fuel"][scn.home_loc(s.id), j, 0, T - 1]
            feas.append(f"{s.name}:{f:.1f}t" if np.isfinite(f) else
                        f"{s.name}:INF")
        print(f"  {m.name} from home@0 (finish free): " + "  ".join(feas))
