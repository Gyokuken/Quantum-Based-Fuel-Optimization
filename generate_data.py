"""
generate_data.py  --  Synthetic ship-voyage data generator (report section 4).

The Indian Coast Guard's real fuel/voyage logs are not public, so we *simulate*
them from transparent naval-architecture physics:

  1. Sample each ship's STATIC specs by class (Interceptor / Fast Patrol / OPV).
  2. Sample the DYNAMIC voyage conditions (speed, sea state, wind, current, load).
  3. Compute the fuel-burn RATE (tonnes/day) from a physics-based formula.
  4. Apply multiplicative noise (sensor + sea + operational variability).

The central physical idea is the CUBIC SPEED-POWER LAW (the "Admiralty law"):

        propulsion power  ~  displacement^(2/3) * (speed_through_water)^3

so fuel burned PER DAY grows with the cube of speed. Two important refinements:

  * Speed through water = speed_over_ground - current  (a following current
    means the ship needs less power to make the same progress over ground).
  * A speed-INDEPENDENT "hotel load" (generators, electronics, accommodation)
    burns fuel per day no matter how fast you go. This is what later makes
    *total voyage fuel* a U-shaped function of speed (the economic-speed effect).

The formula below is the hidden "truth"; the ML model only sees noisy
(features -> fuel_rate) rows and must learn to approximate it.

Run:
    py generate_data.py
    py generate_data.py --n 5000 --seed 7
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import config

# --------------------------------------------------------------------------- #
# Ground-truth fuel-model coefficients (the physics the model must rediscover) #
# --------------------------------------------------------------------------- #
PROP_COEF = 5.0e-5     # scales the cubic propulsion term -> realistic t/day
HOTEL_COEF = 0.02      # speed-independent auxiliary load ~ displacement^(2/3)
WAVE_COEF = 0.06       # added resistance per metre of significant wave height
WIND_COEF = 0.005      # added resistance per knot of wind
LADEN_FACTOR = 1.12    # laden ships sit deeper -> more resistance than ballast
NOISE_FRAC = 0.06      # 6% multiplicative noise

# Relative energy density of fuels (higher -> fewer tonnes for the same energy).
FUEL_ENERGY = {"MGO": 1.03, "VLSFO": 1.01, "HFO": 1.00}


def true_fuel_rate(df: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """Hidden physics: map feature rows -> fuel-burn rate (tonnes/day) + noise."""
    speed = df["speed_knots"].to_numpy()
    current = df["current_speed_kn"].to_numpy()
    disp = df["displacement_tonnes"].to_numpy()
    hull = df["hull_coefficient"].to_numpy()
    waves = df["wave_height_m"].to_numpy()
    wind = df["wind_speed_kn"].to_numpy()

    # Speed through water (current helps when positive); floor avoids div issues.
    stw = np.maximum(speed - current, 1.0)
    disp23 = disp ** (2.0 / 3.0)

    sea_state = 1.0 + WAVE_COEF * waves
    wind_factor = 1.0 + WIND_COEF * wind
    load_factor = np.where(df["load_condition"].to_numpy() == "Laden",
                           LADEN_FACTOR, 1.0)
    energy = df["fuel_type"].map(FUEL_ENERGY).to_numpy()

    propulsion = (PROP_COEF * disp23 * stw ** 3
                  * hull * sea_state * wind_factor * load_factor)
    hotel = HOTEL_COEF * disp23                      # speed-independent

    rate = (propulsion + hotel) / energy
    rate = rate * (1.0 + rng.normal(0.0, NOISE_FRAC, size=len(df)))
    return np.maximum(rate, 0.1)


def generate(n: int = 10_000, seed: int = 42) -> pd.DataFrame:
    """Generate `n` synthetic voyage-leg records as a DataFrame."""
    rng = np.random.default_rng(seed)

    # --- static specs, sampled per ship class ------------------------------ #
    classes = list(config.SHIP_SPECS.keys())
    probs = [config.SHIP_SPECS[c]["p"] for c in classes]
    ship_type = rng.choice(classes, size=n, p=probs)

    disp = np.empty(n)
    power = np.empty(n)
    hull = np.empty(n)
    fuel_type = np.empty(n, dtype=object)
    speed = np.empty(n)
    for c in classes:
        mask = ship_type == c
        k = int(mask.sum())
        if k == 0:
            continue
        spec = config.SHIP_SPECS[c]
        disp[mask] = rng.normal(*spec["disp"], k)
        power[mask] = rng.normal(*spec["power"], k)
        hull[mask] = rng.normal(*spec["hull"], k)
        fuel_type[mask] = rng.choice(list(spec["fuel"].keys()), size=k,
                                     p=list(spec["fuel"].values()))
        # Operational speed range for this class (5 kn .. class max).
        speed[mask] = rng.uniform(5.0, spec["max_speed"], k)

    disp = np.clip(disp, 30, 4000)
    power = np.clip(power, 800, 15000)
    hull = np.clip(hull, 0.38, 0.75)

    # --- dynamic voyage conditions ----------------------------------------- #
    wave_height = np.clip(rng.gamma(2.0, 1.0, n), 0, 8)          # sea state (m)
    # Wind correlates with sea state (rougher seas, stronger winds).
    wind_speed = np.clip(5 + 6 * wave_height + rng.normal(0, 5, n), 0, 50)
    current_speed = np.clip(rng.normal(0, 1.2, n), -3, 3)        # +ve = following
    load_condition = rng.choice(["Ballast", "Laden"], size=n, p=[0.5, 0.5])

    df = pd.DataFrame({
        "ship_type": ship_type,
        "fuel_type": fuel_type,
        "load_condition": load_condition,
        "displacement_tonnes": np.round(disp, 0),
        "engine_power_kw": np.round(power, 0),
        "hull_coefficient": np.round(hull, 3),
        "speed_knots": np.round(speed, 2),
        "wave_height_m": np.round(wave_height, 2),
        "wind_speed_kn": np.round(wind_speed, 1),
        "current_speed_kn": np.round(current_speed, 2),
    })

    df[config.TARGET] = np.round(true_fuel_rate(df, rng), 3)
    return df[config.FEATURE_COLUMNS + [config.TARGET]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic ship data.")
    parser.add_argument("--n", type=int, default=10_000, help="number of rows")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    args = parser.parse_args()

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = generate(args.n, args.seed)
    df.to_csv(config.DATA_CSV, index=False)

    print(f"Generated {len(df):,} voyage legs -> {config.DATA_CSV}")
    print("\nFirst 5 rows:")
    print(df.head().to_string(index=False))
    print("\nFuel rate (tonnes/day) summary:")
    print(df[config.TARGET].describe().round(2).to_string())


if __name__ == "__main__":
    main()
