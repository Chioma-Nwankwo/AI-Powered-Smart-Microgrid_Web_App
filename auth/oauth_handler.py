"""
OAuth authentication handler for Google, Apple, and Microsoft
"""
from google.oauth2 import id_token
from google.auth.transport import requests
from authlib.integrations.base_client import OAuthError
from config import config
import requests as http_requests
import logging

logger = logging.getLogger(__name__)


class OAuthHandler:
    """Handle OAuth authentication for multiple providers"""
    
    @staticmethod
    def get_google_auth_url() -> str:
        """Get Google OAuth authorization URL"""
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": config.GOOGLE_CLIENT_ID,
            "redirect_uri": config.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": "google"  # Add provider identifier
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    @staticmethod
    def get_microsoft_auth_url() -> str:
        """Get Microsoft OAuth authorization URL"""
        base_url = f"https://login.microsoftonline.com/{config.MICROSOFT_TENANT_ID}/oauth2/v2.0/authorize"
        params = {
            "client_id": config.MICROSOFT_CLIENT_ID,
            "redirect_uri": config.MICROSOFT_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "response_mode": "query",
            "state": "microsoft"  # Add provider identifier
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    @staticmethod
    def get_apple_auth_url() -> str:
        """Get Apple OAuth authorization URL"""
        base_url = "https://appleid.apple.com/auth/authorize"
        params = {
            "client_id": config.APPLE_CLIENT_ID,
            "redirect_uri": config.REDIRECT_URI,
            "response_type": "code",
            "scope": "email name",
            "response_mode": "form_post"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    @staticmethod
    def verify_google_token(token: str) -> dict:
        """Verify Google ID token and extract user info"""
        try:
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                config.GOOGLE_CLIENT_ID
            )
            
            return {
                "provider": "google",
                "provider_id": idinfo['sub'],
                "email": idinfo['email'],
                "name": idinfo.get('name', ''),
                "verified": idinfo.get('email_verified', False)
            }
        except Exception as e:
            logger.error(f"Google token verification failed: {e}")
            return None
    
    @staticmethod
    def exchange_google_code(code: str) -> dict:
        """Exchange Google authorization code for user info"""
        try:
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": config.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            
            response = http_requests.post(token_url, data=token_data)
            response.raise_for_status()
            tokens = response.json()
            
            # Verify ID token
            return OAuthHandler.verify_google_token(tokens['id_token'])
        except Exception as e:
            logger.error(f"Google code exchange failed: {e}")
            return None
    
    @staticmethod
    def exchange_microsoft_code(code: str) -> dict:
        """Exchange Microsoft authorization code for user info"""
        try:
            token_url = f"https://login.microsoftonline.com/{config.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
            token_data = {
                "code": code,
                "client_id": config.MICROSOFT_CLIENT_ID,
                "client_secret": config.MICROSOFT_CLIENT_SECRET,
                "redirect_uri": config.MICROSOFT_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            
            response = http_requests.post(token_url, data=token_data)
            response.raise_for_status()
            tokens = response.json()
            
            # Get user info
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            user_response = http_requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            )
            user_response.raise_for_status()
            user_info = user_response.json()
            
            return {
                "provider": "microsoft",
                "provider_id": user_info['id'],
                "email": user_info.get('mail') or user_info.get('userPrincipalName'),
                "name": user_info.get('displayName', ''),
                "verified": True
            }
        except Exception as e:
            logger.error(f"Microsoft code exchange failed: {e}")
            return None
    
    @staticmethod
    def exchange_apple_code(code: str) -> dict:
        """Exchange Apple authorization code for user info"""
        try:
            # Apple sign-in requires JWT client secret generation
            # This is a simplified version - production needs proper JWT signing
            token_url = "https://appleid.apple.com/auth/token"
            token_data = {
                "code": code,
                "client_id": config.APPLE_CLIENT_ID,
                "client_secret": config.APPLE_CLIENT_SECRET,
                "redirect_uri": config.REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            
            response = http_requests.post(token_url, data=token_data)
            response.raise_for_status()
            tokens = response.json()
            
            # Decode ID token to get user info
            import jwt
            id_info = jwt.decode(tokens['id_token'], options={"verify_signature": False})
            
            return {
                "provider": "apple",
                "provider_id": id_info['sub'],
                "email": id_info.get('email', ''),
                "name": "",  # Apple doesn't always provide name
                "verified": id_info.get('email_verified', False)
            }
        except Exception as e:
            logger.error(f"Apple code exchange failed: {e}")
            return None


oauth_handler = OAuthHandler()
