"""
API routes for anomaly detection
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pathlib import Path

try:
    from models.anomaly_detection import (
        AutoencoderAnomalyDetector,
        PCAAnomalyDetector,
        OneClassSVMAnomalyDetector,
        IsolationForestAnomalyDetector,
        EnsembleAnomalyDetector,
    )
    _HAS_ANOMALY_MODELS = True
except Exception:
    _HAS_ANOMALY_MODELS = False
    AutoencoderAnomalyDetector = PCAAnomalyDetector = None
    OneClassSVMAnomalyDetector = IsolationForestAnomalyDetector = None
    EnsembleAnomalyDetector = None
from utils.data_processor import DataProcessor
import numpy as np
import pandas as pd
from config import config
import logging

logger = logging.getLogger(__name__)
anomaly_bp = Blueprint('anomaly', __name__, url_prefix='/api/anomaly')


@anomaly_bp.route('', methods=['GET'], strict_slashes=False)
def get_anomalies():
    try:
        return _run_anomalies()
    except Exception as e:
        logger.error("Anomaly route error: %s", e, exc_info=True)
        return jsonify({
            'error': str(e),
            'anomalies': [], 'n_anomalies': 0,
            'country': request.args.get('country', 'nigeria'),
        }), 500


def _run_anomalies():
    """GET /api/anomaly?country=nigeria&hours=48
    Chapter 3.6.2 ensemble: Isolation Forest + PCA + One-Class SVM.
    Fitted on historical ERA5 data; predicted on XGBoost forecast points.
    Majority vote (≥2/3 sklearn detectors) flags an anomaly.
    """
    from data_loader import data_loader as dl
    from model_loader import model_loader
    from datetime import datetime, timedelta
    import math
    from sklearn.ensemble import IsolationForest
    from sklearn.decomposition import PCA
    from sklearn.svm import OneClassSVM
    from sklearn.preprocessing import StandardScaler

    country = request.args.get('country', 'nigeria').lower()
    hours   = int(request.args.get('hours', 48))

    _GEO_A = {
        'nigeria':   {'lat':  9.0,  'utc':  1},
        'australia': {'lat': -25.0, 'utc': 10},
        'germany':   {'lat':  51.5, 'utc':  1},
        'canada':    {'lat':  56.0, 'utc': -5},
    }
    def _daytime(ts):
        geo = _GEO_A.get(country, {'lat': 0, 'utc': 0})
        lh  = (ts.hour + geo['utc']) % 24
        lr  = math.radians(geo['lat'])
        doy = ts.timetuple().tm_yday
        decl = math.radians(23.45 * math.sin(math.radians(360/365*(doy-81))))
        cos_ha = max(-1.0, min(1.0, -math.tan(lr)*math.tan(decl)))
        ha = math.degrees(math.acos(cos_ha))
        return (12.0 - ha/15.0) <= lh < (12.0 + ha/15.0)

    # ── 1. Load historical training data ─────────────────────────────
    hist_df = dl.get_latest_data(country, hours=max(hours * 6, 1440))
    FEAT_COLS = ['solar_radiation_wm2', 'wind_speed']
    for c in ['temperature_celsius', 'pressure', 'precipitation_mm']:
        if hist_df is not None and c in hist_df.columns:
            FEAT_COLS.append(c)

    if hist_df is None or hist_df.empty:
        return jsonify({'anomalies': [], 'country': country, 'hours': hours,
                        'detectors': [], 'note': 'No historical data available'})

    hist_cols = [c for c in FEAT_COLS if c in hist_df.columns]
    X_hist = hist_df[hist_cols].fillna(0).values
    if len(X_hist) < 50:
        return jsonify({'anomalies': [], 'country': country, 'hours': hours,
                        'detectors': [], 'note': 'Insufficient historical data'})

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_hist)

    # ── 2. Fit 3 sklearn detectors on historical data ─────────────────
    iso_forest = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
    iso_forest.fit(X_scaled)

    pca = PCA(n_components=min(3, X_scaled.shape[1]))
    X_pca = pca.fit_transform(X_scaled)
    X_recon = pca.inverse_transform(X_pca)
    recon_errors = np.mean((X_scaled - X_recon) ** 2, axis=1)
    pca_threshold = np.percentile(recon_errors, 95)

    ocsvm = OneClassSVM(kernel='rbf', nu=0.05, gamma='scale')
    ocsvm.fit(X_scaled)

    # Also compute IQR bounds for score magnitude
    hist_2col = hist_df[['solar_radiation_wm2', 'wind_speed']].dropna()
    iqr_bounds = {}
    for col in ['solar_radiation_wm2', 'wind_speed']:
        if col in hist_df.columns:
            s = hist_df[col].dropna()
            Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
            IQR = Q3 - Q1
            iqr_bounds[col] = {'lower': Q1 - 1.5*IQR, 'upper': Q3 + 1.5*IQR,
                                'median': float(s.median()), 'iqr': max(float(IQR), 1e-9)}

    # ── 3. Get forecast points to evaluate ───────────────────────────
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    timestamps = [now + timedelta(hours=i) for i in range(1, hours + 1)]

    solar_fc = model_loader.predict_next_hours(country, hours=hours,
                                               target='solar_radiation_wm2', model_type='xgb')
    wind_fc  = model_loader.predict_next_hours(country, hours=hours,
                                               target='wind_speed',          model_type='xgb')

    solar_preds = [
        max(0.0, float(v)) if _daytime(timestamps[i]) else 0.0
        for i, v in enumerate(solar_fc['predictions'])
    ] if solar_fc else [0.0] * hours
    wind_preds = [max(0.0, float(v)) for v in wind_fc['predictions']] if wind_fc else [0.0] * hours

    severity_map = {0: 'low', 1: 'medium', 2: 'high', 3: 'critical'}
    anomalies = []

    for i, ts in enumerate(timestamps):
        # Build feature vector for this forecast point
        feat_vals = []
        for col in hist_cols:
            if col == 'solar_radiation_wm2': feat_vals.append(solar_preds[i])
            elif col == 'wind_speed':        feat_vals.append(wind_preds[i])
            else:
                col_mean = float(hist_df[col].mean()) if col in hist_df.columns else 0.0
                feat_vals.append(col_mean)

        X_point = scaler.transform([feat_vals])

        # Run 3 detectors
        if_pred   = iso_forest.predict(X_point)[0]          # -1 = anomaly
        if_score  = -iso_forest.score_samples(X_point)[0]   # higher = more anomalous

        pca_recon  = pca.inverse_transform(pca.transform(X_point))
        pca_err    = float(np.mean((X_point - pca_recon) ** 2))
        pca_pred   = -1 if pca_err > pca_threshold else 1

        svm_pred   = ocsvm.predict(X_point)[0]              # -1 = anomaly
        svm_score  = -ocsvm.score_samples(X_point)[0]

        votes = sum(1 for p in [if_pred, pca_pred, svm_pred] if p == -1)
        is_anomaly = votes >= 2   # majority vote (Chapter 3.6.2)

        if not is_anomaly:
            continue

        # Composite anomaly score (normalised average)
        comp_score = (if_score + (pca_err / max(pca_threshold, 1e-9)) + max(0, svm_score)) / 3.0
        sev_i = min(3, int(comp_score * 4))

        # Variable attribution: which variable deviated most from IQR
        max_dev, culprit = 0.0, 'solar_radiation_wm2'
        for col, val in [('solar_radiation_wm2', solar_preds[i]), ('wind_speed', wind_preds[i])]:
            if col in iqr_bounds:
                b = iqr_bounds[col]
                dev = max(0.0, val - b['upper'], b['lower'] - val) / b['iqr']
                if dev > max_dev:
                    max_dev = dev
                    culprit = col

        col_label = culprit.replace('_', ' ').title()
        col_val = solar_preds[i] if 'solar' in culprit else wind_preds[i]
        bounds = iqr_bounds.get(culprit, {})

        anomalies.append({
            'variable':       col_label,
            'timestamp':      ts.isoformat() + 'Z',
            'value':          round(col_val, 4),
            'anomaly_score':  round(float(comp_score), 4),
            'severity':       severity_map[sev_i],
            'model':          'Ensemble (IF + PCA + OCSVM, majority vote)',
            'detector_votes': {
                'isolation_forest': if_pred == -1,
                'pca_reconstruction': pca_pred == -1,
                'one_class_svm': svm_pred == -1,
            },
            'bounds': {
                'lower': round(float(bounds.get('lower', 0)), 3),
                'upper': round(float(bounds.get('upper', 0)), 3),
            } if bounds else None,
            'type': 'predicted',
        })

    anomalies.sort(key=lambda x: x['anomaly_score'], reverse=True)
    return jsonify({
        'country':     country,
        'hours':       hours,
        'n_anomalies': len(anomalies),
        'anomalies':   anomalies[:30],
        'detectors':   ['Isolation Forest (n=100, contamination=0.05)',
                        'PCA Reconstruction (95% variance, threshold=95th pct)',
                        'One-Class SVM (RBF kernel, nu=0.05)'],
        'ensemble':    'Majority vote ≥ 2/3 detectors',
        'note':        f'Chapter 3.6.2 ensemble anomaly detection on {hours}h XGBoost forecast.',
    })

# Cache for loaded models
_anomaly_models = {}


def get_anomaly_detector(country: str, method: str = 'ensemble'):
    """
    Get or load anomaly detector for a country
    
    Args:
        country: Country name
        method: Detection method ('autoencoder', 'pca', 'svm', 'isolation_forest', 'ensemble')
        
    Returns:
        Trained detector or None if not found
    """
    cache_key = f"{country}_{method}"
    
    # Return cached model if exists
    if cache_key in _anomaly_models:
        return _anomaly_models[cache_key]
    
    # Try to load from disk
    model_dir = config.MODELS_DIR / country / 'anomaly'
    
    if method == 'ensemble':
        if (model_dir / 'ensemble_config.pkl').exists():
            # Load sample data to initialize
            processor = DataProcessor(country)
            data = processor.engineer_features()
            if data is not None:
                X_sample = data.select_dtypes(include=[np.number]).fillna(0).values[:10]
                detector = EnsembleAnomalyDetector(X_sample)
                detector.load(model_dir)
                _anomaly_models[cache_key] = detector
                return detector
    elif method == 'autoencoder':
        if (model_dir / 'autoencoder.h5').exists():
            detector = AutoencoderAnomalyDetector(input_dim=1)  # Will be overridden by load
            detector.load(model_dir / 'autoencoder')
            _anomaly_models[cache_key] = detector
            return detector
    elif method == 'pca':
        if (model_dir / 'pca.pkl').exists():
            detector = PCAAnomalyDetector()
            detector.load(model_dir / 'pca.pkl')
            _anomaly_models[cache_key] = detector
            return detector
    elif method == 'svm':
        if (model_dir / 'svm.pkl').exists():
            detector = OneClassSVMAnomalyDetector()
            detector.load(model_dir / 'svm.pkl')
            _anomaly_models[cache_key] = detector
            return detector
    elif method == 'isolation_forest':
        if (model_dir / 'isolation_forest.pkl').exists():
            detector = IsolationForestAnomalyDetector()
            detector.load(model_dir / 'isolation_forest.pkl')
            _anomaly_models[cache_key] = detector
            return detector
    
    return None


@anomaly_bp.route('/train', methods=['POST'])
@jwt_required()
def train_anomaly_detector():
    """
    Train anomaly detection models for a country
    
    Request body:
        {
            "country": "Nigeria",
            "method": "ensemble",  // or specific: "autoencoder", "pca", "svm", "isolation_forest"
            "contamination": 0.05,  // expected outlier ratio
            "threshold_percentile": 95  // for autoencoder/pca
        }
    """
    try:
        data = request.get_json()
        country = data.get('country', 'Nigeria')
        method = data.get('method', 'ensemble')
        contamination = data.get('contamination', 0.05)
        threshold_percentile = data.get('threshold_percentile', 95.0)
        
        # Load and prepare data
        processor = DataProcessor(country)
        df = processor.engineer_features()
        
        if df is None:
            return jsonify({
                'success': False,
                'message': f'No data available for {country}'
            }), 404
        
        # Select numeric features only
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        X = df[numeric_cols].fillna(0).values
        
        logger.info(f"Training {method} anomaly detector for {country} with {X.shape[0]} samples, {X.shape[1]} features")
        
        # Train based on method
        if method == 'ensemble':
            detector = EnsembleAnomalyDetector(X[:10], voting='majority')
            results = detector.train(X)
        elif method == 'autoencoder':
            detector = AutoencoderAnomalyDetector(
                input_dim=X.shape[1],
                latent_dim=max(8, X.shape[1] // 4),
                threshold_percentile=threshold_percentile
            )
            results = detector.train(X, epochs=50, verbose=0)
        elif method == 'pca':
            detector = PCAAnomalyDetector(
                n_components=0.95,
                threshold_percentile=threshold_percentile
            )
            results = detector.train(X)
        elif method == 'svm':
            detector = OneClassSVMAnomalyDetector(nu=contamination)
            results = detector.train(X)
        elif method == 'isolation_forest':
            detector = IsolationForestAnomalyDetector(contamination=contamination)
            results = detector.train(X)
        else:
            return jsonify({
                'success': False,
                'message': f'Unknown method: {method}'
            }), 400
        
        # Save model
        model_dir = config.MODELS_DIR / country / 'anomaly'
        model_dir.mkdir(parents=True, exist_ok=True)
        
        if method == 'ensemble':
            detector.save(model_dir)
        elif method == 'autoencoder':
            detector.save(model_dir / 'autoencoder')
        elif method == 'pca':
            detector.save(model_dir / 'pca.pkl')
        elif method == 'svm':
            detector.save(model_dir / 'svm.pkl')
        elif method == 'isolation_forest':
            detector.save(model_dir / 'isolation_forest.pkl')
        
        # Cache the model
        cache_key = f"{country}_{method}"
        _anomaly_models[cache_key] = detector
        
        return jsonify({
            'success': True,
            'message': f'{method.title()} anomaly detector trained successfully',
            'method': method,
            'country': country,
            'training_samples': int(X.shape[0]),
            'features': int(X.shape[1]),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Training error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@anomaly_bp.route('/detect', methods=['POST'])
@jwt_required()
def detect_anomalies():
    """
    Detect anomalies in recent data
    
    Request body:
        {
            "country": "Nigeria",
            "method": "ensemble",
            "recent_hours": 168  // analyze last 7 days
        }
    """
    try:
        data = request.get_json()
        country = data.get('country', 'Nigeria')
        method = data.get('method', 'ensemble')
        recent_hours = data.get('recent_hours', 168)
        
        # Load detector
        detector = get_anomaly_detector(country, method)
        
        if detector is None:
            return jsonify({
                'success': False,
                'message': f'No trained {method} model found for {country}. Please train first.'
            }), 404
        
        # Load recent data
        processor = DataProcessor(country)
        df = processor.engineer_features()
        
        if df is None:
            return jsonify({
                'success': False,
                'message': f'No data available for {country}'
            }), 404
        
        # Take most recent hours
        df_recent = df.tail(recent_hours)
        
        # Select numeric features
        numeric_cols = df_recent.select_dtypes(include=[np.number]).columns.tolist()
        X = df_recent[numeric_cols].fillna(0).values
        
        # Detect anomalies
        if method == 'ensemble':
            results = detector.predict(X)
            
            # Format response
            response = {
                'success': True,
                'method': 'ensemble',
                'country': country,
                'samples_analyzed': int(X.shape[0]),
                'ensemble': {
                    'n_anomalies': int(results['ensemble']['n_anomalies']),
                    'anomaly_ratio': float(results['ensemble']['anomaly_ratio']),
                    'voting_method': results['ensemble']['voting_method']
                },
                'individual_detectors': {}
            }
            
            for detector_name in ['autoencoder', 'pca', 'svm', 'isolation_forest']:
                response['individual_detectors'][detector_name] = {
                    'n_anomalies': int(results[detector_name]['n_anomalies']),
                    'anomaly_ratio': float(results[detector_name]['anomaly_ratio'])
                }
            
            # Add timestamps of anomalies if available
            if 'timestamp' in df_recent.columns:
                ensemble_anomaly_indices = np.where(results['ensemble']['is_anomaly'])[0]
                response['anomaly_timestamps'] = df_recent.iloc[ensemble_anomaly_indices]['timestamp'].astype(str).tolist()
            
        else:
            # Single detector
            anomaly_scores, is_anomaly = detector.predict(X)
            
            response = {
                'success': True,
                'method': method,
                'country': country,
                'samples_analyzed': int(X.shape[0]),
                'n_anomalies': int(np.sum(is_anomaly)),
                'anomaly_ratio': float(np.mean(is_anomaly)),
                'anomaly_score_stats': {
                    'min': float(anomaly_scores.min()),
                    'max': float(anomaly_scores.max()),
                    'mean': float(anomaly_scores.mean()),
                    'std': float(anomaly_scores.std())
                }
            }
            
            # Add timestamps
            if 'timestamp' in df_recent.columns:
                anomaly_indices = np.where(is_anomaly)[0]
                response['anomaly_timestamps'] = df_recent.iloc[anomaly_indices]['timestamp'].astype(str).tolist()
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Detection error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@anomaly_bp.route('/status', methods=['GET'])
@jwt_required()
def get_anomaly_status():
    """
    Check which anomaly detection models are trained
    
    Query params:
        ?country=Nigeria
    """
    try:
        country = request.args.get('country', 'Nigeria')
        
        model_dir = config.MODELS_DIR / country / 'anomaly'
        
        status = {
            'country': country,
            'models': {
                'ensemble': (model_dir / 'ensemble_config.pkl').exists(),
                'autoencoder': (model_dir / 'autoencoder.h5').exists(),
                'pca': (model_dir / 'pca.pkl').exists(),
                'svm': (model_dir / 'svm.pkl').exists(),
                'isolation_forest': (model_dir / 'isolation_forest.pkl').exists()
            }
        }
        
        status['any_trained'] = any(status['models'].values())
        status['all_trained'] = all(status['models'].values())
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@anomaly_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_anomalies():
    """
    Comprehensive anomaly analysis with detailed insights
    
    Request body:
        {
            "country": "Nigeria",
            "method": "ensemble",
            "recent_hours": 168
        }
    """
    try:
        data = request.get_json()
        country = data.get('country', 'Nigeria')
        method = data.get('method', 'ensemble')
        recent_hours = data.get('recent_hours', 168)
        
        # Get detection results
        detector = get_anomaly_detector(country, method)
        
        if detector is None:
            return jsonify({
                'success': False,
                'message': f'No trained {method} model found for {country}'
            }), 404
        
        # Load data
        processor = DataProcessor(country)
        df = processor.engineer_features()
        
        if df is None:
            return jsonify({
                'success': False,
                'message': f'No data available for {country}'
            }), 404
        
        df_recent = df.tail(recent_hours)
        numeric_cols = df_recent.select_dtypes(include=[np.number]).columns.tolist()
        X = df_recent[numeric_cols].fillna(0).values
        
        # Detect
        if method == 'ensemble':
            results = detector.predict(X)
            is_anomaly = results['ensemble']['is_anomaly']
        else:
            _, is_anomaly = detector.predict(X)
        
        # Analyze anomalous samples
        anomaly_indices = np.where(is_anomaly)[0]
        
        analysis = {
            'success': True,
            'country': country,
            'method': method,
            'total_samples': int(X.shape[0]),
            'n_anomalies': int(len(anomaly_indices)),
            'anomaly_ratio': float(len(anomaly_indices) / X.shape[0]),
            'anomalies': []
        }
        
        # Get details for each anomaly
        for idx in anomaly_indices[:20]:  # Limit to 20 most recent
            anomaly_info = {
                'index': int(idx),
                'features': {}
            }
            
            # Add timestamp if available
            if 'timestamp' in df_recent.columns:
                anomaly_info['timestamp'] = str(df_recent.iloc[idx]['timestamp'])
            
            # Add feature values
            for i, col in enumerate(numeric_cols[:10]):  # Limit to 10 features
                anomaly_info['features'][col] = float(X[idx, i])
            
            analysis['anomalies'].append(anomaly_info)
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
