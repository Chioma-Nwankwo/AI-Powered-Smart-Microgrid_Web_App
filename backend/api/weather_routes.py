"""
Weather API Routes
Integrates with OpenWeatherMap API for real-time weather data
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

sys.path.append(str(Path(__file__).parent.parent.parent))

from config import config

weather_bp = Blueprint('weather', __name__)
logger = logging.getLogger(__name__)

# OpenWeatherMap API configuration
OPENWEATHER_API_KEY = config.OPENWEATHER_API_KEY if hasattr(config, 'OPENWEATHER_API_KEY') else None
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


@weather_bp.route('/current', methods=['GET'])
@jwt_required()
def get_current_weather():
    """
    Get current weather for a location
    
    Query params:
    - lat: Latitude
    - lon: Longitude
    OR
    - city: City name
    - country: Country code (optional)
    """
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        city = request.args.get('city')
        country = request.args.get('country')
        
        if not OPENWEATHER_API_KEY:
            # Return mock data if API key not configured
            return jsonify({
                'temperature': 25.5,
                'feels_like': 26.2,
                'humidity': 65,
                'wind_speed': 3.5,
                'wind_direction': 180,
                'cloud_cover': 20,
                'pressure': 1013,
                'visibility': 10000,
                'weather': 'Clear',
                'description': 'clear sky',
                'icon': '01d',
                'sunrise': (datetime.now().replace(hour=6, minute=30)).isoformat(),
                'sunset': (datetime.now().replace(hour=18, minute=45)).isoformat()
            }), 200
        
        # Build API request
        params = {'appid': OPENWEATHER_API_KEY, 'units': 'metric'}
        
        if lat and lon:
            params['lat'] = lat
            params['lon'] = lon
        elif city:
            params['q'] = f"{city},{country}" if country else city
        else:
            return jsonify({'error': 'Must provide lat/lon or city'}), 400
        
        # Call OpenWeatherMap API
        response = requests.get(f"{OPENWEATHER_BASE_URL}/weather", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parse response
        weather_data = {
            'temperature': data['main']['temp'],
            'feels_like': data['main']['feels_like'],
            'humidity': data['main']['humidity'],
            'wind_speed': data['wind']['speed'],
            'wind_direction': data['wind'].get('deg', 0),
            'cloud_cover': data['clouds']['all'],
            'pressure': data['main']['pressure'],
            'visibility': data.get('visibility', 10000),
            'weather': data['weather'][0]['main'],
            'description': data['weather'][0]['description'],
            'icon': data['weather'][0]['icon'],
            'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).isoformat(),
            'sunset': datetime.fromtimestamp(data['sys']['sunset']).isoformat(),
            'location': {
                'name': data['name'],
                'country': data['sys']['country'],
                'lat': data['coord']['lat'],
                'lon': data['coord']['lon']
            }
        }
        
        return jsonify(weather_data), 200
        
    except requests.RequestException as e:
        logger.error(f"Weather API error: {e}")
        return jsonify({'error': 'Failed to fetch weather data'}), 500
    except Exception as e:
        logger.error(f"Weather processing error: {e}", exc_info=True)
        return jsonify({'error': 'Weather data processing failed'}), 500


@weather_bp.route('/forecast', methods=['GET'])
@jwt_required()
def get_weather_forecast():
    """
    Get 5-day weather forecast
    
    Query params:
    - lat: Latitude
    - lon: Longitude
    OR
    - city: City name
    - country: Country code (optional)
    """
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        city = request.args.get('city')
        country = request.args.get('country')
        
        if not OPENWEATHER_API_KEY:
            # Return mock forecast data
            forecast_data = []
            base_time = datetime.now()
            for i in range(40):  # 5 days, 3-hour intervals
                forecast_data.append({
                    'timestamp': (base_time + timedelta(hours=i*3)).isoformat(),
                    'temperature': 20 + (i % 8) * 2,
                    'weather': 'Clear' if i % 3 == 0 else 'Clouds',
                    'wind_speed': 2.5 + (i % 5),
                    'cloud_cover': (i * 10) % 100,
                    'humidity': 60 + (i % 20)
                })
            
            return jsonify({
                'forecast': forecast_data,
                'location': {
                    'name': city or 'Sample City',
                    'country': country or 'XX'
                }
            }), 200
        
        # Build API request
        params = {'appid': OPENWEATHER_API_KEY, 'units': 'metric'}
        
        if lat and lon:
            params['lat'] = lat
            params['lon'] = lon
        elif city:
            params['q'] = f"{city},{country}" if country else city
        else:
            return jsonify({'error': 'Must provide lat/lon or city'}), 400
        
        # Call OpenWeatherMap API
        response = requests.get(f"{OPENWEATHER_BASE_URL}/forecast", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parse forecast
        forecast = []
        for item in data['list']:
            forecast.append({
                'timestamp': datetime.fromtimestamp(item['dt']).isoformat(),
                'temperature': item['main']['temp'],
                'feels_like': item['main']['feels_like'],
                'weather': item['weather'][0]['main'],
                'description': item['weather'][0]['description'],
                'icon': item['weather'][0]['icon'],
                'wind_speed': item['wind']['speed'],
                'wind_direction': item['wind'].get('deg', 0),
                'cloud_cover': item['clouds']['all'],
                'humidity': item['main']['humidity'],
                'pressure': item['main']['pressure'],
                'precipitation': item.get('rain', {}).get('3h', 0)
            })
        
        return jsonify({
            'forecast': forecast,
            'location': {
                'name': data['city']['name'],
                'country': data['city']['country'],
                'lat': data['city']['coord']['lat'],
                'lon': data['city']['coord']['lon']
            }
        }), 200
        
    except requests.RequestException as e:
        logger.error(f"Forecast API error: {e}")
        return jsonify({'error': 'Failed to fetch forecast data'}), 500
    except Exception as e:
        logger.error(f"Forecast processing error: {e}", exc_info=True)
        return jsonify({'error': 'Forecast data processing failed'}), 500


@weather_bp.route('/solar-potential', methods=['GET'])
@jwt_required()
def get_solar_potential():
    """
    Calculate solar generation potential based on weather
    
    Query params:
    - lat: Latitude
    - lon: Longitude
    - capacity: Solar panel capacity (MW)
    """
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        capacity = request.args.get('capacity', 10.0, type=float)
        
        if not lat or not lon:
            return jsonify({'error': 'Latitude and longitude required'}), 400
        
        # Get current weather
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        } if OPENWEATHER_API_KEY else None
        
        if params:
            response = requests.get(f"{OPENWEATHER_BASE_URL}/weather", params=params, timeout=10)
            response.raise_for_status()
            weather = response.json()
            
            # Calculate solar potential based on cloud cover
            cloud_cover = weather['clouds']['all']
            clear_sky_factor = (100 - cloud_cover) / 100
            
            # Simplified solar calculation (peak sun hours * capacity * efficiency)
            peak_sun_hours = 5 * clear_sky_factor  # Varies by location
            efficiency = 0.18  # 18% panel efficiency
            potential_mw = capacity * peak_sun_hours * efficiency
        else:
            # Mock calculation
            clear_sky_factor = 0.7
            potential_mw = capacity * 5 * 0.18 * clear_sky_factor
        
        return jsonify({
            'solar_potential_mwh': round(potential_mw, 2),
            'capacity_mw': capacity,
            'clear_sky_factor': round(clear_sky_factor, 2),
            'estimated_generation': round(potential_mw / 24, 2)  # Per hour average
        }), 200
        
    except Exception as e:
        logger.error(f"Solar potential calculation error: {e}", exc_info=True)
        return jsonify({'error': 'Solar potential calculation failed'}), 500
