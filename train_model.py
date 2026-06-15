"""
train_model.py  --  Ship fuel-rate prediction models (report section 6 + eval).

We train three models in increasing order of power, exactly like the report's
"baseline -> ensemble -> boosting" progression:

    1. Linear Regression   (baseline; fast, but underfits the cubic speed law)
    2. Random Forest       (captures non-linearity; strong classical baseline)
    3. Gradient Boosting   (HistGradientBoosting; state-of-the-art on tabular)

Target: fuel-burn RATE in tonnes/day. The model is domain-agnostic -- it simply
reads the feature schema from config.py, so the same code trains on ship data.

Each model is wrapped in a scikit-learn Pipeline that one-hot-encodes the
categorical columns, so the whole thing is a single fit/predict object. We score
every model with R2, MAE, RMSE and MAPE on a held-out test set, plus 5-fold
cross-validation R2 for robustness. The best model (by test R2) is saved to
models/ so the optimizer and (later) the dashboard can reuse it.

Run:
    py train_model.py
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

import config
import generate_data

RANDOM_STATE = 42


def load_data() -> pd.DataFrame:
    """Load the synthetic dataset, generating it first if it doesn't exist."""
    if not config.DATA_CSV.exists():
        print("No dataset found -- generating a default one (10,000 rows)...")
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        generate_data.generate().to_csv(config.DATA_CSV, index=False)
    return pd.read_csv(config.DATA_CSV)


def _one_hot_encoder() -> OneHotEncoder:
    """OneHotEncoder that returns dense output, across sklearn versions."""
    try:  # sklearn >= 1.2
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # older sklearn
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_pipeline(estimator) -> Pipeline:
    """Wrap an estimator with the shared preprocessing (one-hot categoricals)."""
    preprocess = ColumnTransformer([
        ("num", "passthrough", config.NUMERIC_FEATURES),
        ("cat", _one_hot_encoder(), config.CATEGORICAL),
    ])
    return Pipeline([("preprocess", preprocess), ("model", estimator)])


def _metrics(y_true, y_pred) -> dict:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)
    return {
        "R2": float(r2_score(y_true, y_pred)),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": rmse,
        "MAPE%": mape,
    }


def train_all(df: pd.DataFrame):
    """Train + evaluate all candidate models. Returns (results_df, name, pipe)."""
    X = df[config.FEATURE_COLUMNS]
    y = df[config.TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )

    candidates = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(
            n_estimators=200, n_jobs=-1, random_state=RANDOM_STATE
        ),
        "Gradient Boosting": HistGradientBoostingRegressor(
            random_state=RANDOM_STATE
        ),
    }

    rows, fitted = [], {}
    for name, est in candidates.items():
        pipe = build_pipeline(est)

        # 5-fold cross-validated R2 (robustness check on the full dataset).
        cv = cross_val_score(pipe, X, y, cv=5, scoring="r2")

        # Held-out test performance.
        pipe.fit(X_train, y_train)
        m = _metrics(y_test, pipe.predict(X_test))

        fitted[name] = pipe
        rows.append({
            "Model": name,
            "CV_R2_mean": round(cv.mean(), 4),
            "CV_R2_std": round(cv.std(), 4),
            "Test_R2": round(m["R2"], 4),
            "Test_MAE": round(m["MAE"], 3),
            "Test_RMSE": round(m["RMSE"], 3),
            "Test_MAPE%": round(m["MAPE%"], 2),
        })

    results = pd.DataFrame(rows).sort_values("Test_R2", ascending=False)
    best_name = results.iloc[0]["Model"]
    return results, best_name, fitted[best_name]


def save(best_name: str, best_pipe: Pipeline, df: pd.DataFrame) -> None:
    """Persist the best pipeline + metadata for downstream use."""
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipe, config.MODEL_PATH)

    meta = {
        "best_model": best_name,
        "feature_columns": config.FEATURE_COLUMNS,
        "numeric_features": config.NUMERIC_FEATURES,
        "categorical": config.CATEGORICAL,
        "target": config.TARGET,
        # Handy for the future dashboard: valid dropdown values.
        "categorical_options": {c: sorted(df[c].unique().tolist())
                                for c in config.CATEGORICAL},
    }
    joblib.dump(meta, config.META_PATH)


def main() -> None:
    df = load_data()
    print(f"Loaded {len(df):,} rows from {config.DATA_CSV.name}\n")

    results, best_name, best_pipe = train_all(df)

    print("Model comparison (sorted by test R2):")
    print(results.to_string(index=False))
    print(f"\nBest model: {best_name}")

    save(best_name, best_pipe, df)
    print(f"Saved best model -> {config.MODEL_PATH}")
    print(f"Saved metadata   -> {config.META_PATH}")


if __name__ == "__main__":
    main()
