"""
optimizer.py  --  Quantum-inspired voyage optimizer (report section 7).

Once we can PREDICT a ship's fuel-burn RATE (tonnes/day), we can OPTIMIZE a
voyage. The maritime twist vs road vehicles:

  * Fuel RATE grows with the cube of speed, so "minimise fuel" alone just says
    "go as slow as possible" -- trivial and operationally useless.
  * The REAL problem is SLOW STEAMING: minimise the *total fuel for the leg*
    while still ARRIVING ON TIME. Total fuel = rate(speed) x voyage_time, and
    voyage_time = distance / speed, so:

        total_fuel(speed) = rate(speed) * distance / (24 * speed)

    Because the ship also burns a speed-independent "hotel load" per day, this
    total-fuel curve is U-SHAPED -- there is an "economic speed". The deadline
    adds a hard floor on speed (you cannot go slower than distance/deadline).

We minimise total voyage fuel with **Simulated Annealing** (the classical cousin
of quantum annealing -- hence "quantum-inspired"), and validate against a
brute-force grid search. We also report CO2 emissions (IMO factor) since the
Coast Guard problem statement calls out environmental compliance.
(Phase 2 will add a QUBO/neal formulation and combinatorial route optimization.)

Run:
    py optimizer.py
    py optimizer.py --distance 600 --deadline 80 --waves 4 --wind 30
"""

from __future__ import annotations

import argparse

import joblib
import numpy as np
import pandas as pd

import config


# --------------------------------------------------------------------------- #
# Model loading + objective functions                                          #
# --------------------------------------------------------------------------- #
def load_model():
    """Load the trained pipeline, training it first if it doesn't exist."""
    if not config.MODEL_PATH.exists():
        print("No trained model found -- training one now...")
        import train_model
        train_model.main()
    return joblib.load(config.MODEL_PATH)


def predict_rate(pipe, scenario: dict, speed: float) -> float:
    """Predicted fuel-burn rate (tonnes/day) for `scenario` at `speed` knots."""
    row = {**scenario, config.DECISION_VAR: float(speed)}
    X = pd.DataFrame([row])[config.FEATURE_COLUMNS]
    return float(pipe.predict(X)[0])


def voyage_fuel(pipe, scenario: dict, speed: float, distance_nm: float) -> float:
    """Total fuel (tonnes) to cover `distance_nm` at `speed` knots."""
    rate_tpd = predict_rate(pipe, scenario, speed)   # tonnes / day
    time_days = distance_nm / (speed * 24.0)         # hours/24
    return rate_tpd * time_days


# --------------------------------------------------------------------------- #
# Simulated Annealing  (generic over a vector of decision variables)          #
# --------------------------------------------------------------------------- #
def simulated_annealing(objective, x0, bounds, *, n_iter=2000, t0=5.0,
                        cooling=0.995, seed=0):
    """Minimise `objective(x)` over a box `bounds` via simulated annealing.

    Returns (best_x, best_energy, best_energy_history).
    """
    rng = np.random.default_rng(seed)
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)
    step = 0.10 * (hi - lo)          # move size per dimension

    x = np.array(x0, dtype=float)
    energy = objective(x)
    best_x, best_energy = x.copy(), energy
    history = [best_energy]

    temp = t0
    for _ in range(n_iter):
        candidate = np.clip(x + rng.normal(0.0, step), lo, hi)
        cand_energy = objective(candidate)
        delta = cand_energy - energy
        # Accept if better, or probabilistically if worse (the SA twist).
        if delta < 0 or rng.random() < np.exp(-delta / max(temp, 1e-9)):
            x, energy = candidate, cand_energy
        if energy < best_energy:
            best_x, best_energy = x.copy(), energy
        history.append(best_energy)
        temp *= cooling

    return best_x, best_energy, history


def grid_search(objective_1d, bounds, n=1000):
    """Brute-force minimum of a 1-D objective -- the 'truth' SA must match."""
    xs = np.linspace(bounds[0], bounds[1], n)
    fs = np.array([objective_1d(x) for x in xs])
    i = int(np.argmin(fs))
    return xs[i], fs[i], xs, fs


