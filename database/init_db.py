"""
Database initialization script
Run this to set up the database tables and indexes
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.postgres_handler import postgres_db
from database.mongo_handler import mongo_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_databases():
    """Initialize both PostgreSQL and MongoDB"""
    logger.info("Starting database initialization...")
    
    # Initialize PostgreSQL
    logger.info("Setting up PostgreSQL tables...")
    if postgres_db.create_tables():
        logger.info("✓ PostgreSQL tables created successfully")
    else:
        logger.error("✗ Failed to create PostgreSQL tables")
        return False
    
    # MongoDB collections are created automatically
    if mongo_db.db is not None:
        logger.info("✓ MongoDB collections initialized successfully")
    else:
        logger.error("✗ Failed to initialize MongoDB")
        return False
    
    logger.info("Database initialization completed successfully!")
    return True


if __name__ == "__main__":
    try:
        success = init_databases()
        if success:
            print("\n✓ Database setup complete!")
            print("\nNext steps:")
            print("1. Copy .env.example to .env")
            print("2. Fill in your credentials in .env")
            print("3. Start backend:  cd backend && python app.py")
            print("4. Start frontend: cd microgrid-ui && npm run dev")
            print("   Then open http://localhost:3000")
        else:
            print("\n✗ Database setup failed. Check logs for details.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        print(f"\n✗ Error: {e}")
        sys.exit(1)
