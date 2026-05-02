"""
Security Layer Module
Implements encryption, monitoring, and security best practices
"""
import hashlib
import hmac
import secrets
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from functools import wraps
from flask import request, jsonify
import json

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """Monitor and log security events"""
    
    def __init__(self, mongo_db):
        self.mongo_db = mongo_db
        self.security_collection = mongo_db.db['security_events']
    
    def log_event(self, event_type: str, user_id: Optional[str], 
                  details: Dict, severity: str = 'info'):
        """
        Log security event to MongoDB
        
        Args:
            event_type: Type of event (login_attempt, api_access, anomaly_detected)
            user_id: User ID if applicable
            details: Event details
            severity: info, warning, critical
        """
        event = {
            'timestamp': datetime.utcnow(),
            'event_type': event_type,
            'user_id': user_id,
            'details': details,
            'severity': severity,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        }
        
        self.security_collection.insert_one(event)
        
        if severity == 'critical':
            logger.critical(f"SECURITY ALERT: {event_type} - {details}")
        elif severity == 'warning':
            logger.warning(f"Security warning: {event_type} - {details}")
    
    def get_recent_events(self, event_type: Optional[str] = None, 
                         hours: int = 24) -> list:
        """Get recent security events"""
        query = {'timestamp': {'$gte': datetime.utcnow() - timedelta(hours=hours)}}
        if event_type:
            query['event_type'] = event_type
        
        return list(self.security_collection.find(query).sort('timestamp', -1))
    
    def detect_suspicious_activity(self, user_id: str) -> Dict:
        """
        Detect suspicious activity patterns
        - Multiple failed login attempts
        - Unusual access patterns
        - High API request rate
        """
        last_hour = datetime.utcnow() - timedelta(hours=1)
        
        # Check failed logins
        failed_logins = self.security_collection.count_documents({
            'user_id': user_id,
            'event_type': 'login_failed',
            'timestamp': {'$gte': last_hour}
        })
        
        # Check API request rate
        api_requests = self.security_collection.count_documents({
            'user_id': user_id,
            'event_type': 'api_request',
            'timestamp': {'$gte': last_hour}
        })
        
        suspicious = {
            'is_suspicious': False,
            'failed_logins': failed_logins,
            'api_requests_per_hour': api_requests,
            'alerts': []
        }
        
        if failed_logins > 5:
            suspicious['is_suspicious'] = True
            suspicious['alerts'].append('Multiple failed login attempts')
        
        if api_requests > 1000:
            suspicious['is_suspicious'] = True
            suspicious['alerts'].append('Unusually high API request rate')
        
        return suspicious


class DataEncryption:
    """Handle data encryption for sensitive information"""
    
    @staticmethod
    def encrypt_field(data: str, key: str) -> str:
        """
        Simple encryption for sensitive fields
        In production, use proper encryption libraries like cryptography
        """
        # This is a placeholder - use proper encryption in production
        return hashlib.sha256(f"{data}{key}".encode()).hexdigest()
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """One-way hash for sensitive data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate secure API key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_hmac_signature(data: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature for API requests"""
        expected_signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)


class RateLimiter:
    """Simple rate limiter for API endpoints"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [(timestamp, count)]}
    
    def is_allowed(self, identifier: str) -> tuple[bool, Dict]:
        """
        Check if request is allowed
        
        Returns:
            (is_allowed, info_dict)
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Clean old entries
        if identifier in self.requests:
            self.requests[identifier] = [
                (ts, count) for ts, count in self.requests[identifier]
                if ts > window_start
            ]
        else:
            self.requests[identifier] = []
        
        # Count requests in window
        request_count = sum(count for _, count in self.requests[identifier])
        
        if request_count >= self.max_requests:
            return False, {
                'allowed': False,
                'requests_made': request_count,
                'limit': self.max_requests,
                'reset_in_seconds': self.window_seconds
            }
        
        # Add current request
        self.requests[identifier].append((now, 1))
        
        return True, {
            'allowed': True,
            'requests_made': request_count + 1,
            'limit': self.max_requests,
            'remaining': self.max_requests - request_count - 1
        }


def require_api_key(f):
    """Decorator to require API key for endpoint"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # Verify API key (implement your verification logic)
        # This is a placeholder - implement proper verification
        valid_keys = ['your-api-key']  # Load from database
        
        if api_key not in valid_keys:
            return jsonify({'error': 'Invalid API key'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """Decorator to apply rate limiting to endpoint"""
    limiter = RateLimiter(max_requests, window_seconds)
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = request.remote_addr
            allowed, info = limiter.is_allowed(identifier)
            
            if not allowed:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    **info
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


class SecurityConfig:
    """Security configuration and best practices"""
    
    # Password requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Session settings
    SESSION_TIMEOUT_MINUTES = 60
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    # API settings
    API_RATE_LIMIT = 100  # requests per minute
    MAX_REQUEST_SIZE_MB = 10
    
    # Encryption
    ENCRYPTION_ALGORITHM = 'AES-256'
    HASH_ALGORITHM = 'SHA-256'
    
    # Monitoring
    LOG_SECURITY_EVENTS = True
    ALERT_ON_SUSPICIOUS_ACTIVITY = True
    
    @classmethod
    def get_security_headers(cls) -> Dict[str, str]:
        """Get recommended security headers for Flask responses"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }


# Example usage
if __name__ == "__main__":
    # Test rate limiter
    limiter = RateLimiter(max_requests=5, window_seconds=10)
    
    for i in range(7):
        allowed, info = limiter.is_allowed('test_ip')
        print(f"Request {i+1}: {info}")
    
    # Test encryption
    key = DataEncryption.generate_api_key()
    print(f"Generated API key: {key}")
    
    sensitive_data = "user_password_123"
    hashed = DataEncryption.hash_sensitive_data(sensitive_data)
    print(f"Hashed data: {hashed}")
