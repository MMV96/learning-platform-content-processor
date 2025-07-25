# learning-platform-content-processor/src/database.py

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Global MongoDB client
mongodb_client: AsyncIOMotorClient = None

def get_mongodb_client() -> AsyncIOMotorClient:
    """Get MongoDB client instance"""
    global mongodb_client
    
    if mongodb_client is None:
        try:
            mongodb_client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=10,
                minPoolSize=1,
                maxIdleTimeMS=45000,
                waitQueueTimeoutMS=5000,
                serverSelectionTimeoutMS=5000
            )
            logger.info("MongoDB client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}")
            raise
    
    return mongodb_client

def get_database():
    """Dependency to get database instance"""
    client = get_mongodb_client()
    return client[settings.DATABASE_NAME]

async def close_mongodb_connection():
    """Close MongoDB connection"""
    global mongodb_client
    
    if mongodb_client:
        mongodb_client.close()
        mongodb_client = None
        logger.info("MongoDB connection closed")


# Database Collections
class Collections:
    """Database collection names"""
    BOOKS = "books"
    QUIZZES = "quizzes"
    QUIZ_SESSIONS = "quiz_sessions"
    FLASHCARDS = "flashcards"
    USERS = "users"

# Database Indexes
async def create_indexes(db):
    """Create database indexes for optimal performance"""
    try:
        # Books collection indexes
        await db[Collections.BOOKS].create_index("userId")
        await db[Collections.BOOKS].create_index("uploadedAt")
        await db[Collections.BOOKS].create_index([("title", "text"), ("content", "text")])
        
        # Quizzes collection indexes
        await db[Collections.QUIZZES].create_index("bookId")
        await db[Collections.QUIZZES].create_index("createdAt")
        
        # Quiz sessions collection indexes
        await db[Collections.QUIZ_SESSIONS].create_index("userId")
        await db[Collections.QUIZ_SESSIONS].create_index("quizId")
        await db[Collections.QUIZ_SESSIONS].create_index("completedAt")
        
        # Flashcards collection indexes
        await db[Collections.FLASHCARDS].create_index("userId")
        await db[Collections.FLASHCARDS].create_index("bookId")
        await db[Collections.FLASHCARDS].create_index("nextReview")
        
        # Users collection indexes
        await db[Collections.USERS].create_index("email", unique=True)
        
        logger.info("✅ Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create database indexes: {e}")
        raise

# Initialize client on module import
mongodb_client = get_mongodb_client()