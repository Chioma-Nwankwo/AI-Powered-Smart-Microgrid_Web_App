"""
User API Routes
Handles user profile and settings
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from auth.user_manager import user_manager
from database.models import User
from config import config
import logging

user_bp = Blueprint('user', __name__)
logger = logging.getLogger(__name__)


@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile"""
    try:
        user_id = get_jwt_identity()
        user_data = User.get_by_user_id(user_id)
        
        if user_data:
            return jsonify({
                'user_id': user_data['user_id'],
                'email': user_data['email'],
                'country': user_data['country'],
                'state': user_data['state'],
                'building_type': user_data['building_type'],
                'address': user_data['address'],
                'created_at': str(user_data.get('created_at', '')),
                'last_login': str(user_data.get('last_login', ''))
            }), 200
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        return jsonify({'error': 'Failed to fetch profile'}), 500


@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        allowed = ['country', 'state', 'building_type', 'address',
                   'electricity_rate', 'peak_demand_kw', 'daily_kwh', 'appliances']
        update_data = {k: v for k, v in data.items() if k in allowed and v is not None}

        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Update electricity rate if country/state changed
        if 'country' in update_data or 'state' in update_data:
            user = User.get_by_user_id(user_id)
            country = update_data.get('country', user['country'] if user else 'Nigeria')
            state   = update_data.get('state',   user['state']   if user else 'FCT')
            update_data['electricity_rate'] = config.get_electricity_rate(country, state)

        success = User.update_profile(user_id, update_data)

        if success:
            user = User.get_by_user_id(user_id)
            return jsonify({
                'message': 'Profile updated successfully',
                'user': {
                    'user_id':       user['user_id'],
                    'email':         user['email'],
                    'country':       user['country'],
                    'state':         user['state'],
                    'building_type': user['building_type'],
                    'address':       user['address'],
                }
            }), 200
        else:
            return jsonify({'error': 'Update failed'}), 500

    except Exception as e:
        logger.error(f"Update profile error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update profile'}), 500


@user_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_settings():
    """Get user settings (theme, language, etc.)"""
    try:
        user_id = get_jwt_identity()
        
        # TODO: Store user preferences in database
        # For now, return default settings
        
        return jsonify({
            'theme': 'light',
            'language': 'en',
            'notifications': True,
            'currency': config.CURRENCY_SYMBOLS.get('Nigeria', '$')
        }), 200
        
    except Exception as e:
        logger.error(f"Get settings error: {e}")
        return jsonify({'error': 'Failed to fetch settings'}), 500


@user_bp.route('/settings', methods=['PUT'])
@jwt_required()
def update_settings():
    """Update user settings"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # TODO: Store settings in database or session
        
        return jsonify({
            'message': 'Settings updated successfully',
            'settings': data
        }), 200
        
    except Exception as e:
        logger.error(f"Update settings error: {e}")
        return jsonify({'error': 'Failed to update settings'}), 500
