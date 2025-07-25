# tests/test_models/test_document.py

import pytest
from datetime import datetime
from bson import ObjectId

from src.models.document import (
    PyObjectId,
    DocumentMetadata,
    DocumentChunk,
    Document,
    DocumentResponse,
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentProcessingRequest,
    DocumentSearchRequest,
    DocumentSearchResponse
)

class TestPyObjectId:
    """Test suite for PyObjectId custom type"""
    
    def test_pyobjectid_valid_string(self):
        """Test PyObjectId validation with valid ObjectId string"""
        # Arrange
        valid_id = str(ObjectId())
        
        # Act
        result = PyObjectId.validate(valid_id)
        
        # Assert
        assert isinstance(result, str)
        assert result == valid_id
    
    def test_pyobjectid_valid_objectid(self):
        """Test PyObjectId validation with ObjectId instance"""
        # Arrange
        valid_id = ObjectId()
        
        # Act
        result = PyObjectId.validate(valid_id)
        
        # Assert
        assert isinstance(result, str)
        assert result == str(valid_id)
    
    def test_pyobjectid_invalid_string_raises_error(self):
        """Test PyObjectId validation with invalid string"""
        # Arrange
        invalid_id = "invalid_objectid_string"
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            PyObjectId.validate(invalid_id)
        assert "Invalid ObjectId" in str(exc_info.value)
    
    def test_pyobjectid_json_schema_modification(self):
        """Test PyObjectId JSON schema modification"""
        # Arrange
        field_schema = {}
        
        # Act
        PyObjectId.__modify_schema__(field_schema)
        
        # Assert
        assert field_schema["type"] == "string"

class TestDocumentMetadata:
    """Test suite for DocumentMetadata model"""
    
    def test_document_metadata_creation_success(self):
        """Test successful DocumentMetadata creation with required fields"""
        # Arrange & Act
        metadata = DocumentMetadata(
            file_type="text/plain",
            file_size=1024
        )
        
        # Assert
        assert metadata.file_type == "text/plain"
        assert metadata.file_size == 1024
        assert metadata.author is None
        assert metadata.pages is None
        assert metadata.language is None
    
    def test_document_metadata_with_optional_fields(self):
        """Test DocumentMetadata creation with all optional fields"""
        # Arrange & Act
        metadata = DocumentMetadata(
            file_type="application/pdf",
            file_size=2048,
            author="John Doe",
            pages=10,
            language="en",
            word_count=500,
            character_count=3000,
            estimated_reading_time=3
        )
        
        # Assert
        assert metadata.author == "John Doe"
        assert metadata.pages == 10
        assert metadata.language == "en"
        assert metadata.word_count == 500
        assert metadata.character_count == 3000
        assert metadata.estimated_reading_time == 3
    
    def test_document_metadata_missing_required_fields_raises_error(self):
        """Test DocumentMetadata validation with missing required fields"""
        # Act & Assert
        with pytest.raises(ValueError):
            DocumentMetadata(file_size=1024)  # Missing file_type

class TestDocumentChunk:
    """Test suite for DocumentChunk model"""
    
    def test_document_chunk_creation_success(self):
        """Test successful DocumentChunk creation"""
        # Arrange & Act
        chunk = DocumentChunk(
            index=0,
            content="Sample chunk content",
            start_position=0,
            end_position=20,
            word_count=3,
            character_count=20
        )
        
        # Assert
        assert chunk.index == 0
        assert chunk.content == "Sample chunk content"
        assert chunk.start_position == 0
        assert chunk.end_position == 20
        assert chunk.word_count == 3
        assert chunk.character_count == 20
    
    def test_document_chunk_serialization(self):
        """Test DocumentChunk serialization to dict"""
        # Arrange
        chunk = DocumentChunk(
            index=1,
            content="Test content",
            start_position=10,
            end_position=22,
            word_count=2,
            character_count=12
        )
        
        # Act
        chunk_dict = chunk.model_dump()
        
        # Assert
        assert chunk_dict["index"] == 1
        assert chunk_dict["content"] == "Test content"
        assert chunk_dict["start_position"] == 10
        assert chunk_dict["end_position"] == 22

class TestDocument:
    """Test suite for Document model"""
    
    def test_document_creation_with_minimal_fields(self, sample_metadata):
        """Test Document creation with minimal required fields"""
        # Arrange
        metadata = DocumentMetadata(**sample_metadata)
        
        # Act
        document = Document(
            title="Test Document",
            content="Sample content",
            metadata=metadata
        )
        
        # Assert
        assert document.title == "Test Document"
        assert document.content == "Sample content"
        assert document.status == "processing"  # Default value
        assert isinstance(document.uploaded_at, datetime)
        assert document.processed_at is None
        assert document.user_id is None
        assert len(document.chunks) == 0
    
    def test_document_creation_with_all_fields(self, sample_metadata):
        """Test Document creation with all fields populated"""
        # Arrange
        metadata = DocumentMetadata(**sample_metadata)
        chunks = [
            DocumentChunk(
                index=0,
                content="Chunk 1",
                start_position=0,
                end_position=7,
                word_count=2,
                character_count=7
            )
        ]
        upload_time = datetime.utcnow()
        process_time = datetime.utcnow()
        
        # Act
        document = Document(
            title="Complete Document",
            content="Full content here",
            summary="Brief summary",
            chunks=chunks,
            user_id="user_123",
            uploaded_at=upload_time,
            processed_at=process_time,
            metadata=metadata,
            status="completed"
        )
        
        # Assert
        assert document.title == "Complete Document"
        assert document.summary == "Brief summary"
        assert len(document.chunks) == 1
        assert document.user_id == "user_123"
        assert document.uploaded_at == upload_time
        assert document.processed_at == process_time
        assert document.status == "completed"
    
    def test_document_objectid_handling(self, sample_metadata):
        """Test Document ObjectId field handling"""
        # Arrange
        metadata = DocumentMetadata(**sample_metadata)
        custom_id = ObjectId()
        
        # Act
        document = Document(
            id=str(custom_id),
            title="Test Document",
            content="Sample content",
            metadata=metadata
        )
        
        # Assert
        assert document.id == str(custom_id)
        assert isinstance(document.id, str)
    
    def test_document_json_serialization(self, sample_metadata):
        """Test Document JSON serialization with ObjectId"""
        # Arrange
        metadata = DocumentMetadata(**sample_metadata)
        document = Document(
            title="Test Document",
            content="Sample content",
            metadata=metadata
        )
        
        # Act
        json_data = document.model_dump_json()
        
        # Assert
        assert '"title":"Test Document"' in json_data
        assert '"status":"processing"' in json_data
        # ObjectId should be serialized as string
        assert '"id":' in json_data

