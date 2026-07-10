"""
scenario.py -- synthetic FLEET scenario generator (Phase 4).

Generates, from one seed, a complete deterministic fleet instance:

  * a MOVING weather field  waves[t, r, c]  (storms drift + grow/decay),
    kept inside the ranges the Phase-1 ML model was trained on
    (waves clipped to 0-8 m; wind = 5 + 6 x waves, the training correlation);
  * K ship instances (one per ICG class by default) stationed at ports;
  * M missions: patrol legs "sail from S to E, STARTING within [es, ls]".

The schema deliberately mirrors what real Coast Guard data would look like
(a vessel list, a tasking list with time windows, a gridded forecast), so
synthetic data can later be swapped for real data without redesigning anything.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

import numpy as np

import fleet_config as fc

sys.path.insert(0, str(fc.PARENT_DIR))
import config as parent_config                      # read-only import


# --------------------------------------------------------------------------- #
# Data classes                                                                 #
# --------------------------------------------------------------------------- #
@dataclass
class Ship:
    id: int
    name: str
    ship_class: str                 # key into parent config.SHIP_SPECS
    home: tuple[int, int]           # (row, col) port cell
    speeds: np.ndarray              # discrete cruise speeds (kn)


@dataclass
class Mission:
    id: int
    name: str
    start: tuple[int, int]          # S: where the patrol leg begins
    end: tuple[int, int]            # E: where it ends
    es: int                         # earliest START slot
    ls: int                         # latest START slot


@dataclass
class Scenario:
    seed: int
    waves: np.ndarray               # [T, R, C] metres
    current_kn: float               # region-wide current (scalar, v1)
    ships: list[Ship] = field(default_factory=list)
    missions: list[Mission] = field(default_factory=list)

    # location registry: 0..K-1 ship homes, then mission starts, then ends
    def locations(self) -> list[tuple[int, int]]:
        locs = [s.home for s in self.ships]
        locs += [m.start for m in self.missions]
        locs += [m.end for m in self.missions]
        return locs

    def home_loc(self, ship_idx: int) -> int:
        return ship_idx

    def start_loc(self, mission_idx: int) -> int:
        return len(self.ships) + mission_idx

    def end_loc(self, mission_idx: int) -> int:
        return len(self.ships) + len(self.missions) + mission_idx


# --------------------------------------------------------------------------- #
# Weather: drifting Gaussian storms                                            #
# --------------------------------------------------------------------------- #
def build_moving_weather(rng, T=fc.HORIZON_SLOTS, R=fc.N_ROWS, C=fc.N_COLS,
                         n_storms=3):
    """waves[t, r, c]: calm baseline + drifting/evolving Gaussian storms.
    Storm centres move with a constant drift velocity; amplitude follows a
    grow-then-decay envelope. Clipped to the model's trained range [0, 8] m."""
    rows = np.arange(R)[:, None]
    cols = np.arange(C)[None, :]
    waves = np.full((T, R, C), 1.0)

    for _ in range(n_storms):
        r0 = rng.uniform(0, R - 1)
        c0 = rng.uniform(2, C - 3)
        amp0 = rng.uniform(4.0, 6.5)
        sr = rng.uniform(1.2, 2.2)
        sc = rng.uniform(1.2, 2.5)
        drift_r = rng.uniform(-0.08, 0.08)          # cells per slot
        drift_c = rng.uniform(-0.12, 0.12)
        peak_t = rng.uniform(0.2, 0.8) * T          # when the storm peaks
        width_t = rng.uniform(0.35, 0.7) * T

        for t in range(T):
            rc = r0 + drift_r * t
            cc = c0 + drift_c * t
            envelope = np.exp(-((t - peak_t) ** 2) / (2 * width_t ** 2))
            waves[t] += (amp0 * envelope *
                         np.exp(-(((rows - rc) ** 2) / (2 * sr ** 2)
                                  + ((cols - cc) ** 2) / (2 * sc ** 2))))

    return np.clip(waves, 0.0, 8.0)


