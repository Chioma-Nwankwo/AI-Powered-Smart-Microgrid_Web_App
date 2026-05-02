"""
Model loader for app — loads trained models and makes predictions.
Supports three model types: rf (Random Forest), gb (Gradient Boosting), xgb (XGBoost).
"""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(self, models_dir: str = "models/trained"):
        self.models_dir  = Path(models_dir)
        self.scalers_dir = Path("models/scalers")
        self.models_cache  = {}
        self.scalers_cache = {}

    def load_model(self, country: str, target: str, model_type: str = 'xgb'):
        """Load a trained model by type (rf / gb / xgb)."""
        cache_key = f"{country}_{target}_{model_type}"
        if cache_key in self.models_cache:
            return self.models_cache[cache_key]

        # Primary: type-specific file
        model_path = self.models_dir / f"{country}_{target}_{model_type}_model.pkl"
        # Fallback: legacy xgb file saved without type suffix
        if not model_path.exists():
            model_path = self.models_dir / f"{country}_{target}_model.pkl"

        if not model_path.exists():
            logger.warning(f"Model not found: {country}/{target}/{model_type}")
            return None

        try:
            obj = joblib.load(model_path)
            model = obj.get('model', obj) if isinstance(obj, dict) else obj
            self.models_cache[cache_key] = model
            logger.info(f"Loaded model: {model_path.name}")
            return model
        except Exception as e:
            logger.error(f"Error loading model {model_path}: {e}")
            return None

    def load_scaler(self, country: str, target: str):
        """Load the shared scaler (same for all model types)."""
        cache_key = f"{country}_{target}"
        if cache_key in self.scalers_cache:
            return self.scalers_cache[cache_key]

        scaler_path = self.scalers_dir / f"{country}_{target}_scaler.pkl"
        if not scaler_path.exists():
            scaler_path = self.models_dir / f"{country}_{target}_scaler.pkl"

        if not scaler_path.exists():
            logger.warning(f"Scaler not found for {country}/{target}")
            return None

        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scaler = joblib.load(scaler_path)
            self.scalers_cache[cache_key] = scaler
            logger.info(f"Loaded scaler: {scaler_path.name}")
            return scaler
        except Exception as e:
            logger.error(f"Error loading scaler: {e}")
            return None

    def predict_next_hours(
        self,
        country: str,
        hours: int = 24,
        target: str = 'solar_radiation_wm2',
        model_type: str = 'xgb',
    ) -> Optional[Dict]:
        """Return predictions for the next N hours using the given model type."""
        from data_loader import data_loader

        model  = self.load_model(country, target, model_type)
        scaler = self.load_scaler(country, target)

        if model is None or scaler is None:
            return None

        recent_data = data_loader.get_latest_data(country, hours=168)
        if recent_data is None or len(recent_data) < hours:
            return None

        # Load saved feature list
        feat_path = self.scalers_dir / f"{country}_{target}_features.pkl"
        if feat_path.exists():
            feature_cols = joblib.load(feat_path)
            feature_cols = [c for c in feature_cols if c in recent_data.columns]
        else:
            feature_cols = [c for c in recent_data.columns
                            if c not in ('time', 'country', target)
                            and pd.api.types.is_numeric_dtype(recent_data[c])]

        X_latest = recent_data[feature_cols].tail(hours).values
        valid_mask = ~np.isnan(X_latest).any(axis=1)
        X_valid = X_latest[valid_mask] if valid_mask.any() else X_latest

        try:
            X_scaled = scaler.transform(X_valid)
        except Exception:
            X_scaled = X_valid

        predictions_raw = model.predict(X_scaled)
        predictions = np.full(len(X_latest), np.nan)
        if valid_mask.any():
            predictions[valid_mask] = predictions_raw
        else:
            predictions = predictions_raw

        last_time = recent_data['time'].iloc[-1]
        future_times = pd.date_range(
            start=last_time + pd.Timedelta(hours=1),
            periods=hours,
            freq='h',
        )

        actual_values = recent_data[target].tail(hours).values if target in recent_data.columns else None

        return {
            'predictions': predictions.tolist(),
            'times':       [str(t) for t in future_times],
            'actual':      actual_values.tolist() if actual_values is not None else None,
            'country':     country,
            'target':      target,
            'model_type':  model_type,
            'hours':       hours,
        }

    def check_models_available(self, country: str) -> Dict[str, bool]:
        """Check which model types are available for a country."""
        available = {}
        for mtype in ('rf', 'gb', 'xgb'):
            m = self.load_model(country, 'solar_radiation_wm2', mtype)
            s = self.load_scaler(country, 'solar_radiation_wm2')
            available[mtype] = (m is not None and s is not None)
        return available


model_loader = ModelLoader()


def get_country_forecast(country: str, hours: int = 24, model_type: str = 'xgb') -> Optional[Dict]:
    return model_loader.predict_next_hours(country, hours, model_type=model_type)
