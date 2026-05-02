"""
Database models and data access layer
"""
from datetime import datetime
from typing import Optional, Dict, List
from database.postgres_handler import postgres_db
from database.mongo_handler import mongo_db
import logging

logger = logging.getLogger(__name__)


class User:
    """User model for database operations"""
    
    @staticmethod
    def create(user_data: Dict) -> Optional[str]:
        """Create a new user"""
        query = """
        INSERT INTO users (user_id, email, password_hash, country, state, 
                          building_type, address, auth_provider, provider_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING user_id;
        """
        params = (
            user_data['user_id'],
            user_data.get('email'),
            user_data.get('password_hash'),
            user_data['country'],
            user_data['state'],
            user_data['building_type'],
            user_data['address'],
            user_data.get('auth_provider', 'email'),
            user_data.get('provider_id')
        )
        
        result = postgres_db.execute_query(query, params)
        if result:
            # Log activity
            mongo_db.log_activity(user_data['user_id'], 'user_created', {
                'country': user_data['country'],
                'building_type': user_data['building_type']
            })
            return result[0]['user_id']
        return None
    
    @staticmethod
    def get_by_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = %s AND is_active = TRUE;"
        result = postgres_db.execute_query(query, (email,))
        return dict(result[0]) if result else None
    
    @staticmethod
    def get_by_user_id(user_id: str) -> Optional[Dict]:
        """Get user by user ID"""
        query = "SELECT * FROM users WHERE user_id = %s AND is_active = TRUE;"
        result = postgres_db.execute_query(query, (user_id,))
        return dict(result[0]) if result else None
    
    @staticmethod
    def get_by_provider(provider: str, provider_id: str) -> Optional[Dict]:
        """Get user by OAuth provider and ID"""
        query = """
        SELECT * FROM users 
        WHERE auth_provider = %s AND provider_id = %s AND is_active = TRUE;
        """
        result = postgres_db.execute_query(query, (provider, provider_id))
        return dict(result[0]) if result else None
    
    @staticmethod
    def update_last_login(user_id: str):
        """Update user's last login timestamp"""
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s;"
        postgres_db.execute_query(query, (user_id,), fetch=False)
        mongo_db.log_activity(user_id, 'user_login')
    
    @staticmethod
    def update_password(user_id: str, password_hash: str) -> bool:
        """Update user password"""
        try:
            query = "UPDATE users SET password_hash = %s WHERE user_id = %s;"
            postgres_db.execute_query(query, (password_hash, user_id), fetch=False)
            mongo_db.log_activity(user_id, 'password_changed')
            return True
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False
    
    @staticmethod
    def email_exists(email: str) -> bool:
        """Check if email already exists"""
        query = "SELECT COUNT(*) as count FROM users WHERE email = %s;"
        result = postgres_db.execute_query(query, (email,))
        return result[0]['count'] > 0 if result else False

    @staticmethod
    def update_profile(user_id: str, data: Dict) -> bool:
        """Update user profile fields."""
        try:
            allowed = ['country', 'state', 'building_type', 'address', 'electricity_rate']
            fields  = [f for f in allowed if f in data]
            if not fields:
                return False
            set_clause = ', '.join(f"{f} = %s" for f in fields)
            params     = [data[f] for f in fields] + [user_id]
            query      = f"UPDATE users SET {set_clause} WHERE user_id = %s;"
            postgres_db.execute_query(query, params, fetch=False)
            mongo_db.log_activity(user_id, 'profile_updated', {'fields': fields})
            return True
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False


class Forecast:
    """Forecast model for predictions"""
    
    @staticmethod
    def save(user_id: str, forecast_type: str, predictions: List[Dict]) -> bool:
        """Save forecast predictions"""
        query = """
        INSERT INTO forecasts (user_id, forecast_type, timestamp, predicted_value, 
                              confidence_interval)
        VALUES (%s, %s, %s, %s, %s);
        """
        params_list = [
            (user_id, forecast_type, pred['timestamp'], pred['value'], 
             pred.get('confidence'))
            for pred in predictions
        ]
        return postgres_db.execute_many(query, params_list)
    
    @staticmethod
    def get_recent(user_id: str, forecast_type: str, limit: int = 100) -> List[Dict]:
        """Get recent forecasts"""
        query = """
        SELECT * FROM forecasts 
        WHERE user_id = %s AND forecast_type = %s
        ORDER BY timestamp DESC
        LIMIT %s;
        """
        result = postgres_db.execute_query(query, (user_id, forecast_type, limit))
        return [dict(row) for row in result] if result else []


class Optimization:
    """Optimization results model"""
    
    @staticmethod
    def save(user_id: str, result_data: Dict) -> bool:
        """Save optimization results"""
        query = """
        INSERT INTO optimization_results 
        (user_id, timestamp, energy_saved, cost_saved, battery_level, 
         grid_status, recommendations)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        params = (
            user_id,
            result_data['timestamp'],
            result_data.get('energy_saved', 0),
            result_data.get('cost_saved', 0),
            result_data.get('battery_level', 0),
            result_data.get('grid_status', 'normal'),
            result_data.get('recommendations')
        )
        postgres_db.execute_query(query, params, fetch=False)
        return True
    
    @staticmethod
    def get_recent(user_id: str, limit: int = 50) -> List[Dict]:
        """Get recent optimization results"""
        query = """
        SELECT * FROM optimization_results 
        WHERE user_id = %s
        ORDER BY timestamp DESC
        LIMIT %s;
        """
        result = postgres_db.execute_query(query, (user_id, limit))
        return [dict(row) for row in result] if result else []


class Metrics:
    """Performance metrics model"""
    
    @staticmethod
    def save(user_id: str, metric_type: str, value: float, metadata: Dict = None) -> bool:
        """Save performance metric"""
        query = """
        INSERT INTO performance_metrics (user_id, metric_type, metric_value, metadata)
        VALUES (%s, %s, %s, %s);
        """
        postgres_db.execute_query(query, (user_id, metric_type, value, metadata), fetch=False)
        return True
    
    @staticmethod
    def get_by_type(user_id: str, metric_type: str, limit: int = 100) -> List[Dict]:
        """Get metrics by type"""
        query = """
        SELECT * FROM performance_metrics 
        WHERE user_id = %s AND metric_type = %s
        ORDER BY timestamp DESC
        LIMIT %s;
        """
        result = postgres_db.execute_query(query, (user_id, metric_type, limit))
        return [dict(row) for row in result] if result else []
