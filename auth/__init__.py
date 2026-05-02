"""
Authentication package initialization
"""
from auth.password_handler import (
    hash_password,
    verify_password,
    generate_user_id,
    validate_password_strength,
    validate_email
)
from auth.oauth_handler import oauth_handler, OAuthHandler
from auth.user_manager import user_manager, UserManager

__all__ = [
    'hash_password',
    'verify_password',
    'generate_user_id',
    'validate_password_strength',
    'validate_email',
    'oauth_handler',
    'OAuthHandler',
    'user_manager',
    'UserManager'
]
