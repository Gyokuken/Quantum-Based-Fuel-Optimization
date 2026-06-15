"""
Central configuration for the Maritime Fuel Efficiency project.

Domain: SHIPS (Indian Coast Guard -- Problem Statement 77,
"Fuel consumption optimization using AI-based tools").

Keeping the feature schema, ship specifications, file paths, and voyage defaults
in one place means the data generator, the model trainer, and the optimizer all
agree on the same columns and ship classes -- no silent mismatches.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths                                                                        #
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
OUTPUTS_DIR = ROOT_DIR / "outputs"

DATA_CSV = DATA_DIR / "ship_fuel_data.csv"
MODEL_PATH = MODELS_DIR / "ship_fuel_model.joblib"
META_PATH = MODELS_DIR / "model_meta.joblib"

# --------------------------------------------------------------------------- #
# Feature schema  (static = ship design, dynamic = voyage conditions)         #
# --------------------------------------------------------------------------- #
# Static numeric: properties of the vessel.
NUMERIC_STATIC = ["displacement_tonnes", "engine_power_kw", "hull_coefficient"]

# Dynamic numeric: conditions during the voyage leg.
NUMERIC_DYNAMIC = ["speed_knots", "wave_height_m", "wind_speed_kn", "current_speed_kn"]

# Categorical features.
CATEGORICAL = ["ship_type", "fuel_type", "load_condition"]

# What we predict: main + auxiliary fuel burn RATE, in tonnes per day.
TARGET = "fuel_rate_tpd"

NUMERIC_FEATURES = NUMERIC_STATIC + NUMERIC_DYNAMIC
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL

# The decision variable the optimizer controls.
DECISION_VAR = "speed_knots"

# --------------------------------------------------------------------------- #
# Ship classes (Indian Coast Guard style patrol fleet)                        #
# --------------------------------------------------------------------------- #
# For each class: sampling priors for the data generator (disp/power/hull/fuel),
# plus operational speeds (knots) used by the optimizer for search bounds and
# the "business as usual" baseline.
#   disp  = (mean, sd) displacement in tonnes
#   power = (mean, sd) installed engine power in kW
#   hull  = (mean, sd) hull/block coefficient (finer hull = lower)
#   fuel  = probability of each fuel type
SHIP_SPECS = {
    "Interceptor": dict(
        p=0.35, disp=(60, 15), power=(3000, 600), hull=(0.42, 0.04),
        fuel={"MGO": 1.0},
        max_speed=35.0, service_speed=28.0,
    ),
    "Fast_Patrol": dict(
        p=0.40, disp=(550, 120), power=(6000, 1200), hull=(0.50, 0.04),
        fuel={"MGO": 0.9, "VLSFO": 0.1},
        max_speed=28.0, service_speed=22.0,
    ),
    "Offshore_Patrol": dict(
        p=0.25, disp=(2000, 400), power=(9000, 1800), hull=(0.62, 0.04),
        fuel={"MGO": 0.6, "VLSFO": 0.3, "HFO": 0.1},
        max_speed=25.0, service_speed=18.0,
    ),
}

# CO2 emitted per tonne of fuel burned (IMO factors, t CO2 / t fuel).
EMISSION_FACTORS = {"MGO": 3.206, "VLSFO": 3.151, "HFO": 3.114}

# --------------------------------------------------------------------------- #
# Voyage / optimization defaults                                              #
# --------------------------------------------------------------------------- #
PHYSICAL_MIN_SPEED = 4.0          # knots; below this a ship loses steerage
DEFAULT_VOYAGE_NM = 600.0         # nautical miles for the demo leg
DEFAULT_DEADLINE_HOURS = 40.0     # must complete the leg within this time

# A representative scenario the optimizer/plot demo uses by default.
# (Everything except `speed_knots`, which the optimizer chooses.)
DEFAULT_SCENARIO = {
    "ship_type": "Offshore_Patrol",
    "fuel_type": "MGO",
    "load_condition": "Laden",
    "displacement_tonnes": 2000.0,
    "engine_power_kw": 9000.0,
    "hull_coefficient": 0.62,
    "wave_height_m": 1.5,
    "wind_speed_kn": 12.0,
    "current_speed_kn": 0.0,
}
