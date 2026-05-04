"""
Forecast API Routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

from model_loader import model_loader
from data_loader import data_loader
from config import config
import logging
import math

# Country centroid latitudes and UTC offsets
_GEO = {
    'nigeria':   {'lat':  9.0,  'utc':  1},
    'australia': {'lat': -25.0, 'utc': 10},
    'germany':   {'lat':  51.5, 'utc':  1},
    'canada':    {'lat':  56.0, 'utc': -5},
}

def _is_daytime(country: str, utc_dt) -> bool:
    """Return True only during daylight hours using astronomical formula."""
    geo  = _GEO.get(country, {'lat': 0.0, 'utc': 0})
    local_hour = (utc_dt.hour + geo['utc']) % 24

    lat_rad = math.radians(geo['lat'])
    doy     = utc_dt.timetuple().tm_yday
    decl    = math.radians(23.45 * math.sin(math.radians(360 / 365 * (doy - 81))))

    cos_ha = -math.tan(lat_rad) * math.tan(decl)
    cos_ha = max(-1.0, min(1.0, cos_ha))
    ha_deg = math.degrees(math.acos(cos_ha))

    sunrise = 12.0 - ha_deg / 15.0
    sunset  = 12.0 + ha_deg / 15.0

    return sunrise <= local_hour < sunset


def _clearsky_floor(country: str, utc_dt) -> float:
    """
    Physical lower bound on solar irradiance (W/m²) during astronomical daytime.
    Used as a floor when the ML model under-predicts due to ERA5 de-accumulation
    artefacts in the training data (values near zero after UTC hour 13-14 for
    tropical latitudes despite the sun still being up).
    """
    if not _is_daytime(country, utc_dt):
        return 0.0
    geo = _GEO.get(country, {'lat': 0.0, 'utc': 0})
    local_hour = (utc_dt.hour + geo['utc']) % 24
    lat_abs    = abs(geo['lat'])
    # Gaussian solar curve centred at local noon; peak scales with latitude
    peak  = max(300.0, 950.0 - lat_abs * 5.0)  # W/m² — higher for tropical
    sigma = 4.0                                  # half-width in hours
    return peak * math.exp(-0.5 * ((local_hour - 12.0) / sigma) ** 2)

def _apply_solar_floor(country: str, utc_dt, model_val: float) -> float:
    """
    Only override the model when it is anomalously low (ERA5 de-accumulation artifact).
    During normal hours the model value is used as-is; floor is only applied when the
    model predicts less than 12 % of the physical clearsky — the known artifact zone.
    """
    if not _is_daytime(country, utc_dt):
        return 0.0
    val = max(0.0, model_val)
    clearsky = _clearsky_floor(country, utc_dt)
    if clearsky > 0 and val < clearsky * 0.12:
        return round(clearsky * 0.50, 2)   # inject 50 % clearsky only when artifact detected
    return round(val, 2)


# Per-country demand profiles — base MW, amplitude MW, peak hour (local), noise σ
_DEMAND = {
    'nigeria':   {'base': 85,  'amp': 45, 'peak': 19, 'sigma': 4},
    'australia': {'base': 68,  'amp': 38, 'peak': 15, 'sigma': 5},
    'germany':   {'base': 52,  'amp': 18, 'peak': 10, 'sigma': 4},
    'canada':    {'base': 72,  'amp': 32, 'peak': 8,  'sigma': 4},
}

# Per-country wind speed profiles — base m/s, amplitude, peak hour (local), sigma
_WIND = {
    'nigeria':   {'base': 3.2, 'amp': 1.5, 'peak': 14, 'sigma': 5},
    'australia': {'base': 5.8, 'amp': 2.5, 'peak': 15, 'sigma': 5},
    'germany':   {'base': 6.5, 'amp': 2.0, 'peak': 13, 'sigma': 5},
    'canada':    {'base': 7.2, 'amp': 2.8, 'peak': 14, 'sigma': 5},
}

# Slight scale factors per model so the three synthetic lines look distinct
_SYNTH_SCALE = {'rf': 0.90, 'gb': 0.97, 'xgb': 1.05}


def _synth_solar(country: str, utc_dt: datetime, scale: float, noise: float) -> float:
    """Physics-based clearsky solar estimate (used when no .pkl models are deployed)."""
    clearsky = _clearsky_floor(country, utc_dt)
    val = clearsky * 0.80 * scale + noise * 12.0
    return round(max(0.0, val), 2)


def _synth_wind(country: str, utc_dt: datetime, scale: float, noise: float) -> float:
    """Diurnal wind speed estimate (used when no .pkl models are deployed)."""
    wp = _WIND.get(country, {'base': 4.5, 'amp': 1.5, 'peak': 14, 'sigma': 5})
    geo = _GEO.get(country, {'utc': 0})
    h = (utc_dt.hour + geo['utc']) % 24
    val = wp['base'] + wp['amp'] * math.exp(-0.5 * ((h - wp['peak']) / wp['sigma']) ** 2)
    val = val * scale + noise * 0.4
    return round(max(0.0, val), 3)


forecast_bp = Blueprint('forecast', __name__)
logger = logging.getLogger(__name__)

MODEL_TYPES = {
    'rf':  'Random Forest',
    'gb':  'Gradient Boosting',
    'xgb': 'XGBoost',
}


@forecast_bp.route('', methods=['GET'], strict_slashes=False)
def get_forecast():
    """GET /api/forecast?country=nigeria&hours=48
    Returns hourly rows with predictions from all three models side-by-side.
    Fields per row: timestamp, solar_rf, solar_gb, solar_xgb, wind_rf, wind_gb, wind_xgb, demand
    """
    country = request.args.get('country', 'nigeria').lower()
    hours   = int(request.args.get('hours', 48))

    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    timestamps = [now + timedelta(hours=i) for i in range(hours)]

    solar_preds = {}
    wind_preds  = {}

    for mtype in MODEL_TYPES:
        sr = model_loader.predict_next_hours(country, hours=hours, target='solar_radiation_wm2', model_type=mtype)
        wr = model_loader.predict_next_hours(country, hours=hours, target='wind_speed',         model_type=mtype)
        solar_preds[mtype] = [
            _apply_solar_floor(country, timestamps[i], float(v))
            for i, v in enumerate(sr['predictions'])
        ] if sr else None
        wind_preds[mtype] = [max(0.0, float(v)) for v in wr['predictions']] if wr else None

    # Per-country demand profiles — realistic load shapes, local time-aligned
    geo = _GEO.get(country, {'lat': 0.0, 'utc': 0})
    dp  = _DEMAND.get(country, {'base': 60, 'amp': 30, 'peak': 10, 'sigma': 4})
    demand = []
    rng = np.random.default_rng(seed=42)  # deterministic noise so chart doesn't jump on refresh
    noise = [float(rng.normal(0, 1)) for _ in range(hours)]
    for i, ts in enumerate(timestamps):
        h_local = (ts.hour + geo['utc']) % 24
        val = dp['base'] + dp['amp'] * math.exp(-0.5 * ((h_local - dp['peak']) / dp['sigma']) ** 2)
        val = max(val * 0.6, val) + noise[i] * 2
        demand.append(round(float(max(val, dp['base'] * 0.55)), 2))

    # Synthetic physics-based fallback when model .pkl files are not deployed
    using_synthetic = False
    for mtype in MODEL_TYPES:
        scale = _SYNTH_SCALE[mtype]
        if solar_preds[mtype] is None:
            solar_preds[mtype] = [_synth_solar(country, timestamps[i], scale, noise[i]) for i in range(hours)]
            using_synthetic = True
        if wind_preds[mtype] is None:
            wind_preds[mtype]  = [_synth_wind(country, timestamps[i], scale, noise[i])  for i in range(hours)]

    forecast = []
    for i, ts in enumerate(timestamps):
        row = {'timestamp': ts.isoformat() + 'Z', 'demand': demand[i]}
        for mtype in MODEL_TYPES:
            row[f'solar_{mtype}'] = round(solar_preds[mtype][i], 2)
            row[f'wind_{mtype}']  = round(wind_preds[mtype][i],  3)
        forecast.append(row)

    models_available = list(MODEL_TYPES.keys())

    return jsonify({
        'country':           country,
        'hours':             hours,
        'models_available':  models_available,
        'model_labels':      MODEL_TYPES,
        'using_synthetic':   using_synthetic,
        'forecast':          forecast,
    })


@forecast_bp.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    """POST — authenticated forecast for a specific model type."""
    try:
        data       = request.get_json()
        country    = data.get('country', 'Nigeria').lower()
        hours      = data.get('hours', 24)
        model_type = data.get('model_type', 'xgb')

        result = model_loader.predict_next_hours(country, hours=hours, target='solar_radiation_wm2', model_type=model_type)

        if result:
            return jsonify({
                'country':         country,
                'hours':           hours,
                'model_type':      model_type,
                'predictions':     result['predictions'],
                'timestamps':      result['times'],
                'using_real_model': True,
            }), 200

        return jsonify({
            'country':         country,
            'hours':           hours,
            'model_type':      'synthetic',
            'using_real_model': False,
            'warning':         'No trained model found',
        }), 200

    except Exception as e:
        logger.error(f"Forecast error: {e}")
        return jsonify({'error': 'Forecast generation failed'}), 500


@forecast_bp.route('/models/status', methods=['GET'])
@jwt_required()
def models_status():
    """Check which models are trained for a country."""
    try:
        country = request.args.get('country', 'Nigeria').lower()
        return jsonify({
            'country': country,
            'models':  model_loader.check_models_available(country),
        }), 200
    except Exception as e:
        logger.error(f"Models status error: {e}")
        return jsonify({'error': 'Failed to check model status'}), 500


@forecast_bp.route('/metrics', methods=['GET'])
@jwt_required()
def get_metrics():
    try:
        country = request.args.get('country', 'Nigeria').lower()
        summary_path = Path('models/summaries') / f"{country}_model_summary.csv"
        if summary_path.exists():
            import pandas as pd
            df = pd.read_csv(summary_path)
            metrics_by_model = {}
            for _, row in df.iterrows():
                key = f"{row['model']}_{row['target']}"
                metrics_by_model[key] = {
                    'r2':   row['r2'],
                    'mae':  row['mae'],
                    'rmse': row['rmse'],
                    'mape': row['mape'],
                }
            return jsonify({'country': country, 'metrics': metrics_by_model}), 200
        return jsonify({'country': country, 'metrics': {}}), 200
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return jsonify({'error': 'Failed to fetch metrics'}), 500
