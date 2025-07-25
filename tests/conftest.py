import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from bson import ObjectId

# Set test environment before any imports
os.environ['TESTING'] = 'true'
os.environ['MONGODB_URL'] = 'mongodb://admin:password123@localhost:27017/learning_platform_test?authSource=admin'
os.environ['DATABASE_NAME'] = 'learning_platform_test'
os.environ['DEBUG'] = 'true'

# Test data
SAMPLE_TEXT = """
Artificial Intelligence and Machine Learning

Artificial Intelligence (AI) is a field of computer science that aims to create 
intelligent machines that can perform tasks that typically require human intelligence.

Machine Learning (ML) is a subset of AI that focuses on the development of algorithms
that can learn and improve from experience without being explicitly programmed.

Deep Learning is a subset of machine learning that uses neural networks with multiple
layers to analyze and learn from large amounts of data.

Key applications of AI include:
1. Natural Language Processing
2. Computer Vision
3. Speech Recognition
4. Autonomous Vehicles
5. Medical Diagnosis

The future of AI looks promising with continued advancements in technology.
"""

SAMPLE_PDF_TEXT = """
Introduction to Python Programming

Python is a high-level, interpreted programming language known for its simplicity 
and readability. It was created by Guido van Rossum and first released in 1991.

Key Features:
- Easy to learn and use
- Cross-platform compatibility  
- Large standard library
- Strong community support

Python is widely used in web development, data science, artificial intelligence,
and automation tasks.
"""

@pytest.fixture
def sample_text():
    """Sample text for testing document processing"""
    return SAMPLE_TEXT.strip()

@pytest.fixture
def sample_pdf_text():
    """Sample PDF text for testing text extraction"""
    return SAMPLE_PDF_TEXT.strip()

@pytest.fixture
def sample_metadata():
    """Sample document metadata"""
    return {
        "file_type": "text/plain",
        "file_size": 1024,
        "word_count": 150,
        "character_count": 850,
        "estimated_reading_time": 1,
        "language": "en"
    }

@pytest.fixture
def mock_database():
    """Mock database instance"""
    db = MagicMock()
    
    # Mock collection with async methods
    collection = AsyncMock()
    db.__getitem__.return_value = collection
    
    # Mock common database operations
    collection.insert_one.return_value = AsyncMock(inserted_id=ObjectId())
    collection.find_one.return_value = None
    collection.find.return_value = AsyncMock()
    collection.delete_one.return_value = AsyncMock(deleted_count=1)
    collection.update_one.return_value = AsyncMock(modified_count=1)
    
    return db

@pytest.fixture
def mock_upload_file():
    """Mock FastAPI UploadFile"""
    file = MagicMock()
    file.filename = "test_document.txt"
    file.content_type = "text/plain"
    file.size = 1024
    file.read = AsyncMock(return_value=SAMPLE_TEXT.encode('utf-8'))
    return file

@pytest.fixture
def mock_pdf_file():
    """Mock PDF UploadFile"""
    file = MagicMock()
    file.filename = "test_document.pdf"
    file.content_type = "application/pdf"
    file.size = 2048
    file.read = AsyncMock(return_value=b"%PDF-1.4 fake pdf content")
    return file

@pytest.fixture
def sample_document_dict():
    """Sample document dictionary from database"""
    return {
        "_id": ObjectId(),
        "title": "Test Document",
        "content": SAMPLE_TEXT,
        "summary": "A test document about AI and ML...",
        "chunks": [
            {
                "index": 0,
                "content": "Artificial Intelligence and Machine Learning...",
                "start_position": 0,
                "end_position": 100,
                "word_count": 15,
                "character_count": 100
            }
        ],
        "user_id": "test_user_123",
        "uploaded_at": datetime.utcnow(),
        "processed_at": datetime.utcnow(),
        "metadata": {
            "file_type": "text/plain",
            "file_size": 1024,
            "word_count": 150,
            "character_count": 850,
            "estimated_reading_time": 1,
            "language": "en"
        },
        "status": "completed"
    }

@pytest.fixture
def mock_settings():
    """Mock application settings"""
    settings = MagicMock()
    settings.CHUNK_SIZE = 1000
    settings.CHUNK_OVERLAP = 100
    settings.MIN_CHUNK_SIZE = 100
    settings.MAX_FILE_SIZE = 50 * 1024 * 1024
    settings.ALLOWED_FILE_TYPES = [
        "application/pdf",
        "text/plain",
        "application/epub+zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    settings.ALLOWED_FILE_EXTENSIONS = [".pdf", ".txt", ".epub", ".docx"]
    return settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Test data builders
class DocumentBuilder:
    """Builder pattern for creating test documents"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self._title = "Test Document"
        self._content = SAMPLE_TEXT
        self._user_id = "test_user_123"
        self._file_type = "text/plain"
        self._file_size = 1024
        return self
    
    def with_title(self, title):
        self._title = title
        return self
    
    def with_content(self, content):
        self._content = content
        return self
    
    def with_user_id(self, user_id):
        self._user_id = user_id
        return self
    
    def with_file_type(self, file_type):
        self._file_type = file_type
        return self
    
    def with_file_size(self, file_size):
        self._file_size = file_size
        return self
    
    def build_dict(self):
        """Build document as dictionary"""
        return {
            "_id": ObjectId(),
            "title": self._title,
            "content": self._content,
            "user_id": self._user_id,
            "uploaded_at": datetime.utcnow(),
            "processed_at": datetime.utcnow(),
            "metadata": {
                "file_type": self._file_type,
                "file_size": self._file_size,
                "word_count": len(self._content.split()),
                "character_count": len(self._content),
                "estimated_reading_time": max(1, len(self._content.split()) // 200),
                "language": "en"
            },
            "chunks": [],
            "status": "completed"
        }

@pytest.fixture
def document_builder():
    """Factory for building test documents"""
    return DocumentBuilder()