"""
Authentication API Routes
Handles login, signup, and OAuth callbacks
"""
from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import sys, base64, json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from auth.user_manager import user_manager
from auth.oauth_handler import oauth_handler
from auth.password_handler import validate_password_strength, validate_email
from config import config
import requests as http_requests
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Register a new user"""
    try:
        from database.mongo_handler import mongo_db
        if not mongo_db.available:
            return jsonify({'error': 'Database not configured. Set MONGODB_URI in the Render environment variables.'}), 503

        data = request.get_json()

        logger.info(f"Signup attempt for email: {data.get('email')}")
        
        # Validate required fields
        required = ['email', 'password', 'country', 'state', 'building_type', 'address']
        if not all(field in data for field in required):
            missing = [f for f in required if f not in data]
            logger.warning(f"Missing required fields: {missing}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
        
        # Validate email
        if not validate_email(data['email']):
            logger.warning(f"Invalid email format: {data['email']}")
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        is_valid, message = validate_password_strength(data['password'])
        if not is_valid:
            logger.warning(f"Weak password for {data['email']}: {message}")
            return jsonify({'error': message}), 400
        
        # Create user
        user_data = {
            'email': data['email'],
            'country': data['country'],
            'state': data['state'],
            'building_type': data['building_type'].lower(),
            'address': data['address'],
            'auth_provider': 'email',
            'electricity_rate': config.get_electricity_rate(data['country'], data['state'])
        }
        
        # Add Nigeria-specific data if applicable
        if data['country'] == 'Nigeria' and 'nigeria_band' in data:
            # Handle both 'A' and 'Band A' formats
            band = data['nigeria_band']
            if band in ['A', 'B', 'C', 'D', 'E']:
                band = f'Band {band}'
            user_data['nigeria_band'] = band
            user_data['band_rate'] = config.NIGERIA_BANDS.get(band, {}).get('rate', 225.0)
        
        success, message, user_id = user_manager.register_user(user_data, data['password'])
        
        if success:
            logger.info(f"User registered successfully: {user_id}")
            # Create access token
            access_token = create_access_token(identity=user_id)
            
            return jsonify({
                'message': 'User registered successfully',
                'user_id': user_id,
                'access_token': access_token
            }), 201
        else:
            logger.error(f"Registration failed for {data['email']}: {message}")
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Signup error: {e}", exc_info=True)
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login with email/user_id and password"""
    try:
        from database.mongo_handler import mongo_db
        if not mongo_db.available:
            return jsonify({'error': 'Database not configured. Set MONGODB_URI in the Render environment variables.'}), 503

        data = request.get_json()

        # Support both 'identifier' and 'email' fields
        identifier = data.get('identifier') or data.get('email')
        password = data.get('password')

        if not identifier or not password:
            return jsonify({'error': 'Missing credentials'}), 400

        success, message, user_data = user_manager.login_user(identifier, password)
        
        if success:
            # Create access token
            access_token = create_access_token(identity=user_data['user_id'])
            
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'user': {
                    'user_id':       user_data['user_id'],
                    'email':         user_data.get('email'),
                    'country':       user_data['country'],
                    'state':         user_data['state'],
                    'building_type': user_data['building_type'],
                    'address':       user_data.get('address', ''),
                }
            }), 200
        else:
            return jsonify({'error': message}), 401

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({'error': 'Login failed'}), 500


