# learning-platform-content-processor/src/main.py

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import List, Optional
import logging

from .config import settings
from .database import mongodb_client, get_database
from .services.document_processor import DocumentProcessor
from .services.text_extractor import TextExtractor
from .models.document import DocumentResponse, DocumentUploadResponse
from .utils.file_validator import validate_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting Content Processor Service...")
    
    # Test database connection
    try:
        await mongodb_client.admin.command('ping')
        logger.info("✅ MongoDB connection successful")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Content Processor Service...")
    mongodb_client.close()

# Initialize FastAPI app
app = FastAPI(
    title="Learning Platform - Content Processor",
    description="Microservice for document upload, parsing and content processing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
document_processor = DocumentProcessor()
text_extractor = TextExtractor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        await mongodb_client.admin.command('ping')
        
        return {
            "status": "healthy",
            "service": "content-processor",
            "version": "1.0.0",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = None,  # TODO: Get from JWT token
    db=Depends(get_database)
):
    """Upload and process a document (PDF, EPUB, TXT)"""
    
    try:
        # Validate file
        validate_file(file)
        
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        extracted_text = await text_extractor.extract_text(
            content, 
            file.filename, 
            file.content_type
        )
        
        # Process document (chunking, metadata extraction)
        processed_doc = await document_processor.process_document(
            text=extracted_text,
            filename=file.filename,
            file_type=file.content_type,
            user_id=user_id
        )
        
        # Save to database
        doc_id = await document_processor.save_document(processed_doc, db)
        
        logger.info(f"Document uploaded successfully: {doc_id}")
        
        return DocumentUploadResponse(
            document_id=str(doc_id),
            filename=file.filename,
            status="processed",
            chunks_count=len(processed_doc.chunks),
            message="Document uploaded and processed successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like validation errors) as-is
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db=Depends(get_database)):
    """Get document by ID"""
    
    try:
        document = await document_processor.get_document(document_id, db)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentResponse(**document)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) as-is
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    user_id: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    db=Depends(get_database)
):
    """List documents with pagination"""
    
    try:
        documents = await document_processor.list_documents(
            user_id=user_id,
            limit=limit,
            skip=skip,
            db=db
        )
        
        return [DocumentResponse(**doc) for doc in documents]
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str, db=Depends(get_database)):
    """Delete document by ID"""
    
    try:
        success = await document_processor.delete_document(document_id, db)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) as-is
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/{document_id}/reprocess")
async def reprocess_document(document_id: str, db=Depends(get_database)):
    """Reprocess document (re-chunk, update metadata)"""
    
    try:
        result = await document_processor.reprocess_document(document_id, db)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "message": "Document reprocessed successfully",
            "chunks_count": result.get("chunks_count", 0)
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) as-is
        raise
    except Exception as e:
        logger.error(f"Failed to reprocess document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )