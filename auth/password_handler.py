"""
Password-based authentication handler
"""
import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional, Dict
from config import config
import secrets
import string


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (max 72 bytes)"""
    # bcrypt has 72 BYTE limit, not character limit
    # Encode to bytes and truncate if needed
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # bcrypt has 72 BYTE limit, not character limit
    password_bytes = plain_password.encode('utf-8')[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))


def generate_user_id(prefix: str = "USR") -> str:
    """Generate a unique user ID"""
    timestamp = datetime.now().strftime("%Y%m%d")
    random_str = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    return f"{prefix}-{timestamp}-{random_str}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict]:
    """Decode and verify JWT access token"""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    Returns: (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if not any(c in string.punctuation for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