def _complete_oauth_login(user_info):
    """Shared: find or auto-create an OAuth user and return a JWT response."""
    success, message, user_data = user_manager.login_oauth(user_info)
    is_new_user = False

    if not success:
        is_new_user = True
        # Auto-register with sensible defaults; user can update profile later
        register_data = {
            'email':            user_info['email'],
            'country':          'Nigeria',
            'state':            'FCT',
            'building_type':    'residential',
            'address':          'Not specified',
            'auth_provider':    user_info['provider'],
            'provider_id':      user_info['provider_id'],
            'electricity_rate': config.get_electricity_rate('Nigeria', 'FCT'),
        }
        reg_ok, reg_msg, _ = user_manager.register_user(register_data)
        if not reg_ok and 'already registered' not in reg_msg.lower():
            return jsonify({'error': reg_msg}), 400
        # Second attempt after registration (or email-already-exists merge)
        success, message, user_data = user_manager.login_oauth(user_info)
        if not success:
            # Email registered under a different provider — find by email
            existing = user_manager.get_user_by_email(user_info['email'])
            if existing:
                from auth.password_handler import generate_user_id
                from database.mongo_handler import mongo_db
                session_id = generate_user_id(prefix="SESS")
                mongo_db.create_session(
                    existing['user_id'], session_id,
                    datetime.utcnow() + timedelta(days=7)
                )
                user_data = {k: v for k, v in existing.items() if k != 'password_hash'}
                user_data['session_id'] = session_id
            else:
                return jsonify({'error': 'Authentication failed'}), 500

    access_token = create_access_token(identity=user_data['user_id'])
    return jsonify({
        'access_token': access_token,
        'is_new_user':  is_new_user,
        'user': {
            'user_id':       user_data['user_id'],
            'name':          user_data.get('name', ''),
            'email':         user_data.get('email'),
            'country':       user_data.get('country'),
            'state':         user_data.get('state'),
            'building_type': user_data.get('building_type'),
            'address':       user_data.get('address', 'Not specified'),
        },
    })


@auth_bp.route('/google', methods=['GET', 'POST'])
def google_auth():
    """GET → return auth URL.  POST → accept Google access token from frontend."""
    if request.method == 'GET':
        auth_url = oauth_handler.get_google_auth_url()
        return jsonify({'auth_url': auth_url}), 200

    data  = request.get_json() or {}
    token = data.get('token')
    if not token:
        return jsonify({'error': 'Token required'}), 400

    try:
        # Try as ID token first (from GoogleLogin credential flow)
        id_resp = http_requests.get(
            'https://www.googleapis.com/oauth2/v3/tokeninfo',
            params={'id_token': token},
            timeout=10,
        )
        if id_resp.status_code == 200:
            info = id_resp.json()
        else:
            # Fall back to access token userinfo
            acc_resp = http_requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {token}'},
                timeout=10,
            )
            if acc_resp.status_code != 200:
                return jsonify({'error': 'Invalid Google token'}), 401
            info = acc_resp.json()
    except Exception as e:
        logger.error(f"Google token verify error: {e}")
        return jsonify({'error': 'Failed to verify Google token'}), 500

    return _complete_oauth_login({
        'provider':    'google',
        'provider_id': info['sub'],
        'email':       info.get('email', ''),
        'name':        info.get('name', ''),
    })


@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        code = request.args.get('code')
        if not code:
            return redirect(f"{config.FRONTEND_URL}?error=no_code")
        
        # Exchange code for user info
        user_info = oauth_handler.exchange_google_code(code)
        
        if not user_info:
            return redirect(f"{config.FRONTEND_URL}?error=oauth_failed")
        
        # Try to login user (check if user exists)
        success, message, user_data = user_manager.login_oauth(user_info)
        
        if success:
            # Create token
            access_token = create_access_token(identity=user_data['user_id'])
            # Redirect to frontend with token
            return redirect(f"{config.FRONTEND_URL}/auth/callback?token={access_token}")
        else:
            # User needs to complete registration
            return redirect(f"{config.FRONTEND_URL}/signup?email={user_info['email']}&name={user_info.get('name', '')}&provider=google")
            
    except Exception as e:
        logger.error(f"Google callback error: {e}")
        return redirect(f"http://localhost:3000?error=oauth_failed")


@auth_bp.route('/microsoft', methods=['GET', 'POST'])
def microsoft_auth():
    """GET → return auth URL.  POST → accept MSAL id_token from frontend."""
    if request.method == 'GET':
        auth_url = oauth_handler.get_microsoft_auth_url()
        return jsonify({'auth_url': auth_url}), 200

    data  = request.get_json() or {}
    token = data.get('token')
    if not token:
        return jsonify({'error': 'Token required'}), 400

    try:
        parts = token.split('.')
        if len(parts) < 2:
            return jsonify({'error': 'Invalid token format'}), 400
        padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(padded))
    except Exception as e:
        logger.error(f"Microsoft token decode error: {e}")
        return jsonify({'error': 'Failed to decode Microsoft token'}), 500

    email = (payload.get('preferred_username')
             or payload.get('email')
             or payload.get('upn', ''))
    return _complete_oauth_login({
        'provider':    'microsoft',
        'provider_id': payload.get('oid') or payload.get('sub', ''),
        'email':       email,
        'name':        payload.get('name', ''),
    })


