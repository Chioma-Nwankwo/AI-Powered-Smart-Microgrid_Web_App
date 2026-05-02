"""
PostgreSQL database handler for user data and structured information
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from contextlib import contextmanager
from config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PostgresHandler:
    """PostgreSQL database connection and operations handler"""
    
    def __init__(self):
        """Initialize PostgreSQL connection pool"""
        host = config.POSTGRES_HOST
        if host in ('localhost', '127.0.0.1', ''):
            # No production PostgreSQL — skip silently. MongoDB is the production database.
            logger.info("PostgreSQL: localhost host — skipping (MongoDB in use)")
            self.connection_pool = None
            return
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=host,
                port=config.POSTGRES_PORT,
                database=config.POSTGRES_DB,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD
            )
            logger.info("PostgreSQL connection pool created successfully")
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed (non-fatal): {e}")
            self.connection_pool = None
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            if self.connection_pool:
                conn = self.connection_pool.getconn()
                yield conn
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn and self.connection_pool:
                self.connection_pool.putconn(conn)
    
    def execute_query(self, query, params=None, fetch=True):
        """Execute a query and return results"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params or ())
                    if fetch:
                        return cursor.fetchall()
                    return None
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return None
    
    def execute_many(self, query, params_list):
        """Execute multiple queries"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    return True
        except Exception as e:
            logger.error(f"Batch execution error: {e}")
            return False
    
    def create_tables(self):
        """Create necessary database tables"""
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255),
            country VARCHAR(100) NOT NULL,
            state VARCHAR(100) NOT NULL,
            building_type VARCHAR(50) NOT NULL,
            address TEXT NOT NULL,
            auth_provider VARCHAR(50) DEFAULT 'email',
            provider_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
        """
        
        create_forecasts_table = """
        CREATE TABLE IF NOT EXISTS forecasts (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) REFERENCES users(user_id),
            forecast_type VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            predicted_value FLOAT NOT NULL,
            actual_value FLOAT,
            confidence_interval JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        create_optimization_table = """
        CREATE TABLE IF NOT EXISTS optimization_results (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) REFERENCES users(user_id),
            timestamp TIMESTAMP NOT NULL,
            energy_saved FLOAT,
            cost_saved FLOAT,
            battery_level FLOAT,
            grid_status VARCHAR(50),
            recommendations JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        create_metrics_table = """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) REFERENCES users(user_id),
            metric_type VARCHAR(50) NOT NULL,
            metric_value FLOAT NOT NULL,
            metadata JSONB,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_forecasts_user ON forecasts(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_forecasts_timestamp ON forecasts(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_optimization_user ON optimization_results(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_metrics_user ON performance_metrics(user_id);"
        ]
        
        try:
            # Create tables
            self.execute_query(create_users_table, fetch=False)
            self.execute_query(create_forecasts_table, fetch=False)
            self.execute_query(create_optimization_table, fetch=False)
            self.execute_query(create_metrics_table, fetch=False)
            
            # Create indexes
            for index_query in create_indexes:
                self.execute_query(index_query, fetch=False)
            
            logger.info("Database tables created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            return False
    
    def close(self):
        """Close all connections in the pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("PostgreSQL connection pool closed")


# Singleton instance
postgres_db = PostgresHandler()
