"""MongoDB connection and database helpers."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Global MongoDB client
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    """Initialize MongoDB connection."""
    global _client, _database
    
    try:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
        # Test the connection
        await _client.admin.command('ping')
        
        # Extract database name from URI or use default
        _database = _client.get_default_database()
        
        # Create indexes
        await create_indexes()
        
        logger.info("Successfully connected to MongoDB")
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection() -> None:
    """Close MongoDB connection."""
    global _client
    
    if _client:
        _client.close()
        logger.info("Closed MongoDB connection")


def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    if _database is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return _database


def get_sessions_collection():
    """Get the sessions collection."""
    db = get_database()
    return db.sessions


def get_turns_collection():
    """Get the turns collection."""
    db = get_database()
    return db.turns


def get_users_collection():
    """Get the users collection."""
    db = get_database()
    return db.users


async def create_indexes() -> None:
    """Create database indexes."""
    try:
        # Users collection - unique index on email
        users = get_users_collection()
        await users.create_index("email", unique=True)
        logger.info("Created unique index on users.email")
        
        # Sessions collection - compound index for user queries
        sessions = get_sessions_collection()
        await sessions.create_index([("user_id", 1), ("created_at", -1)])
        logger.info("Created index on sessions.user_id + created_at")
        
        # Turns collection - compound index for session queries
        turns = get_turns_collection()
        await turns.create_index([("session_id", 1), ("index", 1)])
        logger.info("Created index on turns.session_id + index")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        raise
