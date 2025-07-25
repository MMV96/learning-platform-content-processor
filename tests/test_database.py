import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

from src.database import (
    get_mongodb_client,
    get_database,
    close_mongodb_connection,
    create_indexes,
    Collections
)

class TestMongoDBClient:
    """Test suite for MongoDB client management"""
    
    def test_get_mongodb_client_creates_client(self):
        """Test that get_mongodb_client creates and returns client"""
        # Arrange
        with patch('src.database.mongodb_client', None):
            with patch('src.database.AsyncIOMotorClient') as mock_client_class:
                mock_client_instance = MagicMock()
                mock_client_class.return_value = mock_client_instance
                
                # Act
                result = get_mongodb_client()
        
        # Assert
        assert result == mock_client_instance
        mock_client_class.assert_called_once()
    
    def test_get_mongodb_client_returns_existing_client(self):
        """Test that get_mongodb_client returns existing client if available"""
        # Arrange
        existing_client = MagicMock()
        
        with patch('src.database.mongodb_client', existing_client):
            # Act
            result = get_mongodb_client()
        
        # Assert
        assert result == existing_client
    
    def test_get_mongodb_client_with_correct_parameters(self):
        """Test that MongoDB client is created with correct parameters"""
        # Arrange
        with patch('src.database.mongodb_client', None):
            with patch('src.database.AsyncIOMotorClient') as mock_client_class:
                with patch('src.database.settings') as mock_settings:
                    mock_settings.MONGODB_URL = "mongodb://test:27017/test"
                    
                    # Act
                    get_mongodb_client()
        
        # Assert
        mock_client_class.assert_called_once_with(
            "mongodb://test:27017/test",
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=45000,
            waitQueueTimeoutMS=5000,
            serverSelectionTimeoutMS=5000
        )
    
    def test_get_mongodb_client_handles_initialization_error(self):
        """Test that get_mongodb_client handles initialization errors properly"""
        # Arrange
        with patch('src.database.mongodb_client', None):
            with patch('src.database.AsyncIOMotorClient', side_effect=Exception("Connection failed")):
                # Act & Assert
                with pytest.raises(Exception) as exc_info:
                    get_mongodb_client()
                assert "Connection failed" in str(exc_info.value)

class TestGetDatabase:
    """Test suite for database dependency function"""
    
    def test_get_database_returns_database_instance(self):
        """Test that get_database returns correct database instance"""
        # Arrange
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_client.__getitem__.return_value = mock_database
        
        with patch('src.database.get_mongodb_client', return_value=mock_client):
            with patch('src.database.settings') as mock_settings:
                mock_settings.DATABASE_NAME = "test_db"
                
                # Act
                result = get_database()
        
        # Assert
        assert result == mock_database
        mock_client.__getitem__.assert_called_once_with("test_db")
    
    def test_get_database_uses_correct_database_name(self):
        """Test that get_database uses the correct database name from settings"""
        # Arrange
        mock_client = MagicMock()
        
        with patch('src.database.get_mongodb_client', return_value=mock_client):
            with patch('src.database.settings') as mock_settings:
                mock_settings.DATABASE_NAME = "learning_platform"
                
                # Act
                get_database()
        
        # Assert
        mock_client.__getitem__.assert_called_once_with("learning_platform")

class TestCloseMongoDBConnection:
    """Test suite for closing MongoDB connection"""
    
    @pytest.mark.asyncio
    async def test_close_mongodb_connection_closes_existing_client(self):
        """Test that close_mongodb_connection closes existing client"""
        # Arrange
        mock_client = MagicMock()
        
        with patch('src.database.mongodb_client', mock_client):
            # Act
            await close_mongodb_connection()
        
        # Assert
        mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_mongodb_connection_handles_no_client(self):
        """Test that close_mongodb_connection handles case with no client"""
        # Arrange
        with patch('src.database.mongodb_client', None):
            # Act & Assert - should not raise
            await close_mongodb_connection()


class TestCollections:
    """Test suite for Collections class"""
    
    def test_collections_constants_exist(self):
        """Test that all expected collection constants exist"""
        # Assert
        assert hasattr(Collections, 'BOOKS')
        assert hasattr(Collections, 'QUIZZES')
        assert hasattr(Collections, 'QUIZ_SESSIONS')
        assert hasattr(Collections, 'FLASHCARDS')
        assert hasattr(Collections, 'USERS')
    
    def test_collections_values_are_strings(self):
        """Test that collection constants have expected string values"""
        # Assert
        assert Collections.BOOKS == "books"
        assert Collections.QUIZZES == "quizzes"
        assert Collections.QUIZ_SESSIONS == "quiz_sessions"
        assert Collections.FLASHCARDS == "flashcards"
        assert Collections.USERS == "users"