@auth_bp.route('/apple', methods=['POST'])
def apple_auth():
    """POST — accept Apple id_token from frontend popup flow."""
    data      = request.get_json() or {}
    id_token  = data.get('token')
    user_info = data.get('user_info')   # name/email only present on first Apple login

    if not id_token:
        return jsonify({'error': 'No token provided'}), 400

    try:
        parts  = id_token.split('.')
        if len(parts) < 2:
            return jsonify({'error': 'Invalid token format'}), 400
        padded  = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(padded))

        provider_id = payload.get('sub', '')
        email       = payload.get('email') or (user_info or {}).get('email', '')
        first       = ((user_info or {}).get('name') or {}).get('firstName', '')
        last        = ((user_info or {}).get('name') or {}).get('lastName', '')
        name        = f"{first} {last}".strip() or email

        return _complete_oauth_login({
            'provider':    'apple',
            'provider_id': provider_id,
            'email':       email,
            'name':        name,
        })
    except Exception as e:
        logger.error(f"Apple auth error: {e}")
        return jsonify({'error': 'Apple authentication failed'}), 500


@auth_bp.route('/microsoft/callback', methods=['GET'])
def microsoft_callback():
    """Handle Microsoft OAuth callback"""
    try:
        code = request.args.get('code')
        if not code:
            return redirect(f"{config.FRONTEND_URL}?error=no_code")
        
        # Exchange code for user info
        user_info = oauth_handler.exchange_microsoft_code(code)
        
        if not user_info:
            return redirect(f"{config.FRONTEND_URL}?error=oauth_failed")
        
        # Try to login user (check if user exists)
        success, message, user_data = user_manager.login_oauth(user_info)
        
        if success:
            # Create token
            access_token = create_access_token(identity=user_data['user_id'])
            # Redirect to frontend with token
            return redirect(f"{config.FRONTEND_URL}/auth/callback?token={access_token}")
        else:
            # User needs to complete registration
            return redirect(f"{config.FRONTEND_URL}/signup?email={user_info['email']}&name={user_info.get('name', '')}&provider=microsoft")
            
    except Exception as e:
        logger.error(f"Microsoft callback error: {e}")
        return redirect(f"http://localhost:3000?error=oauth_failed")


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info"""
    try:
        user_id = get_jwt_identity()
        user_data = user_manager.get_user_by_id(user_id)
        
        if user_data:
            response_data = {
                'user_id': user_data['user_id'],
                'email': user_data['email'],
                'country': user_data['country'],
                'state': user_data['state'],
                'building_type': user_data['building_type'],
                'address': user_data.get('address', '')
            }
            
            # Add Nigeria-specific data if applicable
            if user_data.get('country') == 'Nigeria' and 'nigeria_band' in user_data:
                response_data['nigeria_band'] = user_data['nigeria_band']
                
            return jsonify(response_data), 200
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Get current user error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch user'}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
            
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check if user exists
        user_data = user_manager.get_user_by_email(email)
        
        if user_data:
            # Generate reset token (valid for 1 hour)
            reset_token = create_access_token(
                identity=user_data['user_id'],
                expires_delta=timedelta(hours=1)
            )
            
            # In production, send email with reset link
            # For now, return token (in production, don't return it!)
            return jsonify({
                'message': 'Password reset instructions sent to your email',
                'reset_token': reset_token  # Remove this in production
            }), 200
        else:
            # Return success even if user doesn't exist (security best practice)
            return jsonify({
                'message': 'If an account exists with this email, you will receive reset instructions'
            }), 200
            
    except Exception as e:
        logger.error(f"Forgot password error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to process request'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password():
    """Reset password with token"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        new_password = data.get('new_password')
        
        if not new_password:
            return jsonify({'error': 'New password is required'}), 400
        
        # Validate password strength
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Update password
        success, message = user_manager.update_password(user_id, new_password)
        
        if success:
            return jsonify({'message': 'Password updated successfully'}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Reset password error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to reset password'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change password (requires current password)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400
        
        # Validate password strength
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Verify current password
        user_data = user_manager.get_user_by_id(user_id)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        success, message, _ = user_manager.login_user(user_data['email'], current_password)
        if not success:
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        success, message = user_manager.update_password(user_id, new_password)
        
        if success:
            return jsonify({'message': 'Password changed successfully'}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Change password error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to change password'}), 500
