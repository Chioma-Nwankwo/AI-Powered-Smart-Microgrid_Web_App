"""
Helper functions and utilities
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import logging

logger = logging.getLogger(__name__)


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)


def hash_string(text: str) -> str:
    """Create SHA-256 hash of string"""
    return hashlib.sha256(text.encode()).hexdigest()


def format_energy_value(value: float, unit: str = "kWh") -> str:
    """Format energy value with appropriate unit"""
    if value >= 1000:
        return f"{value/1000:.2f} M{unit}"
    elif value >= 1:
        return f"{value:.2f} {unit}"
    else:
        return f"{value*1000:.2f} W{unit[1:]}"


def format_currency(value: float, currency: str = "USD") -> str:
    """Format currency value"""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "NGN": "₦"}
    symbol = symbols.get(currency, "$")
    return f"{symbol}{value:,.2f}"


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string"""
    return dt.strftime(format_str)


def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Parse string to datetime object"""
    try:
        return datetime.strptime(timestamp_str, format_str)
    except Exception as e:
        logger.error(f"Error parsing timestamp: {e}")
        return datetime.now()


def generate_time_series(start: datetime, hours: int = 24, interval_minutes: int = 60) -> List[datetime]:
    """Generate time series for given duration"""
    timestamps = []
    current = start
    
    for _ in range(hours):
        timestamps.append(current)
        current += timedelta(minutes=interval_minutes)
    
    return timestamps


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0 if new_value == 0 else 100
    return ((new_value - old_value) / old_value) * 100


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp value between min and max"""
    return max(min_value, min(value, max_value))


def moving_average(data: List[float], window: int = 5) -> List[float]:
    """Calculate moving average"""
    if len(data) < window:
        return data
    
    result = []
    for i in range(len(data)):
        if i < window - 1:
            result.append(data[i])
        else:
            avg = sum(data[i-window+1:i+1]) / window
            result.append(avg)
    
    return result


def exponential_smoothing(data: List[float], alpha: float = 0.3) -> List[float]:
    """Apply exponential smoothing to data"""
    if not data:
        return []
    
    smoothed = [data[0]]
    for i in range(1, len(data)):
        value = alpha * data[i] + (1 - alpha) * smoothed[i-1]
        smoothed.append(value)
    
    return smoothed


def detect_anomalies(data: List[float], threshold: float = 3.0) -> List[int]:
    """Detect anomalies using z-score method"""
    if len(data) < 3:
        return []
    
    import numpy as np
    mean = np.mean(data)
    std = np.std(data)
    
    if std == 0:
        return []
    
    anomalies = []
    for i, value in enumerate(data):
        z_score = abs((value - mean) / std)
        if z_score > threshold:
            anomalies.append(i)
    
    return anomalies


def calculate_energy_balance(generation: float, demand: float, 
                            battery_level: float, battery_capacity: float) -> Dict:
    """Calculate energy balance status"""
    balance = generation - demand
    
    status = "balanced"
    action = "none"
    
    if balance > 0:
        # Surplus
        if battery_level < battery_capacity * 0.9:
            status = "surplus"
            action = "charge_battery"
        else:
            status = "excess"
            action = "export_to_grid"
    elif balance < 0:
        # Deficit
        if battery_level > battery_capacity * 0.2:
            status = "deficit"
            action = "discharge_battery"
        else:
            status = "shortage"
            action = "import_from_grid"
    
    return {
        'balance': balance,
        'status': status,
        'recommended_action': action,
        'battery_status': 'healthy' if battery_level > battery_capacity * 0.2 else 'low'
    }


def validate_energy_data(data: Dict) -> tuple[bool, str]:
    """Validate energy data format"""
    required_fields = ['demand', 'generation', 'timestamp']
    
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate numeric values
    try:
        demand = float(data['demand'])
        generation = float(data['generation'])
        
        if demand < 0 or generation < 0:
            return False, "Energy values cannot be negative"
        
    except (ValueError, TypeError):
        return False, "Invalid numeric values"
    
    return True, "Valid"


def serialize_numpy(obj: Any) -> Any:
    """Serialize numpy types to JSON-compatible types"""
    import numpy as np
    
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except Exception:
        return default


def get_time_of_day_category(hour: int) -> str:
    """Categorize time of day"""
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"


def get_season(month: int) -> str:
    """Get season based on month (Northern Hemisphere)"""
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


class DataCache:
    """Simple in-memory cache for frequently accessed data"""
    
    def __init__(self, ttl: int = 300):
        """
        Initialize cache
        
        Args:
            ttl: Time to live in seconds (default 5 minutes)
        """
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Any:
        """Get value from cache"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if (datetime.now() - timestamp).total_seconds() < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache"""
        self.cache[key] = (value, datetime.now())
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
    
    def remove(self, key: str):
        """Remove specific key from cache"""
        if key in self.cache:
            del self.cache[key]
