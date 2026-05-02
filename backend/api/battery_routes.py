"""
Battery Optimization API Routes
Handles battery scheduling, SOC monitoring, and optimization
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent.parent))

from models.optimization import BatteryOptimizer
from config import config
import logging

battery_bp = Blueprint('battery', __name__)
logger = logging.getLogger(__name__)


@battery_bp.route('/optimize', methods=['POST'])
@jwt_required()
def optimize_battery():
    """
    Optimize battery charge/discharge schedule
    
    Request body:
    {
        "solar_forecast": [float],  // 24-hour solar generation forecast (MW)
        "load_forecast": [float],   // 24-hour load demand forecast (MW)
        "battery_capacity": float,  // Battery capacity (MWh)
        "initial_soc": float,       // Initial state of charge (MWh)
        "max_charge_rate": float,   // Max charge rate (MW)
        "max_discharge_rate": float,// Max discharge rate (MW)
        "grid_price": [float]       // Grid electricity price per hour ($/MWh)
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required = ['solar_forecast', 'load_forecast', 'battery_capacity', 
                   'initial_soc', 'max_charge_rate', 'max_discharge_rate', 'grid_price']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate array lengths
        if len(data['solar_forecast']) != 24 or len(data['load_forecast']) != 24 or len(data['grid_price']) != 24:
            return jsonify({'error': 'Forecast arrays must have 24 hours of data'}), 400
        
        # Create battery optimizer
        optimizer = BatteryOptimizer(
            battery_capacity=data['battery_capacity'],
            max_charge_rate=data['max_charge_rate'],
            max_discharge_rate=data['max_discharge_rate'],
            charge_efficiency=data.get('charge_efficiency', 0.95),
            discharge_efficiency=data.get('discharge_efficiency', 0.95)
        )
        
        # Run optimization
        result = optimizer.optimize(
            solar_forecast=np.array(data['solar_forecast']),
            load_forecast=np.array(data['load_forecast']),
            initial_soc=data['initial_soc'],
            grid_price=np.array(data['grid_price'])
        )
        
        if result['status'] == 'optimal':
            logger.info(f"Battery optimization successful for user {user_id}")
            
            return jsonify({
                'message': 'Optimization successful',
                'schedule': {
                    'charge': result['charge'].tolist(),
                    'discharge': result['discharge'].tolist(),
                    'soc': result['soc'].tolist(),
                    'grid_import': result['grid_import'].tolist(),
                    'grid_export': result['grid_export'].tolist()
                },
                'metrics': {
                    'total_cost': float(result['total_cost']),
                    'energy_from_grid': float(np.sum(result['grid_import'])),
                    'energy_to_grid': float(np.sum(result['grid_export'])),
                    'renewable_usage': float(result.get('renewable_usage', 0)),
                    'battery_cycles': float(result.get('battery_cycles', 0))
                }
            }), 200
        else:
            return jsonify({
                'error': 'Optimization failed',
                'details': result.get('message', 'Unknown error')
            }), 400
            
    except Exception as e:
        logger.error(f"Battery optimization error: {e}", exc_info=True)
        return jsonify({'error': 'Optimization failed'}), 500


@battery_bp.route('/soc', methods=['GET'])
@jwt_required()
def get_battery_soc():
    """
    Get current battery state of charge and history
    
    Query params:
    - hours: Number of hours of history to retrieve (default: 24)
    """
    try:
        user_id = get_jwt_identity()
        hours = request.args.get('hours', 24, type=int)
        
        # In a real system, this would query from database
        # For now, return mock data
        current_time = pd.Timestamp.now()
        time_range = pd.date_range(end=current_time, periods=hours, freq='H')
        
        # Mock SOC data (would come from battery management system)
        soc_values = np.random.uniform(20, 95, size=hours)
        
        return jsonify({
            'current_soc': float(soc_values[-1]),
            'battery_capacity': 100.0,  # MWh
            'charge_rate': 50.0,  # MW
            'discharge_rate': 50.0,  # MW
            'history': {
                'timestamps': [t.isoformat() for t in time_range],
                'soc': soc_values.tolist(),
                'charge_power': (np.random.uniform(0, 50, size=hours) * (np.random.rand(hours) > 0.7)).tolist(),
                'discharge_power': (np.random.uniform(0, 50, size=hours) * (np.random.rand(hours) > 0.7)).tolist()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"SOC retrieval error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to retrieve SOC data'}), 500


@battery_bp.route('/metrics', methods=['GET'])
@jwt_required()
def get_battery_metrics():
    """
    Get battery performance metrics
    
    Returns:
    - total_cycles: Total battery charge/discharge cycles
    - efficiency: Average round-trip efficiency
    - capacity_degradation: Capacity loss percentage
    - cost_savings: Total cost savings from battery usage (currency)
    - renewable_stored: Total renewable energy stored (MWh)
    """
    try:
        user_id = get_jwt_identity()
        
        # Mock metrics (would come from database aggregation)
        metrics = {
            'total_cycles': 245,
            'average_efficiency': 92.5,
            'capacity_degradation': 2.3,  # %
            'cost_savings': 15420.50,  # currency
            'renewable_stored': 1250.8,  # MWh
            'grid_independence': 68.5,  # %
            'peak_shaving': 450.2  # MWh
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Battery metrics error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to retrieve metrics'}), 500
