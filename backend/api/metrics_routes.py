"""
Performance Metrics API Routes
Provides forecasting, optimization, and anomaly detection metrics
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
from pathlib import Path
import numpy as np
import logging

sys.path.append(str(Path(__file__).parent.parent.parent))

from models.performance_metrics import ForecastingMetrics, OptimizationMetrics, AnomalyDetectionMetrics

metrics_bp = Blueprint('metrics', __name__)
logger = logging.getLogger(__name__)


@metrics_bp.route('/forecasting', methods=['POST'])
@jwt_required()
def evaluate_forecasting():
    """
    Evaluate forecasting performance
    
    Request body:
    {
        "y_true": [float],  // Actual values
        "y_pred": [float],  // Predicted values
        "y_train": [float]  // Optional: Training data for MASE calculation
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if 'y_true' not in data or 'y_pred' not in data:
            return jsonify({'error': 'Missing y_true or y_pred'}), 400
        
        y_true = np.array(data['y_true'])
        y_pred = np.array(data['y_pred'])
        y_train = np.array(data['y_train']) if 'y_train' in data else None
        
        if len(y_true) != len(y_pred):
            return jsonify({'error': 'y_true and y_pred must have same length'}), 400
        
        # Calculate all forecasting metrics
        metrics = ForecastingMetrics.compute_all(y_true, y_pred, y_train)
        
        logger.info(f"Forecasting metrics calculated for user {user_id}")
        
        return jsonify({
            'message': 'Metrics calculated successfully',
            'metrics': metrics
        }), 200
        
    except Exception as e:
        logger.error(f"Forecasting metrics error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to calculate metrics'}), 500


@metrics_bp.route('/optimization', methods=['POST'])
@jwt_required()
def evaluate_optimization():
    """
    Evaluate optimization performance
    
    Request body:
    {
        "solar_generation": [float],
        "load_demand": [float],
        "battery_charged": [float],
        "battery_discharged": [float],
        "grid_import": [float],
        "optimized_cost": float,
        "baseline_cost": float,
        "depth_of_discharge": [float]
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        required_fields = ['solar_generation', 'load_demand', 'battery_charged', 
                          'battery_discharged', 'grid_import', 'optimized_cost', 
                          'baseline_cost', 'depth_of_discharge']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Calculate optimization metrics
        metrics = OptimizationMetrics.compute_all(
            solar=np.array(data['solar_generation']),
            load=np.array(data['load_demand']),
            battery_charged=np.array(data['battery_charged']),
            battery_discharged=np.array(data['battery_discharged']),
            grid_import=np.array(data['grid_import']),
            optimized_cost=data['optimized_cost'],
            baseline_cost=data['baseline_cost'],
            dod=np.array(data['depth_of_discharge'])
        )
        
        logger.info(f"Optimization metrics calculated for user {user_id}")
        
        return jsonify({
            'message': 'Optimization metrics calculated successfully',
            'metrics': metrics
        }), 200
        
    except Exception as e:
        logger.error(f"Optimization metrics error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to calculate optimization metrics'}), 500


@metrics_bp.route('/anomaly-detection', methods=['POST'])
@jwt_required()
def evaluate_anomaly_detection():
    """
    Evaluate anomaly detection performance
    
    Request body:
    {
        "y_true": [int],  // True labels (0 = normal, 1 = anomaly)
        "y_pred": [int],  // Predicted labels
        "y_scores": [float]  // Optional: Prediction scores for ROC-AUC
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if 'y_true' not in data or 'y_pred' not in data:
            return jsonify({'error': 'Missing y_true or y_pred'}), 400
        
        y_true = np.array(data['y_true'])
        y_pred = np.array(data['y_pred'])
        y_scores = np.array(data['y_scores']) if 'y_scores' in data else None
        
        if len(y_true) != len(y_pred):
            return jsonify({'error': 'y_true and y_pred must have same length'}), 400
        
        # Calculate anomaly detection metrics
        metrics = AnomalyDetectionMetrics.compute_all(y_true, y_pred, y_scores)
        
        logger.info(f"Anomaly detection metrics calculated for user {user_id}")
        
        return jsonify({
            'message': 'Anomaly detection metrics calculated successfully',
            'metrics': metrics
        }), 200
        
    except Exception as e:
        logger.error(f"Anomaly detection metrics error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to calculate anomaly detection metrics'}), 500


@metrics_bp.route('/model-comparison', methods=['POST'])
@jwt_required()
def compare_models():
    """
    Compare performance of multiple models
    
    Request body:
    {
        "models": [
            {
                "name": "XGBoost",
                "y_pred": [float]
            },
            {
                "name": "Random Forest",
                "y_pred": [float]
            }
        ],
        "y_true": [float],
        "y_train": [float]
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if 'models' not in data or 'y_true' not in data:
            return jsonify({'error': 'Missing models or y_true'}), 400
        
        y_true = np.array(data['y_true'])
        y_train = np.array(data['y_train']) if 'y_train' in data else None
        
        results = []
        for model in data['models']:
            if 'name' not in model or 'y_pred' not in model:
                continue
            
            y_pred = np.array(model['y_pred'])
            
            if len(y_true) != len(y_pred):
                continue
            
            metrics = ForecastingMetrics.compute_all(y_true, y_pred, y_train)
            results.append({
                'model_name': model['name'],
                'metrics': metrics
            })
        
        # Rank models by R²
        results.sort(key=lambda x: x['metrics']['R2'], reverse=True)
        
        logger.info(f"Model comparison completed for user {user_id}")
        
        return jsonify({
            'message': 'Model comparison completed',
            'results': results,
            'best_model': results[0]['model_name'] if results else None
        }), 200
        
    except Exception as e:
        logger.error(f"Model comparison error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compare models'}), 500


@metrics_bp.route('/ensemble-weights', methods=['POST'])
@jwt_required()
def calculate_ensemble_weights():
    """
    Calculate optimal ensemble weights based on model performance
    
    Request body:
    {
        "models": [
            {
                "name": "XGBoost",
                "y_pred": [float],
                "weight": float (optional)
            }
        ],
        "y_true": [float]
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if 'models' not in data or 'y_true' not in data:
            return jsonify({'error': 'Missing models or y_true'}), 400
        
        y_true = np.array(data['y_true'])
        
        # Calculate MAE for each model
        model_scores = []
        for model in data['models']:
            if 'name' not in model or 'y_pred' not in model:
                continue
            
            y_pred = np.array(model['y_pred'])
            mae = ForecastingMetrics.mae(y_true, y_pred)
            
            model_scores.append({
                'name': model['name'],
                'mae': mae,
                'y_pred': y_pred
            })
        
        # Calculate weights inversely proportional to MAE
        total_inverse_mae = sum(1 / score['mae'] for score in model_scores)
        weights = []
        
        for score in model_scores:
            weight = (1 / score['mae']) / total_inverse_mae
            weights.append({
                'model': score['name'],
                'weight': round(weight, 4),
                'mae': round(score['mae'], 4)
            })
        
        # Calculate weighted ensemble prediction
        ensemble_pred = np.zeros_like(y_true, dtype=float)
        for score, weight_info in zip(model_scores, weights):
            ensemble_pred += score['y_pred'] * weight_info['weight']
        
        # Calculate ensemble metrics
        ensemble_metrics = ForecastingMetrics.compute_all(y_true, ensemble_pred)
        
        logger.info(f"Ensemble weights calculated for user {user_id}")
        
        return jsonify({
            'message': 'Ensemble weights calculated',
            'weights': weights,
            'ensemble_metrics': ensemble_metrics
        }), 200
        
    except Exception as e:
        logger.error(f"Ensemble weights calculation error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to calculate ensemble weights'}), 500
