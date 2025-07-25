# src/models/document.py

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from bson import ObjectId
import json

class PyObjectId(str):
    """Simple ObjectId type that works with any Pydantic v2 version"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(ObjectId(v))

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class DocumentMetadata(BaseModel):
    """Document metadata model"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    author: Optional[str] = None
    pages: Optional[int] = None
    language: Optional[str] = None
    file_type: str
    file_size: int
    word_count: Optional[int] = None
    character_count: Optional[int] = None
    estimated_reading_time: Optional[int] = None

class DocumentChunk(BaseModel):
    """Document chunk model"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    index: int
    content: str
    start_position: int
    end_position: int
    word_count: int
    character_count: int

class Document(BaseModel):
    """Main document model"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    content: str
    summary: Optional[str] = None
    chunks: List[DocumentChunk] = []
    user_id: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    metadata: DocumentMetadata
    status: str = "processing"

class DocumentResponse(BaseModel):
    """Document response model"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    id: str
    title: str
    summary: Optional[str] = None
    chunks_count: int
    user_id: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    metadata: DocumentMetadata
    status: str

class DocumentUploadResponse(BaseModel):
    """Document upload response model"""
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    document_id: str
    filename: str
    status: str
    chunks_count: int
    message: str

class DocumentListResponse(BaseModel):
    """Document list response model"""
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    documents: List[DocumentResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

class DocumentProcessingRequest(BaseModel):
    """Document processing request model"""
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    text: str
    filename: str
    file_type: str
    user_id: Optional[str] = None
    processing_options: Optional[Dict[str, Any]] = None

class DocumentSearchRequest(BaseModel):
    """Document search request model"""
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    query: str
    user_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20
    skip: int = 0

class DocumentSearchResponse(BaseModel):
    """Document search response model"""
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    documents: List[DocumentResponse]
    total_results: int
    query: str
    took_ms: int