class TestCreateIndexes:
    """Test suite for database index creation"""
    
    @pytest.mark.asyncio
    async def test_create_indexes_creates_all_indexes(self):
        """Test that create_indexes creates all required indexes"""
        # Arrange
        mock_db = MagicMock()
        
        # Mock collections
        mock_books = AsyncMock()
        mock_quizzes = AsyncMock()
        mock_quiz_sessions = AsyncMock()
        mock_flashcards = AsyncMock()
        mock_users = AsyncMock()
        
        mock_db.__getitem__.side_effect = lambda col: {
            "books": mock_books,
            "quizzes": mock_quizzes,
            "quiz_sessions": mock_quiz_sessions,
            "flashcards": mock_flashcards,
            "users": mock_users
        }[col]
        
        # Act
        await create_indexes(mock_db)
        
        # Assert - Books collection indexes
        mock_books.create_index.assert_any_call("userId")
        mock_books.create_index.assert_any_call("uploadedAt")
        mock_books.create_index.assert_any_call([("title", "text"), ("content", "text")])
        
        # Assert - Quizzes collection indexes
        mock_quizzes.create_index.assert_any_call("bookId")
        mock_quizzes.create_index.assert_any_call("createdAt")
        
        # Assert - Quiz sessions collection indexes
        mock_quiz_sessions.create_index.assert_any_call("userId")
        mock_quiz_sessions.create_index.assert_any_call("quizId")
        mock_quiz_sessions.create_index.assert_any_call("completedAt")
        
        # Assert - Flashcards collection indexes
        mock_flashcards.create_index.assert_any_call("userId")
        mock_flashcards.create_index.assert_any_call("bookId")
        mock_flashcards.create_index.assert_any_call("nextReview")
        
        # Assert - Users collection indexes
        mock_users.create_index.assert_any_call("email", unique=True)
    
    @pytest.mark.asyncio
    async def test_create_indexes_handles_creation_error(self):
        """Test that create_indexes handles index creation errors"""
        # Arrange
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_collection.create_index.side_effect = Exception("Index creation failed")
        mock_db.__getitem__.return_value = mock_collection
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await create_indexes(mock_db)
        assert "Index creation failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_indexes_books_text_index(self):
        """Test that books collection gets compound text index"""
        # Arrange
        mock_db = MagicMock()
        mock_books = AsyncMock()
        mock_db.__getitem__.return_value = mock_books
        
        # Act
        await create_indexes(mock_db)
        
        # Assert - Check that compound text index is created
        expected_text_index = [("title", "text"), ("content", "text")]
        mock_books.create_index.assert_any_call(expected_text_index)
    
    @pytest.mark.asyncio
    async def test_create_indexes_users_unique_email(self):
        """Test that users collection gets unique email index"""
        # Arrange
        mock_db = MagicMock()
        mock_users = AsyncMock()
        
        def get_collection(name):
            if name == "users":
                return mock_users
            return AsyncMock()
        
        mock_db.__getitem__.side_effect = get_collection
        
        # Act
        await create_indexes(mock_db)
        
        # Assert - Check that unique email index is created
        mock_users.create_index.assert_any_call("email", unique=True)

class TestDatabaseIntegration:
    """Integration tests for database functionality"""
    
    def test_mongodb_client_singleton_behavior(self):
        """Test that mongodb_client behaves as singleton"""
        # Act
        client1 = get_mongodb_client()
        client2 = get_mongodb_client()
        
        # Assert
        assert client1 is client2  # Same instance
    
    @pytest.mark.asyncio
    async def test_database_workflow_integration(self):
        """Test complete database workflow integration"""
        # Arrange
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_database = MagicMock()
        mock_client.__getitem__.return_value = mock_database
        
        with patch('src.database.AsyncIOMotorClient', return_value=mock_client):
            with patch('src.database.mongodb_client', None):  # Reset singleton
                # Act
                client = get_mongodb_client()
                database = get_database()
                await close_mongodb_connection()
        
        # Assert
        assert client == mock_client
        assert database == mock_database
        mock_client.close.assert_called_once()
    
    def test_database_settings_integration(self):
        """Test database functions use settings correctly"""
        # Arrange
        with patch('src.database.settings') as mock_settings:
            mock_settings.MONGODB_URL = "mongodb://test:27017/test"
            mock_settings.DATABASE_NAME = "test_database"
            
            with patch('src.database.mongodb_client', None):
                with patch('src.database.AsyncIOMotorClient') as mock_client_class:
                    mock_client = MagicMock()
                    mock_client_class.return_value = mock_client
                    
                    # Act
                    get_mongodb_client()
                    get_database()
        
        # Assert
        mock_client_class.assert_called_once_with(
            "mongodb://test:27017/test",
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=45000,
            waitQueueTimeoutMS=5000,
            serverSelectionTimeoutMS=5000
        )
        mock_client.__getitem__.assert_called_once_with("test_database")