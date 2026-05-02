"""
MongoDB handler for logs, sessions, and unstructured data
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ConfigurationError
from datetime import datetime
from config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MongoHandler:
    """MongoDB connection and operations handler"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[config.MONGODB_DB]
            logger.info("MongoDB connection established successfully")
            self._create_collections()
        except (ConnectionFailure, OperationFailure, ConfigurationError) as e:
            logger.error(f"MongoDB connection failed: {e}")
            self.client = None
            self.db = None
    
    def _create_collections(self):
        """Create necessary collections and indexes"""
        if self.db is None:
            return
        
        try:
            # User sessions
            if 'sessions' not in self.db.list_collection_names():
                self.db.create_collection('sessions')
                self.db.sessions.create_index('user_id')
                self.db.sessions.create_index('session_id', unique=True)
                self.db.sessions.create_index('expires_at', expireAfterSeconds=0)
            
            # Activity logs
            if 'activity_logs' not in self.db.list_collection_names():
                self.db.create_collection('activity_logs')
                self.db.activity_logs.create_index('user_id')
                self.db.activity_logs.create_index('timestamp')
                self.db.activity_logs.create_index('action')
            
            # System logs
            if 'system_logs' not in self.db.list_collection_names():
                self.db.create_collection('system_logs')
                self.db.system_logs.create_index('timestamp')
                self.db.system_logs.create_index('level')
            
            # ML model predictions cache
            if 'predictions_cache' not in self.db.list_collection_names():
                self.db.create_collection('predictions_cache')
                self.db.predictions_cache.create_index('user_id')
                self.db.predictions_cache.create_index('timestamp')
                self.db.predictions_cache.create_index('cache_key', unique=True)
            
            logger.info("MongoDB collections and indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating MongoDB collections: {e}")
    
    def insert_one(self, collection_name, document):
        """Insert a single document"""
        try:
            if self.db is None:
                return None
            result = self.db[collection_name].insert_one(document)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
            return None
    
    def insert_many(self, collection_name, documents):
        """Insert multiple documents"""
        try:
            if self.db is None:
                return None
            result = self.db[collection_name].insert_many(documents)
            return result.inserted_ids
        except Exception as e:
            logger.error(f"Error inserting documents: {e}")
            return None
    
    def find_one(self, collection_name, query):
        """Find a single document"""
        try:
            if self.db is None:
                return None
            return self.db[collection_name].find_one(query)
        except Exception as e:
            logger.error(f"Error finding document: {e}")
            return None
    
    def find_many(self, collection_name, query, limit=None, sort=None):
        """Find multiple documents"""
        try:
            if self.db is None:
                return []
            cursor = self.db[collection_name].find(query)
            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error finding documents: {e}")
            return []
    
    def update_one(self, collection_name, query, update):
        """Update a single document"""
        try:
            if self.db is None:
                return False
            result = self.db[collection_name].update_one(query, {'$set': update})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return False
    
    def delete_one(self, collection_name, query):
        """Delete a single document"""
        try:
            if self.db is None:
                return False
            result = self.db[collection_name].delete_one(query)
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    def log_activity(self, user_id, action, details=None):
        """Log user activity"""
        log_entry = {
            'user_id': user_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.utcnow()
        }
        return self.insert_one('activity_logs', log_entry)
    
    def create_session(self, user_id, session_id, expires_at):
        """Create a user session"""
        session = {
            'user_id': user_id,
            'session_id': session_id,
            'created_at': datetime.utcnow(),
            'expires_at': expires_at,
            'last_activity': datetime.utcnow()
        }
        return self.insert_one('sessions', session)
    
    def get_session(self, session_id):
        """Retrieve session by session ID"""
        return self.find_one('sessions', {'session_id': session_id})
    
    def update_session_activity(self, session_id):
        """Update last activity timestamp for a session"""
        return self.update_one(
            'sessions',
            {'session_id': session_id},
            {'last_activity': datetime.utcnow()}
        )
    
    def delete_session(self, session_id):
        """Delete a session"""
        return self.delete_one('sessions', {'session_id': session_id})
    
    def cache_prediction(self, user_id, cache_key, prediction_data, ttl=3600):
        """Cache ML prediction results"""
        from datetime import timedelta
        cache_entry = {
            'user_id': user_id,
            'cache_key': cache_key,
            'data': prediction_data,
            'timestamp': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
        }
        try:
            self.db.predictions_cache.update_one(
                {'cache_key': cache_key},
                {'$set': cache_entry},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error caching prediction: {e}")
            return False
    
    def get_cached_prediction(self, cache_key):
        """Retrieve cached prediction"""
        cache_entry = self.find_one('predictions_cache', {
            'cache_key': cache_key,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        return cache_entry['data'] if cache_entry else None
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


# Singleton instance
mongo_db = MongoHandler()