class TestDocumentResponse:
    """Test suite for DocumentResponse model"""
    
    def test_document_response_creation(self, sample_metadata):
        """Test DocumentResponse creation"""
        # Arrange
        metadata = DocumentMetadata(**sample_metadata)
        upload_time = datetime.utcnow()
        
        # Act
        response = DocumentResponse(
            id=str(ObjectId()),
            title="Response Document",
            chunks_count=5,
            uploaded_at=upload_time,
            metadata=metadata,
            status="completed"
        )
        
        # Assert
        assert response.title == "Response Document"
        assert response.chunks_count == 5
        assert response.uploaded_at == upload_time
        assert response.status == "completed"
        assert response.summary is None  # Optional field

class TestDocumentUploadResponse:
    """Test suite for DocumentUploadResponse model"""
    
    def test_document_upload_response_creation(self):
        """Test DocumentUploadResponse creation"""
        # Act
        response = DocumentUploadResponse(
            document_id=str(ObjectId()),
            filename="uploaded_file.txt",
            status="processed",
            chunks_count=3,
            message="Upload successful"
        )
        
        # Assert
        assert response.filename == "uploaded_file.txt"
        assert response.status == "processed"
        assert response.chunks_count == 3
        assert response.message == "Upload successful"

class TestDocumentListResponse:
    """Test suite for DocumentListResponse model"""
    
    def test_document_list_response_creation(self, sample_metadata):
        """Test DocumentListResponse creation"""
        # Arrange
        metadata = DocumentMetadata(**sample_metadata)
        documents = [
            DocumentResponse(
                id=str(ObjectId()),
                title="Document 1",
                chunks_count=2,
                uploaded_at=datetime.utcnow(),
                metadata=metadata,
                status="completed"
            )
        ]
        
        # Act
        response = DocumentListResponse(
            documents=documents,
            total=1,
            page=1,
            per_page=20,
            has_next=False,
            has_prev=False
        )
        
        # Assert
        assert len(response.documents) == 1
        assert response.total == 1
        assert response.page == 1
        assert response.per_page == 20
        assert response.has_next is False
        assert response.has_prev is False

class TestDocumentProcessingRequest:
    """Test suite for DocumentProcessingRequest model"""
    
    def test_document_processing_request_creation(self):
        """Test DocumentProcessingRequest creation"""
        # Act
        request = DocumentProcessingRequest(
            text="Text to process",
            filename="process_me.txt",
            file_type="text/plain",
            user_id="user_456"
        )
        
        # Assert
        assert request.text == "Text to process"
        assert request.filename == "process_me.txt"
        assert request.file_type == "text/plain"
        assert request.user_id == "user_456"
        assert request.processing_options is None

class TestDocumentSearchRequest:
    """Test suite for DocumentSearchRequest model"""
    
    def test_document_search_request_creation(self):
        """Test DocumentSearchRequest creation with defaults"""
        # Act
        request = DocumentSearchRequest(query="search term")
        
        # Assert
        assert request.query == "search term"
        assert request.user_id is None
        assert request.filters is None
        assert request.limit == 20  # Default value
        assert request.skip == 0    # Default value
    
    def test_document_search_request_with_all_fields(self):
        """Test DocumentSearchRequest creation with all fields"""
        # Act
        request = DocumentSearchRequest(
            query="AI and ML",
            user_id="user_789",
            filters={"language": "en"},
            limit=10,
            skip=5
        )
        
        # Assert
        assert request.query == "AI and ML"
        assert request.user_id == "user_789"
        assert request.filters == {"language": "en"}
        assert request.limit == 10
        assert request.skip == 5

class TestDocumentSearchResponse:
    """Test suite for DocumentSearchResponse model"""
    
    def test_document_search_response_creation(self, sample_metadata):
        """Test DocumentSearchResponse creation"""
        # Arrange
        metadata = DocumentMetadata(**sample_metadata)
        documents = [
            DocumentResponse(
                id=str(ObjectId()),
                title="Search Result 1",
                chunks_count=1,
                uploaded_at=datetime.utcnow(),
                metadata=metadata,
                status="completed"
            )
        ]
        
        # Act
        response = DocumentSearchResponse(
            documents=documents,
            total_results=1,
            query="test query",
            took_ms=150
        )
        
        # Assert
        assert len(response.documents) == 1
        assert response.total_results == 1
        assert response.query == "test query"
        assert response.took_ms == 150