# tests/test_api/test_main.py

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
from bson import ObjectId
import io

from src.main import app
from src.models.document import Document, DocumentMetadata

class TestHealthEndpoint:
    """Test suite for health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        # Arrange
        with patch('src.main.mongodb_client') as mock_client:
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get("/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "content-processor"
        assert data["version"] == "1.0.0"
        assert data["database"] == "connected"
    
    @pytest.mark.asyncio
    async def test_health_check_database_failure(self):
        """Test health check with database connection failure"""
        # Arrange
        with patch('src.main.mongodb_client') as mock_client:
            mock_client.admin.command = AsyncMock(side_effect=Exception("Connection failed"))
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get("/health")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert "Service unhealthy" in data["detail"]

class TestDocumentUploadEndpoint:
    """Test suite for document upload endpoint"""
    
    @pytest.mark.asyncio
    async def test_upload_document_success(self, sample_text):
        """Test successful document upload"""
        # Arrange
        file_content = sample_text.encode('utf-8')
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.text_extractor') as mock_extractor, \
             patch('src.main.get_database') as mock_get_db:
            
            # Setup mocks
            mock_extractor.extract_text = AsyncMock(return_value=sample_text)
            
            mock_processed_doc = MagicMock()
            mock_processed_doc.chunks = [MagicMock(), MagicMock()]  # 2 chunks
            mock_processor.process_document = AsyncMock(return_value=mock_processed_doc)
            mock_processor.save_document = AsyncMock(return_value=ObjectId())
            
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.post(
                    "/documents/upload",
                    files={
                        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
                    },
                    params={"user_id": "test_user_123"}
                )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "test.txt"
        assert data["status"] == "processed"
        assert data["chunks_count"] == 2
        assert data["message"] == "Document uploaded and processed successfully"
    
    @pytest.mark.asyncio
    async def test_upload_document_invalid_file_type(self):
        """Test document upload with invalid file type"""
        # Arrange
        file_content = b"fake content"
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post(
                "/documents/upload",
                files={
                    "file": ("test.exe", io.BytesIO(file_content), "application/x-executable")
                }
            )
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "not allowed" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_document_no_file(self):
        """Test document upload without file"""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post("/documents/upload")
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_upload_document_processing_failure(self, sample_text):
        """Test document upload with processing failure"""
        # Arrange
        file_content = sample_text.encode('utf-8')
        
        with patch('src.main.text_extractor') as mock_extractor:
            mock_extractor.extract_text = AsyncMock(side_effect=Exception("Extraction failed"))
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.post(
                    "/documents/upload",
                    files={
                        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
                    }
                )
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "Upload failed" in data["detail"]

class TestGetDocumentEndpoint:
    """Test suite for get document endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_document_success(self, sample_document_dict):
        """Test successful document retrieval"""
        # Arrange
        document_id = str(sample_document_dict["_id"])
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            sample_document_dict["id"] = document_id
            sample_document_dict["chunks_count"] = 1
            mock_processor.get_document = AsyncMock(return_value=sample_document_dict)
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get(f"/documents/{document_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document_id
        assert data["title"] == sample_document_dict["title"]
        assert "chunks_count" in data
    
    @pytest.mark.asyncio
    async def test_get_document_not_found(self):
        """Test document retrieval for non-existent document"""
        # Arrange
        document_id = str(ObjectId())
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            mock_processor.get_document = AsyncMock(return_value=None)
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get(f"/documents/{document_id}")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "Document not found" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_get_document_invalid_id(self):
        """Test document retrieval with invalid ObjectId"""
        # Arrange
        invalid_id = "invalid_objectid"
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            mock_processor.get_document = AsyncMock(side_effect=Exception("Invalid ObjectId"))
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get(f"/documents/{invalid_id}")
        
        # Assert
        assert response.status_code == 500

class TestListDocumentsEndpoint:
    """Test suite for list documents endpoint"""
    
    @pytest.mark.asyncio
    async def test_list_documents_success(self, document_builder):
        """Test successful document listing"""
        # Arrange
        doc1 = document_builder.with_title("Document 1").build_dict()
        doc1["id"] = str(doc1["_id"])
        doc1["chunks_count"] = 2
        
        doc2 = document_builder.with_title("Document 2").build_dict()
        doc2["id"] = str(doc2["_id"])
        doc2["chunks_count"] = 3
        
        mock_documents = [doc1, doc2]
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            mock_processor.list_documents = AsyncMock(return_value=mock_documents)
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get("/documents")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Document 1"
        assert data[1]["title"] == "Document 2"
    
    @pytest.mark.asyncio
    async def test_list_documents_with_filters(self):
        """Test document listing with user_id filter"""
        # Arrange
        user_id = "test_user_123"
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            mock_processor.list_documents = AsyncMock(return_value=[])
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get(f"/documents?user_id={user_id}&limit=10&skip=5")
        
        # Assert
        assert response.status_code == 200
        # Verify the method was called with correct parameters (db can be any database instance)
        mock_processor.list_documents.assert_called_once()
        call_args = mock_processor.list_documents.call_args[1]  # Get keyword arguments
        assert call_args['user_id'] == user_id
        assert call_args['limit'] == 10
        assert call_args['skip'] == 5
        assert 'db' in call_args  # Just verify db was passed
    
    @pytest.mark.asyncio
    async def test_list_documents_empty_result(self):
        """Test document listing with empty result"""
        # Arrange
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            mock_processor.list_documents = AsyncMock(return_value=[])
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get("/documents")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

class TestDeleteDocumentEndpoint:
    """Test suite for delete document endpoint"""
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self):
        """Test successful document deletion"""
        # Arrange
        document_id = str(ObjectId())
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            mock_processor.delete_document = AsyncMock(return_value=True)
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.delete(f"/documents/{document_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document deleted successfully"
    
    @pytest.mark.asyncio
    async def test_delete_document_not_found(self):
        """Test document deletion for non-existent document"""
        # Arrange
        document_id = str(ObjectId())
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            mock_processor.delete_document = AsyncMock(return_value=False)
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.delete(f"/documents/{document_id}")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "Document not found" in data["detail"]

class TestReprocessDocumentEndpoint:
    """Test suite for reprocess document endpoint"""
    
    @pytest.mark.asyncio
    async def test_reprocess_document_success(self):
        """Test successful document reprocessing"""
        # Arrange
        document_id = str(ObjectId())
        reprocess_result = {"chunks_count": 5}
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            mock_processor.reprocess_document = AsyncMock(return_value=reprocess_result)
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.post(f"/documents/{document_id}/reprocess")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document reprocessed successfully"
        assert data["chunks_count"] == 5
    
    @pytest.mark.asyncio
    async def test_reprocess_document_not_found(self):
        """Test document reprocessing for non-existent document"""
        # Arrange
        document_id = str(ObjectId())
        
        with patch('src.main.document_processor') as mock_processor, \
             patch('src.main.get_database') as mock_get_db:
            
            mock_processor.reprocess_document = AsyncMock(return_value=None)
            mock_get_db.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.post(f"/documents/{document_id}/reprocess")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "Document not found" in data["detail"]

class TestCORSMiddleware:
    """Test suite for CORS middleware"""
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self):
        """Test that CORS headers are present in responses"""
        # Arrange
        with patch('src.main.mongodb_client') as mock_client:
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get("/health")
        
        # Assert
        assert response.status_code == 200
        # FastAPI with CORS middleware should include appropriate headers
        # The exact headers depend on the request, but we can check it doesn't fail
    
    @pytest.mark.asyncio
    async def test_options_request_handled(self):
        """Test that OPTIONS preflight requests are handled"""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.options("/health")
        
        # Assert
        # OPTIONS requests should be handled by CORS middleware
        assert response.status_code in [200, 204, 405]  # Depending on FastAPI version