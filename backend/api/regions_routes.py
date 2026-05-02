"""
Regions and Countries API Routes
Handles multi-country support with currencies and tariff systems
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent.parent.parent))

regions_bp = Blueprint('regions', __name__)
logger = logging.getLogger(__name__)

# Multi-country configuration
REGIONS_CONFIG = {
    'nigeria': {
        'name': 'Nigeria',
        'currency': '₦',
        'currency_code': 'NGN',
        'coordinates': {'lat': 9.0820, 'lon': 8.6753},
        'timezone': 'Africa/Lagos',
        'tariff_bands': {
            'Band A': {'rate': 225, 'supply_hours': 20, 'description': 'Premium supply (20+ hours/day)'},
            'Band B': {'rate': 63, 'supply_hours': 16, 'description': 'Good supply (16-20 hours/day)'},
            'Band C': {'rate': 50, 'supply_hours': 12, 'description': 'Average supply (12-16 hours/day)'},
            'Band D': {'rate': 43, 'supply_hours': 8, 'description': 'Low supply (8-12 hours/day)'},
            'Band E': {'rate': 40, 'supply_hours': 4, 'description': 'Minimal supply (<8 hours/day)'}
        },
        'renewable_potential': {
            'solar': 'High',
            'wind': 'Moderate',
            'hydro': 'High'
        }
    },
    'canada': {
        'name': 'Canada',
        'currency': 'CAD$',
        'currency_code': 'CAD',
        'coordinates': {'lat': 45.4215, 'lon': -75.6972},  # Ottawa
        'timezone': 'America/Toronto',
        'provinces': {
            'ON': {'name': 'Ontario', 'rate': 0.087, 'peak_rate': 0.151, 'off_peak_rate': 0.065},
            'QC': {'name': 'Quebec', 'rate': 0.073, 'peak_rate': 0.120, 'off_peak_rate': 0.053},
            'BC': {'name': 'British Columbia', 'rate': 0.094, 'peak_rate': 0.140, 'off_peak_rate': 0.071},
            'AB': {'name': 'Alberta', 'rate': 0.068, 'peak_rate': 0.180, 'off_peak_rate': 0.045},
            'MB': {'name': 'Manitoba', 'rate': 0.088, 'peak_rate': 0.130, 'off_peak_rate': 0.070}
        },
        'renewable_potential': {
            'solar': 'Moderate',
            'wind': 'High',
            'hydro': 'Very High'
        }
    },
    'australia': {
        'name': 'Australia',
        'currency': 'AUD$',
        'currency_code': 'AUD',
        'coordinates': {'lat': -33.8688, 'lon': 151.2093},  # Sydney
        'timezone': 'Australia/Sydney',
        'states': {
            'NSW': {'name': 'New South Wales', 'rate': 0.28, 'peak_rate': 0.50, 'off_peak_rate': 0.18},
            'VIC': {'name': 'Victoria', 'rate': 0.25, 'peak_rate': 0.45, 'off_peak_rate': 0.16},
            'QLD': {'name': 'Queensland', 'rate': 0.24, 'peak_rate': 0.47, 'off_peak_rate': 0.15},
            'SA': {'name': 'South Australia', 'rate': 0.36, 'peak_rate': 0.55, 'off_peak_rate': 0.22},
            'WA': {'name': 'Western Australia', 'rate': 0.29, 'peak_rate': 0.52, 'off_peak_rate': 0.19}
        },
        'renewable_potential': {
            'solar': 'Very High',
            'wind': 'High',
            'hydro': 'Low'
        }
    },
    'germany': {
        'name': 'Germany',
        'currency': '€',
        'currency_code': 'EUR',
        'coordinates': {'lat': 52.5200, 'lon': 13.4050},  # Berlin
        'timezone': 'Europe/Berlin',
        'pricing': {
            'residential': {'rate': 0.32, 'peak_rate': 0.42, 'off_peak_rate': 0.24},
            'industrial': {'rate': 0.18, 'peak_rate': 0.25, 'off_peak_rate': 0.14}
        },
        'renewable_potential': {
            'solar': 'Moderate',
            'wind': 'Very High',
            'hydro': 'Low'
        }
    }
}


@regions_bp.route('/list', methods=['GET'])
@jwt_required()
def list_regions():
    """
    Get list of supported regions/countries
    """
    try:
        regions_list = []
        for key, config in REGIONS_CONFIG.items():
            regions_list.append({
                'id': key,
                'name': config['name'],
                'currency': config['currency'],
                'currency_code': config['currency_code'],
                'coordinates': config['coordinates'],
                'timezone': config['timezone'],
                'renewable_potential': config['renewable_potential']
            })
        
        return jsonify({
            'regions': regions_list,
            'total': len(regions_list)
        }), 200
        
    except Exception as e:
        logger.error(f"List regions error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to retrieve regions'}), 500


@regions_bp.route('/<region_id>', methods=['GET'])
@jwt_required()
def get_region_details(region_id):
    """
    Get detailed information for a specific region
    """
    try:
        if region_id not in REGIONS_CONFIG:
            return jsonify({'error': f'Region {region_id} not found'}), 404
        
        return jsonify(REGIONS_CONFIG[region_id]), 200
        
    except Exception as e:
        logger.error(f"Get region details error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to retrieve region details'}), 500


@regions_bp.route('/<region_id>/tariff', methods=['GET'])
@jwt_required()
def get_tariff_rates(region_id):
    """
    Get electricity tariff rates for a region
    
    Query params:
    - band: Tariff band (Nigeria only)
    - province: Province/State code (Canada/Australia)
    - type: Customer type (Germany: residential/industrial)
    """
    try:
        if region_id not in REGIONS_CONFIG:
            return jsonify({'error': f'Region {region_id} not found'}), 404
        
        config = REGIONS_CONFIG[region_id]
        band = request.args.get('band')
        province = request.args.get('province')
        customer_type = request.args.get('type', 'residential')
        
        if region_id == 'nigeria':
            if 'tariff_bands' in config:
                if band:
                    if band in config['tariff_bands']:
                        return jsonify({
                            'region': region_id,
                            'band': band,
                            'tariff': config['tariff_bands'][band],
                            'currency': config['currency']
                        }), 200
                    else:
                        return jsonify({'error': f'Band {band} not found'}), 404
                else:
                    return jsonify({
                        'region': region_id,
                        'tariff_bands': config['tariff_bands'],
                        'currency': config['currency']
                    }), 200
        
        elif region_id in ['canada', 'australia']:
            location_key = 'provinces' if region_id == 'canada' else 'states'
            if location_key in config:
                if province:
                    if province in config[location_key]:
                        return jsonify({
                            'region': region_id,
                            'location': province,
                            'tariff': config[location_key][province],
                            'currency': config['currency']
                        }), 200
                    else:
                        return jsonify({'error': f'Location {province} not found'}), 404
                else:
                    return jsonify({
                        'region': region_id,
                        location_key: config[location_key],
                        'currency': config['currency']
                    }), 200
        
        elif region_id == 'germany':
            if 'pricing' in config:
                return jsonify({
                    'region': region_id,
                    'customer_type': customer_type,
                    'tariff': config['pricing'].get(customer_type, config['pricing']['residential']),
                    'currency': config['currency']
                }), 200
        
        return jsonify({'error': 'Tariff information not available'}), 404
        
    except Exception as e:
        logger.error(f"Get tariff rates error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to retrieve tariff rates'}), 500


@regions_bp.route('/<region_id>/calculate-cost', methods=['POST'])
@jwt_required()
def calculate_energy_cost(region_id):
    """
    Calculate energy cost based on region tariffs
    
    Request body:
    {
        "energy_kwh": float,
        "band": str (Nigeria),
        "province": str (Canada/Australia),
        "type": str (Germany),
        "time_of_use": {
            "peak_kwh": float,
            "off_peak_kwh": float
        }
    }
    """
    try:
        if region_id not in REGIONS_CONFIG:
            return jsonify({'error': f'Region {region_id} not found'}), 404
        
        data = request.get_json()
        energy_kwh = data.get('energy_kwh', 0)
        config = REGIONS_CONFIG[region_id]
        
        # Get tariff rate
        rate = 0
        breakdown = {}
        
        if region_id == 'nigeria':
            band = data.get('band', 'Band C')
            if band in config['tariff_bands']:
                rate = config['tariff_bands'][band]['rate'] / 100  # Convert kobo to Naira
                total_cost = energy_kwh * rate
                breakdown = {
                    'band': band,
                    'rate_per_kwh': rate,
                    'energy_kwh': energy_kwh,
                    'total_cost': round(total_cost, 2)
                }
        
        elif region_id in ['canada', 'australia']:
            province = data.get('province')
            location_key = 'provinces' if region_id == 'canada' else 'states'
            
            if province and province in config[location_key]:
                tariff = config[location_key][province]
                
                # Time-of-use calculation if provided
                if 'time_of_use' in data:
                    peak_kwh = data['time_of_use'].get('peak_kwh', 0)
                    off_peak_kwh = data['time_of_use'].get('off_peak_kwh', 0)
                    
                    peak_cost = peak_kwh * tariff['peak_rate']
                    off_peak_cost = off_peak_kwh * tariff['off_peak_rate']
                    total_cost = peak_cost + off_peak_cost
                    
                    breakdown = {
                        'location': province,
                        'peak_kwh': peak_kwh,
                        'peak_rate': tariff['peak_rate'],
                        'peak_cost': round(peak_cost, 2),
                        'off_peak_kwh': off_peak_kwh,
                        'off_peak_rate': tariff['off_peak_rate'],
                        'off_peak_cost': round(off_peak_cost, 2),
                        'total_cost': round(total_cost, 2)
                    }
                else:
                    rate = tariff['rate']
                    total_cost = energy_kwh * rate
                    breakdown = {
                        'location': province,
                        'rate_per_kwh': rate,
                        'energy_kwh': energy_kwh,
                        'total_cost': round(total_cost, 2)
                    }
        
        elif region_id == 'germany':
            customer_type = data.get('type', 'residential')
            tariff = config['pricing'][customer_type]
            
            # Time-of-use calculation if provided
            if 'time_of_use' in data:
                peak_kwh = data['time_of_use'].get('peak_kwh', 0)
                off_peak_kwh = data['time_of_use'].get('off_peak_kwh', 0)
                
                peak_cost = peak_kwh * tariff['peak_rate']
                off_peak_cost = off_peak_kwh * tariff['off_peak_rate']
                total_cost = peak_cost + off_peak_cost
                
                breakdown = {
                    'customer_type': customer_type,
                    'peak_kwh': peak_kwh,
                    'peak_rate': tariff['peak_rate'],
                    'peak_cost': round(peak_cost, 2),
                    'off_peak_kwh': off_peak_kwh,
                    'off_peak_rate': tariff['off_peak_rate'],
                    'off_peak_cost': round(off_peak_cost, 2),
                    'total_cost': round(total_cost, 2)
                }
            else:
                rate = tariff['rate']
                total_cost = energy_kwh * rate
                breakdown = {
                    'customer_type': customer_type,
                    'rate_per_kwh': rate,
                    'energy_kwh': energy_kwh,
                    'total_cost': round(total_cost, 2)
                }
        
        return jsonify({
            'region': region_id,
            'currency': config['currency'],
            'currency_code': config['currency_code'],
            **breakdown
        }), 200
        
    except Exception as e:
        logger.error(f"Calculate energy cost error: {e}", exc_info=True)
        return jsonify({'error': 'Cost calculation failed'}), 500
