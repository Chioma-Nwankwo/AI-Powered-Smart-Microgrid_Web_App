"""
Data API Routes
Handles historical data and analytics
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from data_loader import data_loader
from config import config
import logging

data_bp = Blueprint('data', __name__)
logger = logging.getLogger(__name__)


@data_bp.route('/historical', methods=['GET'])
@jwt_required()
def get_historical():
    """Get historical data for user's country"""
    try:
        user_id = get_jwt_identity()
        
        country = request.args.get('country', 'Nigeria')
        hours = int(request.args.get('hours', 168))  # Default 1 week
        
        # Get recent data
        df = data_loader.get_recent_data(country, hours=hours)
        
        if df is not None:
            # Convert to JSON-friendly format
            data = {
                'timestamps': df['time'].astype(str).tolist() if 'time' in df.columns else [],
                'solar_radiation': df['solar_radiation_wm2'].tolist() if 'solar_radiation_wm2' in df.columns else [],
                'temperature': df['temperature_celsius'].tolist() if 'temperature_celsius' in df.columns else [],
                'wind_speed': df['wind_speed'].tolist() if 'wind_speed' in df.columns else []
            }
            
            return jsonify({
                'country': country,
                'hours': hours,
                'data': data
            }), 200
        else:
            return jsonify({'error': 'No data available for country'}), 404
            
    except Exception as e:
        logger.error(f"Historical data error: {e}")
        return jsonify({'error': 'Failed to fetch historical data'}), 500


@data_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_summary():
    """Get data summary for country"""
    try:
        country = request.args.get('country', 'Nigeria')
        
        summary = data_loader.get_data_summary(country)
        
        if summary:
            return jsonify(summary), 200
        else:
            return jsonify({'error': 'No data available'}), 404
            
    except Exception as e:
        logger.error(f"Summary error: {e}")
        return jsonify({'error': 'Failed to fetch summary'}), 500


@data_bp.route('/countries', methods=['GET'])
def get_countries():
    """Get list of available countries"""
    return jsonify({
        'countries': config.COUNTRIES,
        'currency_symbols': config.CURRENCY_SYMBOLS
    }), 200


@data_bp.route('/states', methods=['GET'])
def get_states():
    """Get states for a country"""
    country = request.args.get('country', 'Nigeria')
    
    states = config.STATES.get(country, [])
    
    return jsonify({
        'country': country,
        'states': states
    }), 200