# --------------------------------------------------------------------------- #
# Instance generation                                                          #
# --------------------------------------------------------------------------- #
_CLASS_CYCLE = ["Offshore_Patrol", "Fast_Patrol", "Interceptor"]


def _class_speeds(ship_class: str) -> np.ndarray:
    spec = parent_config.SHIP_SPECS[ship_class]
    top = float(spec["service_speed"])
    return np.linspace(fc.MIN_FLEET_SPEED, top, fc.N_SPEEDS)


def build_scenario(seed: int, n_ships=fc.DEFAULT_N_SHIPS,
                   n_missions=fc.DEFAULT_N_MISSIONS, n_storms=3) -> Scenario:
    rng = np.random.default_rng(seed)
    waves = build_moving_weather(rng, n_storms=n_storms)
    current = float(np.clip(rng.normal(0.0, 1.0), -2.0, 2.0))

    # Ships: stationed on the west edge (ports), classes cycled.
    ships = []
    port_rows = rng.choice(fc.N_ROWS, size=n_ships, replace=False)
    for i in range(n_ships):
        cls = _CLASS_CYCLE[i % len(_CLASS_CYCLE)]
        ships.append(Ship(id=i, name=f"{cls[:3]}-{i}", ship_class=cls,
                          home=(int(port_rows[i]), 0),
                          speeds=_class_speeds(cls)))

    # Missions: patrol legs across the interior. Start windows are STAGGERED
    # in "waves" across the horizon (real taskings are spread over a day; and
    # a fleet of K ships physically cannot serve 2K simultaneous windows --
    # clustering all windows mid-horizon makes instances infeasible).
    missions = []
    n_waves = max(1, int(np.ceil(n_missions / n_ships)))
    wave_span = (fc.HORIZON_SLOTS - 14) / n_waves
    for j in range(n_missions):
        sr = int(rng.integers(0, fc.N_ROWS))
        sc = int(rng.integers(4, fc.N_COLS - 6))
        er = int(np.clip(sr + rng.integers(-3, 4), 0, fc.N_ROWS - 1))
        ec = int(np.clip(sc + rng.integers(3, 8), 0, fc.N_COLS - 1))
        wave = j % n_waves
        es = int(np.clip(2 + wave * wave_span + rng.integers(0, max(2, int(wave_span * 0.5))),
                         1, fc.HORIZON_SLOTS - 10))
        ls = int(min(es + rng.integers(10, 16), fc.HORIZON_SLOTS - 5))
        missions.append(Mission(id=j, name=f"M{j}", start=(sr, sc),
                                end=(er, ec), es=es, ls=ls))

    return Scenario(seed=seed, waves=waves, current_kn=current,
                    ships=ships, missions=missions)


def scenario_hash(scn: Scenario) -> str:
    """Short content hash -- keys the oracle's table cache so a change in the
    generator can never silently serve stale cached tables."""
    import hashlib
    h = hashlib.md5()
    h.update(scn.waves.tobytes())
    h.update(np.float64(scn.current_kn).tobytes())
    for s in scn.ships:
        h.update(f"{s.ship_class}{s.home}{tuple(np.round(s.speeds, 3))}".encode())
    for m in scn.missions:
        h.update(f"{m.start}{m.end}{m.es}{m.ls}".encode())
    return h.hexdigest()[:10]


if __name__ == "__main__":
    scn = build_scenario(0)
    print(f"Scenario seed=0: {len(scn.ships)} ships, {len(scn.missions)} missions")
    print(f"  waves field: {scn.waves.shape}, range "
          f"{scn.waves.min():.1f}-{scn.waves.max():.1f} m, "
          f"current {scn.current_kn:+.1f} kn")
    for s in scn.ships:
        print(f"  {s.name:<8} {s.ship_class:<16} home={s.home} "
              f"speeds={np.round(s.speeds, 1)}")
    for m in scn.missions:
        print(f"  {m.name}: {m.start} -> {m.end}, start window [{m.es}, {m.ls}]")
