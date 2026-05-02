"""
retrain_models.py
-----------------
Trains Random Forest, Gradient Boosting, and XGBoost on the full 2008-2024
processed data for all countries and targets (solar + wind).

Saves to:
  models/trained/{country}_{target}_{model_type}_model.pkl
  models/scalers/{country}_{target}_scaler.pkl     (shared across model types)
  models/scalers/{country}_{target}_features.pkl   (shared)
  models/summaries/{country}_model_summary.csv
"""

import sys, warnings, os
from pathlib import Path

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

from data_loader import data_loader
from config import config

MODELS_DIR   = Path("models/trained")
SCALERS_DIR  = Path("models/scalers")
SUMMARY_DIR  = Path("models/summaries")
for d in (MODELS_DIR, SCALERS_DIR, SUMMARY_DIR):
    d.mkdir(parents=True, exist_ok=True)

COUNTRIES = ["nigeria", "australia", "canada", "germany"]
TARGETS   = ["solar_radiation_wm2", "wind_speed"]

EXCLUDE_ALWAYS = {
    "time", "country", "season",
    "solar_radiation",
    "precipitation",
    "cloud_cover",
    "temperature_celsius",
}


def get_features(df: pd.DataFrame, target: str) -> list:
    excl = EXCLUDE_ALWAYS | {target}
    return [c for c in df.columns
            if c not in excl and pd.api.types.is_numeric_dtype(df[c])]


def build_model(model_type: str):
    if model_type == "rf":
        return RandomForestRegressor(
            n_estimators=100,
            max_depth=20,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
    elif model_type == "gb":
        return GradientBoostingRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.8,
            random_state=42,
        )
    elif model_type == "xgb":
        return xgb.XGBRegressor(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
    raise ValueError(f"Unknown model type: {model_type}")


def train_country(country: str):
    print(f"\n{'='*60}")
    print(f"  {country.upper()}")
    print(f"{'='*60}")

    df = data_loader.load_country_data(country)
    if df is None:
        print(f"  [SKIP] No data found")
        return

    df = df.dropna(how="all")
    print(f"  Loaded {len(df):,} rows")

    summaries = []

    for target in TARGETS:
        if target not in df.columns:
            print(f"  [SKIP] {target} not in data")
            continue

        feat_cols = get_features(df, target)
        sub = df[feat_cols + [target]].dropna()

        if len(sub) < 1000:
            print(f"  [SKIP] {target} — only {len(sub)} clean rows")
            continue

        X = sub[feat_cols].values
        y = sub[target].values

        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # Fit shared scaler once
        scaler = StandardScaler()
        X_tr_sc = scaler.fit_transform(X_train)
        X_te_sc = scaler.transform(X_test)

        # Save shared scaler + feature list (once per target)
        scaler_path = SCALERS_DIR / f"{country}_{target}_scaler.pkl"
        feat_path   = SCALERS_DIR / f"{country}_{target}_features.pkl"
        joblib.dump(scaler,    scaler_path)
        joblib.dump(feat_cols, feat_path)

        print(f"\n  {target}  ({len(X_train):,} train / {len(X_test):,} test / {len(feat_cols)} features)")

        for mtype in ("rf", "gb", "xgb"):
            model = build_model(mtype)
            model.fit(X_tr_sc, y_train)
            preds = model.predict(X_te_sc)

            mae  = mean_absolute_error(y_test, preds)
            rmse = np.sqrt(mean_squared_error(y_test, preds))
            r2   = r2_score(y_test, preds)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mape_arr = np.abs((y_test - preds) / (np.abs(y_test) + 1e-9)) * 100
                mape = float(np.mean(mape_arr[np.isfinite(mape_arr)]))

            model_path = MODELS_DIR / f"{country}_{target}_{mtype}_model.pkl"
            joblib.dump(model, model_path)

            # Keep backward-compat alias for xgb
            if mtype == "xgb":
                joblib.dump(model, MODELS_DIR / f"{country}_{target}_model.pkl")

            tag = {"rf": "Random Forest    ", "gb": "Gradient Boosting", "xgb": "XGBoost          "}[mtype]
            print(f"    {tag}  R²={r2:.4f}  MAE={mae:.3f}  RMSE={rmse:.3f}  MAPE={mape:.1f}%")

            summaries.append({
                "target":     target,
                "model":      mtype,
                "r2":         round(r2,   4),
                "mae":        round(mae,  4),
                "rmse":       round(rmse, 4),
                "mape":       round(mape, 2),
                "n_train":    len(X_train),
                "n_test":     len(X_test),
                "n_features": len(feat_cols),
            })

    if summaries:
        pd.DataFrame(summaries).to_csv(
            SUMMARY_DIR / f"{country}_model_summary.csv", index=False)
        print(f"\n  Summary saved.")


if __name__ == "__main__":
    for country in COUNTRIES:
        train_country(country)
    print("\nAll models retrained and saved.")