# --------------------------------------------------------------------------- #
# High-level: optimise cruising speed for a voyage leg                         #
# --------------------------------------------------------------------------- #
def optimize_speed(pipe, scenario: dict, distance_nm: float,
                   deadline_hours: float, baseline_speed: float | None = None,
                   seed: int = 0) -> dict:
    """Find the fuel-minimising speed that still meets the arrival deadline."""
    spec = config.SHIP_SPECS[scenario["ship_type"]]
    max_speed = spec["max_speed"]
    if baseline_speed is None:                       # "business as usual" speed
        baseline_speed = spec["service_speed"]

    # Deadline imposes a minimum speed: distance / deadline.
    deadline_min_speed = distance_nm / deadline_hours
    lower = max(config.PHYSICAL_MIN_SPEED, deadline_min_speed)
    upper = max_speed
    emission_factor = config.EMISSION_FACTORS[scenario["fuel_type"]]

    # Infeasible: even at full speed the ship cannot arrive in time.
    if lower > upper:
        return {
            "feasible": False,
            "deadline_min_speed": deadline_min_speed,
            "max_speed": max_speed,
            "distance_nm": distance_nm,
            "deadline_hours": deadline_hours,
        }

    obj_1d = lambda s: voyage_fuel(pipe, scenario, s, distance_nm)        # noqa: E731
    obj_vec = lambda v: voyage_fuel(pipe, scenario, float(v[0]), distance_nm)  # noqa: E731

    sa_x, sa_fuel, _ = simulated_annealing(
        obj_vec, x0=[(lower + upper) / 2], bounds=[(lower, upper)], seed=seed
    )
    grid_speed, grid_fuel, _, _ = grid_search(obj_1d, (lower, upper))
    baseline_fuel = obj_1d(baseline_speed)

    def hours(speed):
        return distance_nm / speed

    return {
        "feasible": True,
        "distance_nm": distance_nm,
        "deadline_hours": deadline_hours,
        "deadline_min_speed": deadline_min_speed,
        "max_speed": max_speed,
        "fuel_type": scenario["fuel_type"],
        "baseline_speed": baseline_speed,
        "baseline_fuel": baseline_fuel,
        "baseline_hours": hours(baseline_speed),
        "baseline_co2": baseline_fuel * emission_factor,
        "opt_speed": float(sa_x[0]),
        "opt_fuel": float(sa_fuel),
        "opt_hours": hours(float(sa_x[0])),
        "opt_co2": float(sa_fuel) * emission_factor,
        "grid_speed": float(grid_speed),
        "grid_fuel": float(grid_fuel),
        "fuel_saving_pct": (baseline_fuel - sa_fuel) / baseline_fuel * 100,
        "co2_saved_t": (baseline_fuel - sa_fuel) * emission_factor,
        "sa_vs_grid_speed_gap": abs(float(sa_x[0]) - float(grid_speed)),
    }


def print_report(scenario: dict, res: dict) -> None:
    print("Scenario (fixed inputs):")
    for k, v in scenario.items():
        print(f"  {k:<20} = {v}")

    if not res["feasible"]:
        print("\n  INFEASIBLE: deadline cannot be met even at full speed.")
        print(f"  Need {res['deadline_min_speed']:.1f} kn but max is "
              f"{res['max_speed']:.1f} kn.")
        return

    print(f"\n  Voyage: {res['distance_nm']:.0f} nm, "
          f"deadline {res['deadline_hours']:.0f} h "
          f"(=> min speed {res['deadline_min_speed']:.1f} kn)")
    print()
    print(f"  {'':<14}{'speed':>8}{'time':>9}{'fuel':>9}{'CO2':>9}")
    print(f"  {'':<14}{'(kn)':>8}{'(h)':>9}{'(t)':>9}{'(t)':>9}")
    print(f"  {'Baseline':<14}{res['baseline_speed']:>8.1f}"
          f"{res['baseline_hours']:>9.1f}{res['baseline_fuel']:>9.1f}"
          f"{res['baseline_co2']:>9.1f}")
    print(f"  {'Optimized':<14}{res['opt_speed']:>8.1f}"
          f"{res['opt_hours']:>9.1f}{res['opt_fuel']:>9.1f}"
          f"{res['opt_co2']:>9.1f}")
    print()
    print(f"  Fuel saving : {res['fuel_saving_pct']:.1f}%  "
          f"({res['baseline_fuel'] - res['opt_fuel']:.1f} t fuel, "
          f"{res['co2_saved_t']:.1f} t CO2 per leg)")
    print(f"  Validation  : SA vs grid speed gap "
          f"{res['sa_vs_grid_speed_gap']:.2f} kn (small = true optimum found)")


def main() -> None:
    p = argparse.ArgumentParser(description="Optimise ship speed for a voyage.")
    p.add_argument("--distance", type=float, default=config.DEFAULT_VOYAGE_NM,
                   help="voyage distance (nautical miles)")
    p.add_argument("--deadline", type=float, default=config.DEFAULT_DEADLINE_HOURS,
                   help="arrival deadline (hours)")
    p.add_argument("--waves", type=float,
                   default=config.DEFAULT_SCENARIO["wave_height_m"])
    p.add_argument("--wind", type=float,
                   default=config.DEFAULT_SCENARIO["wind_speed_kn"])
    p.add_argument("--current", type=float,
                   default=config.DEFAULT_SCENARIO["current_speed_kn"])
    p.add_argument("--baseline-speed", type=float, default=None)
    args = p.parse_args()

    scenario = dict(config.DEFAULT_SCENARIO)
    scenario["wave_height_m"] = args.waves
    scenario["wind_speed_kn"] = args.wind
    scenario["current_speed_kn"] = args.current

    pipe = load_model()
    res = optimize_speed(pipe, scenario, args.distance, args.deadline,
                         baseline_speed=args.baseline_speed)
    print_report(scenario, res)


if __name__ == "__main__":
    main()
