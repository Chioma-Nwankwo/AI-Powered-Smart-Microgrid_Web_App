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

# Fitted detector cache: (country, n_rows) → trained detector set.
# Populated at startup by _prewarm thread so first HTTP request is instant.
_detector_cache: dict = {}

_DETECTOR_COUNTRIES = ['nigeria', 'australia', 'germany', 'canada']
_FEAT_BASE = ['solar_radiation_wm2', 'wind_speed']
_FEAT_EXTRA = ['temperature_celsius', 'pressure', 'precipitation_mm']


def _train_detectors(country: str, hist_df) -> dict:
    """Fit all 4 detectors on hist_df and return a cache-entry dict."""
    from sklearn.ensemble import IsolationForest
    from sklearn.decomposition import PCA
    from sklearn.svm import OneClassSVM
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler

    feat_cols = [c for c in _FEAT_BASE + _FEAT_EXTRA if c in hist_df.columns]
    # Replace Inf/-Inf with 0 before filling NaN — StandardScaler throws on Inf
    X = (hist_df[feat_cols]
         .replace([np.inf, -np.inf], np.nan)
         .fillna(0)
         .values.astype(float))

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    iso = IsolationForest(contamination=0.05, random_state=42, n_estimators=50)
    iso.fit(Xs)

    pca = PCA(n_components=min(3, Xs.shape[1]))
    pca_recon_err = np.mean((Xs - pca.inverse_transform(pca.fit_transform(Xs))) ** 2, axis=1)
    pca_thr = float(np.percentile(pca_recon_err, 95))

    # Cap at 500 rows: RBF kernel is O(n²), so 1440 rows → ~60 s on Render free CPU.
    # 500 rows (≈21 days) is representative enough and trains in < 2 s.
    Xs_svm = Xs[-500:] if len(Xs) > 500 else Xs
    svm = OneClassSVM(kernel='rbf', nu=0.05, gamma='scale', max_iter=200)
    svm.fit(Xs_svm)

    nf = Xs.shape[1]
    ae = MLPRegressor(
        hidden_layer_sizes=(nf * 2, max(2, nf // 2), nf * 2),
        activation='tanh', max_iter=100, random_state=42,
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=5,
    )
    ae.fit(Xs, Xs)
    ae_thr = float(np.percentile(np.mean((Xs - ae.predict(Xs)) ** 2, axis=1), 95))

    iqr = {}
    for col in _FEAT_BASE:
        if col in hist_df.columns:
            s = hist_df[col].dropna()
            Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
            IQR = Q3 - Q1
            iqr[col] = {'lower': Q1 - 1.5*IQR, 'upper': Q3 + 1.5*IQR,
                        'median': float(s.median()), 'iqr': max(float(IQR), 1e-9)}

    logger.info("Detectors trained for %s (%d rows, %d features)", country, len(X), nf)
    return dict(scaler=scaler, feat_cols=feat_cols,
                iso=iso, pca=pca, pca_thr=pca_thr,
                svm=svm, ae=ae, ae_thr=ae_thr, iqr=iqr)


def _prewarm():
    """Train detectors for all countries at startup so the first request is instant."""
    import time, threading
    time.sleep(8)  # wait for data_loader/CSVs to be ready
    try:
        from data_loader import data_loader as dl
        for country in _DETECTOR_COUNTRIES:
            try:
                hist_df = dl.get_latest_data(country, hours=1440)
                if hist_df is None or hist_df.empty or len(hist_df) < 50:
                    continue
                key = (country, len(hist_df))
                if key not in _detector_cache:
                    _detector_cache[key] = _train_detectors(country, hist_df)
            except Exception as exc:
                logger.warning("Pre-warm failed for %s: %s", country, exc)
    except Exception as exc:
        logger.warning("Pre-warm thread error: %s", exc)


import threading as _threading
_threading.Thread(target=_prewarm, daemon=True, name="anomaly-prewarm").start()


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
    Chapter 3.6.2 ensemble: Isolation Forest + PCA + One-Class SVM + Autoencoder.
    Fitted on 1440h historical ERA5 data; evaluated on the most recent `hours` rows
    of the same historical data so real extreme-weather events are detected.
    Majority vote ≥2/4 detectors flags an anomaly.
    """
    from data_loader import data_loader as dl
    from datetime import timezone

    country = request.args.get('country', 'nigeria').lower()
    hours   = int(request.args.get('hours', 48))

    # ── 1. Load historical data (training window + evaluation window) ──
    train_hours = max(hours * 6, 1440)
    hist_df = dl.get_latest_data(country, hours=train_hours)

    if hist_df is None or hist_df.empty or len(hist_df) < 50:
        return jsonify({'anomalies': [], 'country': country, 'hours': hours,
                        'detectors': [], 'note': 'Insufficient historical data'})

    # ── 2. Get cached detectors (or train if pre-warm not finished yet) ─
    cache_key = (country, len(hist_df))
    if cache_key not in _detector_cache:
        logger.info("Cache miss — training detectors for %s on request", country)
        _detector_cache[cache_key] = _train_detectors(country, hist_df)

    det        = _detector_cache[cache_key]
    scaler     = det['scaler']
    hist_cols  = det['feat_cols']
    iso_forest = det['iso']
    pca        = det['pca'];   pca_threshold = det['pca_thr']
    ocsvm      = det['svm']
    ae         = det['ae'];    ae_threshold  = det['ae_thr']
    iqr_bounds = det['iqr']

    # ── 3. Evaluate the most recent `hours` rows of real historical data ─
    eval_df = hist_df.tail(hours).copy()

    severity_map = {0: 'low', 1: 'medium', 2: 'high', 3: 'critical'}
    anomalies = []

    for row_i in range(len(eval_df)):
        row = eval_df.iloc[row_i]

        # Build feature vector from actual historical values
        feat_vals = []
        for col in hist_cols:
            raw = row[col] if col in eval_df.columns else 0.0
            raw = float(raw) if not (raw != raw or np.isinf(raw)) else 0.0
            feat_vals.append(raw)

        X_point = scaler.transform([feat_vals])

        # Run 4 detectors
        if_pred   = iso_forest.predict(X_point)[0]
        if_score  = -iso_forest.score_samples(X_point)[0]

        pca_recon = pca.inverse_transform(pca.transform(X_point))
        pca_err   = float(np.mean((X_point - pca_recon) ** 2))
        pca_pred  = -1 if pca_err > pca_threshold else 1

        svm_pred  = ocsvm.predict(X_point)[0]
        svm_score = -ocsvm.score_samples(X_point)[0]

        ae_recon_pt = ae.predict(X_point)
        ae_err      = float(np.mean((X_point - ae_recon_pt) ** 2))
        ae_pred     = -1 if ae_err > ae_threshold else 1

        votes = sum(1 for p in [if_pred, pca_pred, svm_pred, ae_pred] if p == -1)
        is_anomaly = votes >= 2

        if not is_anomaly:
            continue

        comp_score = (
            if_score
            + (pca_err / max(pca_threshold, 1e-9))
            + max(0, svm_score)
            + (ae_err / max(ae_threshold, 1e-9))
        ) / 4.0
        sev_i = min(3, int(comp_score * 4))

        # Variable attribution: which monitored variable deviated most
        max_dev, culprit = 0.0, hist_cols[0]
        for col in hist_cols:
            val = feat_vals[hist_cols.index(col)]
            if col in iqr_bounds:
                b = iqr_bounds[col]
                dev = max(0.0, val - b['upper'], b['lower'] - val) / b['iqr']
                if dev > max_dev:
                    max_dev = dev
                    culprit = col

        col_val = feat_vals[hist_cols.index(culprit)] if culprit in hist_cols else 0.0
        bounds  = iqr_bounds.get(culprit, {})

        # Resolve timestamp
        ts_raw = row.get('timestamp') if 'timestamp' in eval_df.columns else None
        if ts_raw is not None:
            try:
                ts_str = pd.Timestamp(ts_raw).isoformat() + 'Z'
            except Exception:
                ts_str = str(ts_raw)
        else:
            ts_str = None

        anomalies.append({
            'variable':       culprit.replace('_', ' ').title(),
            'timestamp':      ts_str,
            'value':          round(col_val, 4),
            'anomaly_score':  round(float(comp_score), 4),
            'severity':       severity_map[sev_i],
            'model':          'Ensemble (IF + PCA + OCSVM + AE, majority vote)',
            'detector_votes': {
                'isolation_forest':   if_pred  == -1,
                'pca_reconstruction': pca_pred == -1,
                'one_class_svm':      svm_pred == -1,
                'autoencoder':        ae_pred  == -1,
            },
            'bounds': {
                'lower': round(float(bounds.get('lower', 0)), 3),
                'upper': round(float(bounds.get('upper', 0)), 3),
            } if bounds else None,
            'type': 'historical',
        })

    anomalies.sort(key=lambda x: x['anomaly_score'], reverse=True)
    return jsonify({
        'country':     country,
        'hours':       hours,
        'n_anomalies': len(anomalies),
        'anomalies':   anomalies[:30],
        'detectors':   ['Isolation Forest (n=50, contamination=0.05)',
                        'PCA Reconstruction (threshold=95th pct)',
                        'One-Class SVM (RBF kernel, nu=0.05)',
                        'Autoencoder MLP (threshold=95th pct)'],
        'ensemble':    'Majority vote ≥ 2/4 detectors',
        'note':        f'Anomaly detection on the most recent {hours}h of historical ERA5 data.',
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
