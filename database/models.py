"""
Database models — all User operations use MongoDB Atlas.
PostgreSQL was the original backend but is unavailable on Render (no hosted
Postgres configured), so every User method now reads/writes the 'users'
collection in MongoDB. Sessions, logs, and caches were already in MongoDB.
"""
from datetime import datetime
from typing import Optional, Dict, List
from database.mongo_handler import mongo_db
import logging

logger = logging.getLogger(__name__)


class User:
    _COL = 'users'

    @staticmethod
    def create(user_data: Dict) -> Optional[str]:
        doc = {
            **user_data,
            'created_at': datetime.utcnow(),
            'last_login':  None,
            'is_active':   True,
        }
        result = mongo_db.insert_one(User._COL, doc)
        if result:
            mongo_db.log_activity(user_data['user_id'], 'user_created', {
                'country':       user_data['country'],
                'building_type': user_data['building_type'],
            })
            return user_data['user_id']
        return None

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict]:
        return mongo_db.find_one(User._COL, {'email': email, 'is_active': True})

    @staticmethod
    def get_by_user_id(user_id: str) -> Optional[Dict]:
        return mongo_db.find_one(User._COL, {'user_id': user_id, 'is_active': True})

    @staticmethod
    def get_by_provider(provider: str, provider_id: str) -> Optional[Dict]:
        return mongo_db.find_one(User._COL, {
            'auth_provider': provider,
            'provider_id':   provider_id,
            'is_active':     True,
        })

    @staticmethod
    def update_last_login(user_id: str):
        mongo_db.update_one(User._COL, {'user_id': user_id}, {'last_login': datetime.utcnow()})
        mongo_db.log_activity(user_id, 'user_login')

    @staticmethod
    def update_password(user_id: str, password_hash: str) -> bool:
        try:
            mongo_db.update_one(User._COL, {'user_id': user_id}, {'password_hash': password_hash})
            mongo_db.log_activity(user_id, 'password_changed')
            return True
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False

    @staticmethod
    def email_exists(email: str) -> bool:
        return mongo_db.find_one(User._COL, {'email': email}) is not None

    @staticmethod
    def update_profile(user_id: str, data: Dict) -> bool:
        allowed = ['country', 'state', 'building_type', 'address', 'electricity_rate']
        update = {k: v for k, v in data.items() if k in allowed}
        if not update:
            return False
        try:
            mongo_db.update_one(User._COL, {'user_id': user_id}, update)
            mongo_db.log_activity(user_id, 'profile_updated', {'fields': list(update.keys())})
            return True
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False


class Forecast:
    @staticmethod
    def save(user_id: str, forecast_type: str, predictions: List[Dict]) -> bool:
        docs = [
            {'user_id': user_id, 'forecast_type': forecast_type,
             'timestamp': p['timestamp'], 'predicted_value': p['value'],
             'confidence_interval': p.get('confidence'),
             'created_at': datetime.utcnow()}
            for p in predictions
        ]
        return bool(mongo_db.insert_many('forecasts', docs))

    @staticmethod
    def get_recent(user_id: str, forecast_type: str, limit: int = 100) -> List[Dict]:
        return mongo_db.find_many('forecasts',
            {'user_id': user_id, 'forecast_type': forecast_type},
            limit=limit, sort=[('timestamp', -1)])


class Optimization:
    @staticmethod
    def save(user_id: str, result_data: Dict) -> bool:
        doc = {'user_id': user_id, 'created_at': datetime.utcnow(), **result_data}
        return bool(mongo_db.insert_one('optimization_results', doc))

    @staticmethod
    def get_recent(user_id: str, limit: int = 50) -> List[Dict]:
        return mongo_db.find_many('optimization_results',
            {'user_id': user_id}, limit=limit, sort=[('timestamp', -1)])


class Metrics:
    @staticmethod
    def save(user_id: str, metric_type: str, value: float, metadata: Dict = None) -> bool:
        doc = {'user_id': user_id, 'metric_type': metric_type,
               'metric_value': value, 'metadata': metadata or {},
               'timestamp': datetime.utcnow()}
        return bool(mongo_db.insert_one('performance_metrics', doc))

    @staticmethod
    def get_by_type(user_id: str, metric_type: str, limit: int = 100) -> List[Dict]:
        return mongo_db.find_many('performance_metrics',
            {'user_id': user_id, 'metric_type': metric_type},
            limit=limit, sort=[('timestamp', -1)])
