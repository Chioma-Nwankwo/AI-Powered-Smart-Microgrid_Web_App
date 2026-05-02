"""
User management and authentication logic
"""
from typing import Optional, Dict
from database.models import User
from auth.password_handler import (
    hash_password, 
    verify_password, 
    generate_user_id,
    validate_password_strength,
    validate_email,
    create_access_token
)
from database.mongo_handler import mongo_db
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class UserManager:
    """Manage user operations"""
    
    @staticmethod
    def register_user(user_data: Dict, password: Optional[str] = None) -> tuple[bool, str, Optional[str]]:
        """
        Register a new user
        Returns: (success, message, user_id)
        """
        try:
            # Validate email if provided
            if user_data.get('email'):
                if not validate_email(user_data['email']):
                    return False, "Invalid email format", None
                
                if User.email_exists(user_data['email']):
                    return False, "Email already registered", None
            
            # Validate password if using email auth
            if password and user_data.get('auth_provider', 'email') == 'email':
                # Truncate password to 72 BYTES if too long (bcrypt limit)
                password_bytes = password.encode('utf-8')
                if len(password_bytes) > 72:
                    password = password_bytes[:72].decode('utf-8', errors='ignore')
                    logger.info("Password truncated to 72 bytes for bcrypt compatibility")
                
                is_valid, message = validate_password_strength(password)
                if not is_valid:
                    return False, message, None
                user_data['password_hash'] = hash_password(password)
            
            # Generate user ID
            user_data['user_id'] = generate_user_id()
            
            # Validate required fields
            required_fields = ['country', 'state', 'building_type', 'address']
            for field in required_fields:
                if not user_data.get(field):
                    return False, f"Missing required field: {field}", None
            
            # Create user in database
            user_id = User.create(user_data)
            
            if user_id:
                return True, "User registered successfully", user_id
            else:
                return False, "Failed to create user", None
                
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False, f"Registration error: {str(e)}", None
    
    @staticmethod
    def login_user(identifier: str, password: str) -> tuple[bool, str, Optional[Dict]]:
        """
        Login user with email/user_id and password
        Returns: (success, message, user_data)
        """
        try:
            # Try to find user by email or user_id
            user = None
            if '@' in identifier:
                user = User.get_by_email(identifier)
            else:
                user = User.get_by_user_id(identifier)
            
            if not user:
                return False, "User not found", None
            
            # Verify password
            if not user.get('password_hash'):
                return False, "This account uses OAuth. Please login with your provider.", None
            
            if not verify_password(password, user['password_hash']):
                return False, "Incorrect password", None
            
            # Update last login
            User.update_last_login(user['user_id'])
            
            # Create session
            session_id = generate_user_id(prefix="SESS")
            expires_at = datetime.utcnow() + timedelta(days=7)
            mongo_db.create_session(user['user_id'], session_id, expires_at)
            
            # Remove sensitive data
            user_data = {k: v for k, v in user.items() if k != 'password_hash'}
            user_data['session_id'] = session_id
            
            return True, "Login successful", user_data
            
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False, f"Login error: {str(e)}", None
    
    @staticmethod
    def login_oauth(oauth_data: Dict, signup_data: Optional[Dict] = None) -> tuple[bool, str, Optional[Dict]]:
        """
        Login or register user with OAuth
        Returns: (success, message, user_data)
        """
        try:
            provider = oauth_data['provider']
            provider_id = oauth_data['provider_id']
            email = oauth_data.get('email')
            
            # Check if user exists by provider ID first
            user = User.get_by_provider(provider, provider_id)
            
            # If not found by provider ID, check by email (in case of re-auth)
            if not user and email:
                user = User.get_by_email(email)
                # If user exists with this email but different auth provider,
                # update the provider info
                if user:
                    logger.info(f"Found user by email {email}, different provider")
            
            if user:
                # Existing user - login
                User.update_last_login(user['user_id'])
                
                # Create session
                session_id = generate_user_id(prefix="SESS")
                expires_at = datetime.utcnow() + timedelta(days=7)
                mongo_db.create_session(user['user_id'], session_id, expires_at)
                
                user_data = {k: v for k, v in user.items() if k != 'password_hash'}
                user_data['session_id'] = session_id
                
                return True, "Login successful", user_data
            else:
                # New user - needs to complete signup on frontend
                return False, "New user - signup required", None
                    
        except Exception as e:
            logger.error(f"Error during OAuth login: {e}", exc_info=True)
            return False, f"OAuth login error: {str(e)}", None
    
    @staticmethod
    def validate_session(session_id: str) -> Optional[Dict]:
        """Validate user session"""
        try:
            session = mongo_db.get_session(session_id)
            
            if not session:
                return None
            
            if session['expires_at'] < datetime.utcnow():
                mongo_db.delete_session(session_id)
                return None
            
            # Update last activity
            mongo_db.update_session_activity(session_id)
            
            # Get user data
            user = User.get_by_user_id(session['user_id'])
            return user
            
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None
    
    @staticmethod
    def logout_user(session_id: str) -> bool:
        """Logout user by deleting session"""
        try:
            return mongo_db.delete_session(session_id)
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            return User.get_by_email(email)
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict]:
        """Get user by user ID"""
        try:
            return User.get_by_user_id(user_id)
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    @staticmethod
    def update_password(user_id: str, new_password: str) -> tuple[bool, str]:
        """Update user password"""
        try:
            # Truncate password to 72 BYTES if too long (bcrypt limit)
            password_bytes = new_password.encode('utf-8')
            if len(password_bytes) > 72:
                new_password = password_bytes[:72].decode('utf-8', errors='ignore')
                logger.info("Password truncated to 72 bytes for bcrypt compatibility")
            
            # Validate password strength
            is_valid, message = validate_password_strength(new_password)
            if not is_valid:
                return False, message
            
            # Hash new password
            password_hash = hash_password(new_password)
            
            # Update in database
            success = User.update_password(user_id, password_hash)
            
            if success:
                return True, "Password updated successfully"
            else:
                return False, "Failed to update password"
                
        except Exception as e:
            logger.error(f"Error updating password: {e}", exc_info=True)
            return False, "Failed to update password"


user_manager = UserManager()
