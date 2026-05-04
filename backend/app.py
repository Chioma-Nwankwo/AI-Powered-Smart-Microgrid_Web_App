"""
Flask Backend API for Smart Microgrid Analytics
Exposes ML models, authentication, and data through REST API
"""
import sys, os
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
# Fix Flask watchdog reloader: store the absolute path of this script so the
# reloader can find it even after os.chdir() calls in blueprints change cwd.
sys.argv[0] = str(Path(__file__).absolute())

# Set working directory to web app root (parent of backend/) once here so
# relative imports in model_loader/data_loader resolve correctly.
_WEB_APP_ROOT = str(Path(__file__).parent.parent)
os.chdir(_WEB_APP_ROOT)
sys.path.insert(0, _WEB_APP_ROOT)

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

from config import config
from auth.user_manager import user_manager
from auth.oauth_handler import oauth_handler
from database.models import User
import logging

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config.ACCESS_TOKEN_EXPIRE_MINUTES * 60

# Enable CORS — FRONTEND_URL may be comma-separated for multiple Vercel URLs
_allowed_origins = ['http://localhost:3000', 'http://localhost:5173']
for _url in os.environ.get('FRONTEND_URL', '').split(','):
    _url = _url.strip()
    if _url:
        _allowed_origins.append(_url)
CORS(app, origins=_allowed_origins, supports_credentials=True)

# Initialize JWT
jwt = JWTManager(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Smart Microgrid Analytics API',
        'version': '1.0.0'
    }), 200

# Import route blueprints
from api.auth_routes     import auth_bp
from api.forecast_routes import forecast_bp
from api.optimize_routes import optimize_bp
from api.user_routes     import user_bp
from api.data_routes     import data_bp
from api.anomaly_routes  import anomaly_bp
from api.battery_routes  import battery_bp
from api.weather_routes  import weather_bp
from api.regions_routes  import regions_bp
from api.metrics_routes  import metrics_bp
from api.location_routes import location_bp

# Register blueprints
app.register_blueprint(auth_bp,     url_prefix='/api/auth')
app.register_blueprint(forecast_bp, url_prefix='/api/forecast')
app.register_blueprint(optimize_bp, url_prefix='/api/optimize')
app.register_blueprint(user_bp,     url_prefix='/api/user')
app.register_blueprint(data_bp,     url_prefix='/api/data')
app.register_blueprint(anomaly_bp,  url_prefix='/api/anomaly')
app.register_blueprint(battery_bp,  url_prefix='/api/battery')
app.register_blueprint(weather_bp,  url_prefix='/api/weather')
app.register_blueprint(regions_bp,  url_prefix='/api/regions')
app.register_blueprint(metrics_bp,  url_prefix='/api/metrics')
app.register_blueprint(location_bp, url_prefix='/api/location')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Flask API server...")
    logger.info("API will be available at http://localhost:5000")
    # use_reloader=False avoids the watchdog crash caused by os.chdir() in blueprints
    app.run(debug=True, use_reloader=False, port=5000, host='0.0.0.0')
