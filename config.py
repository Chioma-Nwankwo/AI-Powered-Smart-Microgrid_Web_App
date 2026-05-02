"""
Configuration settings for the Smart Microgrid Analytics application
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv is optional, will use environment variables directly
    pass
from pathlib import Path

# Load environment variables if dotenv is available

class Config:
    """Application configuration"""
    
    # App Settings
    APP_NAME = os.getenv("APP_NAME", "Smart Microgrid Analytics")
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    # Database Configuration
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "microgrid_db")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DB = os.getenv("MONGODB_DB", "microgrid_logs")
    
    # OAuth Configuration
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
    APPLE_CLIENT_SECRET = os.getenv("APPLE_CLIENT_SECRET", "")
    APPLE_KEY_ID = os.getenv("APPLE_KEY_ID", "")
    APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID", "")
    
    MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
    
    # OAuth Redirect URIs
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/auth/google/callback")
    MICROSOFT_REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:5000/api/auth/microsoft/callback")
    
    # Legacy support (for backward compatibility)
    REDIRECT_URI = GOOGLE_REDIRECT_URI  # Default to Google for old code
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # External APIs
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
    MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "")
    IPGEOLOCATION_API_KEY = os.getenv("IPGEOLOCATION_API_KEY", "")
    
    # Feature Flags
    ENABLE_ML_MODELS = os.getenv("ENABLE_ML_MODELS", "true").lower() == "true"
    ENABLE_OPTIMIZATION = os.getenv("ENABLE_OPTIMIZATION", "true").lower() == "true"
    
    # Paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    DATA_PROCESSED_DIR = DATA_DIR / "processed"
    DATA_RAW_DIR = DATA_DIR / "raw"
    MODELS_DIR = BASE_DIR / "models" / "trained"
    SCALERS_DIR = BASE_DIR / "models" / "scalers"
    SUMMARIES_DIR = BASE_DIR / "models" / "summaries"
    
    # ML Model Parameters
    TRAIN_TEST_SPLIT = 0.8
    RANDOM_STATE = 42
    FORECAST_HORIZON = 24  # hours
    
    # Countries supported
    COUNTRIES = ["Nigeria", "Germany", "Canada", "Australia"]
    
    # Currency symbols by country
    CURRENCY_SYMBOLS = {
        "Nigeria": "₦",
        "Germany": "€",
        "Canada": "CAD$",
        "Australia": "AUD$"
    }
    
    # Supported languages
    LANGUAGES = {
        "en": "English",
        "fr": "Français",
        "de": "Deutsch",
        "es": "Español"
    }
    
    # States/Provinces by country (also aliased as STATES_BY_COUNTRY for app.py)
    STATES = {
        "Nigeria": [
            "Abuja (FCT)", "Lagos", "Kano", "Rivers (Port Harcourt)", "Oyo (Ibadan)",
            "Kaduna", "Delta", "Ogun", "Anambra", "Enugu", "Katsina", "Imo",
            "Kwara", "Edo", "Plateau", "Abia", "Borno", "Niger", "Akwa Ibom", "Ondo"
        ],
        "Germany": [
            "Baden-Württemberg", "Bavaria", "Berlin", "Brandenburg", "Bremen",
            "Hamburg", "Hesse", "Lower Saxony", "Mecklenburg-Vorpommern",
            "North Rhine-Westphalia", "Rhineland-Palatinate", "Saarland",
            "Saxony", "Saxony-Anhalt", "Schleswig-Holstein", "Thuringia"
        ],
        "Canada": [
            "Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba",
            "Saskatchewan", "Nova Scotia", "New Brunswick", "Newfoundland and Labrador",
            "Prince Edward Island", "Northwest Territories", "Yukon", "Nunavut"
        ],
        "Australia": [
            "New South Wales", "Victoria", "Queensland", "South Australia",
            "Western Australia", "Tasmania", "Northern Territory",
            "Australian Capital Territory"
        ]
    }
    
    # Nigeria Electricity Bands (NERC 2024)
    NIGERIA_BANDS = {
        "Band A": {
            "description": "20-24 hours daily supply",
            "rate": 225.0  # Naira per kWh
        },
        "Band B": {
            "description": "16-20 hours daily supply", 
            "rate": 63.0
        },
        "Band C": {
            "description": "12-16 hours daily supply",
            "rate": 50.0
        },
        "Band D": {
            "description": "8-12 hours daily supply",
            "rate": 43.0
        },
        "Band E": {
            "description": "4-8 hours daily supply",
            "rate": 40.0
        }
    }
    
    # Electricity rates by state/region (USD per kWh)
    ELECTRICITY_RATES = {
        "Nigeria": {
            "Abuja (FCT)": {"base_rate": 0.15, "peak_rate": 0.22, "off_peak_rate": 0.10},
            "Lagos": {"base_rate": 0.16, "peak_rate": 0.24, "off_peak_rate": 0.11},
            "Kano": {"base_rate": 0.14, "peak_rate": 0.20, "off_peak_rate": 0.09},
            "Rivers (Port Harcourt)": {"base_rate": 0.15, "peak_rate": 0.23, "off_peak_rate": 0.10},
            "Oyo (Ibadan)": {"base_rate": 0.14, "peak_rate": 0.21, "off_peak_rate": 0.09},
            "default": {"base_rate": 0.14, "peak_rate": 0.21, "off_peak_rate": 0.09}
        },
        "Germany": {
            "Baden-Württemberg": {"base_rate": 0.32, "peak_rate": 0.38, "off_peak_rate": 0.28},
            "Bavaria": {"base_rate": 0.31, "peak_rate": 0.37, "off_peak_rate": 0.27},
            "Berlin": {"base_rate": 0.33, "peak_rate": 0.40, "off_peak_rate": 0.29},
            "Hamburg": {"base_rate": 0.34, "peak_rate": 0.41, "off_peak_rate": 0.30},
            "North Rhine-Westphalia": {"base_rate": 0.32, "peak_rate": 0.39, "off_peak_rate": 0.28},
            "default": {"base_rate": 0.32, "peak_rate": 0.38, "off_peak_rate": 0.28}
        },
        "Canada": {
            "Ontario": {"base_rate": 0.12, "peak_rate": 0.18, "off_peak_rate": 0.08},
            "Quebec": {"base_rate": 0.07, "peak_rate": 0.09, "off_peak_rate": 0.05},
            "British Columbia": {"base_rate": 0.10, "peak_rate": 0.14, "off_peak_rate": 0.07},
            "Alberta": {"base_rate": 0.13, "peak_rate": 0.20, "off_peak_rate": 0.09},
            "Manitoba": {"base_rate": 0.09, "peak_rate": 0.12, "off_peak_rate": 0.06},
            "Saskatchewan": {"base_rate": 0.11, "peak_rate": 0.16, "off_peak_rate": 0.08},
            "default": {"base_rate": 0.11, "peak_rate": 0.15, "off_peak_rate": 0.08}
        },
        "Australia": {
            "New South Wales": {"base_rate": 0.28, "peak_rate": 0.45, "off_peak_rate": 0.18},
            "Victoria": {"base_rate": 0.26, "peak_rate": 0.42, "off_peak_rate": 0.17},
            "Queensland": {"base_rate": 0.25, "peak_rate": 0.40, "off_peak_rate": 0.16},
            "South Australia": {"base_rate": 0.35, "peak_rate": 0.52, "off_peak_rate": 0.22},
            "Western Australia": {"base_rate": 0.27, "peak_rate": 0.43, "off_peak_rate": 0.18},
            "Tasmania": {"base_rate": 0.24, "peak_rate": 0.38, "off_peak_rate": 0.16},
            "default": {"base_rate": 0.27, "peak_rate": 0.43, "off_peak_rate": 0.18}
        }
    }
    
    @staticmethod
    def get_electricity_rate(country: str, state: str, rate_type: str = "base_rate"):
        """Get electricity rate for a specific location"""
        country_rates = Config.ELECTRICITY_RATES.get(country, {})
        state_rates = country_rates.get(state, country_rates.get("default", {}))
        return state_rates.get(rate_type, 0.15)
    
    @staticmethod
    def format_currency(country: str, amount: float) -> str:
        """Format amount with correct currency symbol for country"""
        symbol = Config.CURRENCY_SYMBOLS.get(country, "$")
        return f"{symbol}{amount:,.2f}"
    
    @classmethod
    def get_database_url(cls):
        """Get PostgreSQL database URL"""
        return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
    
    @classmethod
    def validate(cls):
        """Validate essential configuration"""
        required = []
        
        if not cls.SECRET_KEY or cls.SECRET_KEY == "dev-secret-key-change-in-production":
            required.append("SECRET_KEY")
        
        if cls.ENABLE_ML_MODELS and not cls.MODELS_DIR.exists():
            cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        return required

    # Alias for app.py compatibility
    @classmethod
    @property
    def STATES_BY_COUNTRY(cls):
        return cls.STATES

config = Config()
# Patch instance so app.py attribute access works
config.STATES_BY_COUNTRY = Config.STATES
