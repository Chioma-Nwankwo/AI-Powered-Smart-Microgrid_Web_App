"""
Location Detection API Routes
Uses IP Geolocation to auto-detect user location
"""
from flask import Blueprint, request, jsonify
import requests
import sys
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent.parent.parent))

from config import config

location_bp = Blueprint('location', __name__)
logger = logging.getLogger(__name__)

IPGEOLOCATION_API_KEY = config.IPGEOLOCATION_API_KEY if hasattr(config, 'IPGEOLOCATION_API_KEY') else None


@location_bp.route('/detect', methods=['GET'])
def detect_location():
    """
    Auto-detect user location based on IP address
    
    Returns:
    - country: Country name
    - state: State/Province
    - city: City name
    - latitude: Latitude coordinate
    - longitude: Longitude coordinate
    - timezone: Timezone name
    """
    try:
        if not IPGEOLOCATION_API_KEY:
            # Return default/mock location if API key not configured
            return jsonify({
                'country': 'Nigeria',
                'state': 'Lagos',
                'city': 'Lagos',
                'latitude': 6.5244,
                'longitude': 3.3792,
                'timezone': 'Africa/Lagos',
                'currency': 'NGN',
                'currency_symbol': '₦',
                'note': 'Using default location (API key not configured)'
            }), 200
        
        # Get client IP address
        # Use X-Forwarded-For if behind proxy, otherwise use remote_addr
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # If localhost/private IP, use empty string to get location from public IP
        if ip.startswith('127.') or ip.startswith('192.168.') or ip == '::1':
            ip = ''
        
        # Call IP Geolocation API
        url = f'https://api.ipgeolocation.io/ipgeo'
        params = {
            'apiKey': IPGEOLOCATION_API_KEY,
            'ip': ip
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Extract location data
        location_data = {
            'country': data.get('country_name', 'Unknown'),
            'country_code': data.get('country_code2', ''),
            'state': data.get('state_prov', ''),
            'city': data.get('city', ''),
            'latitude': float(data.get('latitude', 0)),
            'longitude': float(data.get('longitude', 0)),
            'timezone': data.get('time_zone', {}).get('name', 'UTC'),
            'currency': data.get('currency', {}).get('code', 'USD'),
            'currency_symbol': data.get('currency', {}).get('symbol', '$'),
            'calling_code': data.get('calling_code', ''),
            'continent': data.get('continent_name', ''),
            'is_eu': data.get('is_eu', False)
        }
        
        logger.info(f"Location detected: {location_data['city']}, {location_data['country']}")
        
        return jsonify(location_data), 200
        
    except requests.RequestException as e:
        logger.error(f"IP Geolocation API error: {e}")
        return jsonify({
            'error': 'Failed to detect location',
            'country': 'Nigeria',  # Fallback
            'state': 'Lagos',
            'latitude': 6.5244,
            'longitude': 3.3792,
            'timezone': 'Africa/Lagos'
        }), 200  # Return 200 with fallback data instead of error
        
    except Exception as e:
        logger.error(f"Location detection error: {e}", exc_info=True)
        return jsonify({'error': 'Location detection failed'}), 500


@location_bp.route('/reverse', methods=['GET'])
def reverse_geocode():
    """
    Get location details from coordinates
    
    Query params:
    - lat: Latitude
    - lon: Longitude
    """
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        
        if not lat or not lon:
            return jsonify({'error': 'Latitude and longitude required'}), 400
        
        if not IPGEOLOCATION_API_KEY:
            return jsonify({
                'country': 'Nigeria',
                'state': 'Lagos',
                'city': 'Lagos'
            }), 200
        
        # Call IP Geolocation reverse geocoding API
        url = 'https://api.ipgeolocation.io/timezone'
        params = {
            'apiKey': IPGEOLOCATION_API_KEY,
            'lat': lat,
            'long': lon
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        return jsonify({
            'timezone': data.get('timezone', 'UTC'),
            'timezone_offset': data.get('timezone_offset', 0),
            'date_time': data.get('date_time', ''),
            'coordinates': {
                'latitude': lat,
                'longitude': lon
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Reverse geocoding error: {e}", exc_info=True)
        return jsonify({'error': 'Reverse geocoding failed'}), 500


@location_bp.route('/countries', methods=['GET'])
def list_countries():
    """
    List supported countries with their details
    """
    try:
        countries = [
            {
                'name': 'Nigeria',
                'code': 'NG',
                'currency': 'NGN',
                'currency_symbol': '₦',
                'regions': ['Lagos', 'Abuja', 'Kano', 'Port Harcourt', 'Ibadan'],
                'coordinates': {'lat': 9.0820, 'lon': 8.6753}
            },
            {
                'name': 'Canada',
                'code': 'CA',
                'currency': 'CAD',
                'currency_symbol': 'CAD$',
                'regions': ['Ontario', 'Quebec', 'British Columbia', 'Alberta', 'Manitoba'],
                'coordinates': {'lat': 45.4215, 'lon': -75.6972}
            },
            {
                'name': 'Australia',
                'code': 'AU',
                'currency': 'AUD',
                'currency_symbol': 'AUD$',
                'regions': ['New South Wales', 'Victoria', 'Queensland', 'South Australia', 'Western Australia'],
                'coordinates': {'lat': -33.8688, 'lon': 151.2093}
            },
            {
                'name': 'Germany',
                'code': 'DE',
                'currency': 'EUR',
                'currency_symbol': '€',
                'regions': ['Berlin', 'Bavaria', 'Hamburg', 'Hesse', 'North Rhine-Westphalia'],
                'coordinates': {'lat': 52.5200, 'lon': 13.4050}
            }
        ]
        
        return jsonify({'countries': countries}), 200
        
    except Exception as e:
        logger.error(f"List countries error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to list countries'}), 500
