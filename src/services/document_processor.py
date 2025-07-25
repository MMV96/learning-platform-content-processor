# learning-platform-content-processor/src/services/document_processor.py

import re
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
import logging

from ..models.document import Document, DocumentChunk, DocumentMetadata
from ..config import settings
from ..database import Collections

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Service for processing and managing documents"""
    
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.min_chunk_size = settings.MIN_CHUNK_SIZE
    
    async def process_document(
        self, 
        text: str, 
        filename: str, 
        file_type: str, 
        user_id: Optional[str] = None
    ) -> Document:
        """Process a document: clean text, extract metadata, create chunks"""
        
        logger.info(f"Processing document: {filename}")
        
        try:
            # Clean and normalize text
            cleaned_text = self._clean_text(text)
            
            # Extract title from filename or text
            title = self._extract_title(filename, cleaned_text)
            
            # Create metadata
            metadata = self._create_metadata(
                cleaned_text, 
                filename, 
                file_type, 
                len(text)
            )
            
            # Create chunks
            chunks = self._create_chunks(cleaned_text)
            
            # Generate summary (placeholder for now)
            summary = self._generate_summary(cleaned_text)
            
            # Create document object
            document = Document(
                title=title,
                content=cleaned_text,
                summary=summary,
                chunks=chunks,
                user_id=user_id,
                metadata=metadata,
                processed_at=datetime.utcnow(),
                status="completed"
            )
            
            logger.info(f"Document processed successfully: {len(chunks)} chunks created")
            return document
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise Exception(f"Failed to process document: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\']+', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\n+', '\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _extract_title(self, filename: str, text: str) -> str:
        """Extract title from filename or document content"""
        
        # Try to extract from filename first
        title = filename.rsplit('.', 1)[0]  # Remove extension
        title = re.sub(r'[_\-]+', ' ', title)  # Replace underscores/dashes with spaces
        title = title.title()  # Capitalize
        
        # If title is too short or generic, try to extract from text
        if len(title) < 3 or title.lower() in ['document', 'file', 'text']:
            # Look for title patterns in first 500 characters
            text_start = text[:500]
            
            # Look for title-like patterns (capitalized lines)
            lines = text_start.split('\n')
            for line in lines[:5]:  # Check first 5 lines
                line = line.strip()
                if len(line) > 5 and len(line) < 100 and line[0].isupper():
                    title = line
                    break
        
        return title[:100]  # Limit title length
    
    def _create_metadata(
        self, 
        text: str, 
        filename: str, 
        file_type: str, 
        file_size: int
    ) -> DocumentMetadata:
        """Create document metadata"""
        
        word_count = len(text.split())
        character_count = len(text)
        
        # Estimate reading time (average 200 words per minute)
        estimated_reading_time = max(1, word_count // 200)
        
        # Detect language (basic heuristic)
        language = self._detect_language(text)
        
        return DocumentMetadata(
            file_type=file_type,
            file_size=file_size,
            word_count=word_count,
            character_count=character_count,
            estimated_reading_time=estimated_reading_time,
            language=language
        )
    
    def _detect_language(self, text: str) -> str:
        """Basic language detection"""
        # Simple heuristic - count common English vs Italian words
        english_words = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with']
        italian_words = ['il', 'di', 'che', 'e', 'la', 'per', 'in', 'un', 'è', 'con']
        
        text_lower = text.lower()
        
        en_count = sum(1 for word in english_words if f' {word} ' in text_lower)
        it_count = sum(1 for word in italian_words if f' {word} ' in text_lower)
        
        if en_count > it_count:
            return 'en'
        elif it_count > en_count:
            return 'it'
        else:
            return 'unknown'
    
    def _create_chunks(self, text: str) -> List[DocumentChunk]:
        """Split text into chunks for AI processing"""
        
        chunks = []
        text_length = len(text)
        
        if text_length <= self.chunk_size:
            # Document is small enough to be a single chunk
            chunk = DocumentChunk(
                index=0,
                content=text,
                start_position=0,
                end_position=text_length,
                word_count=len(text.split()),
                character_count=text_length
            )
            chunks.append(chunk)
        else:
            # Split into multiple chunks with overlap
            start = 0
            chunk_index = 0
            
            while start < text_length:
                # Calculate end position
                end = min(start + self.chunk_size, text_length)
                
                # Try to end at a sentence boundary
                if end < text_length:
                    # Look for sentence endings within last 100 chars
                    search_start = max(end - 100, start)
                    chunk_text = text[search_start:end]
                    
                    # Find last sentence ending
                    sentence_endings = ['.', '!', '?', '\n']
                    last_sentence_end = -1
                    
                    for ending in sentence_endings:
                        pos = chunk_text.rfind(ending)
                        if pos > last_sentence_end:
                            last_sentence_end = pos
                    
                    if last_sentence_end > 0:
                        end = search_start + last_sentence_end + 1
                
                # Extract chunk content
                chunk_content = text[start:end].strip()
                
                # Skip if chunk is too small
                if len(chunk_content) >= self.min_chunk_size:
                    chunk = DocumentChunk(
                        index=chunk_index,
                        content=chunk_content,
                        start_position=start,
                        end_position=end,
                        word_count=len(chunk_content.split()),
                        character_count=len(chunk_content)
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Move to next chunk with overlap
                start = max(start + 1, end - self.chunk_overlap)
        
        logger.info(f"Created {len(chunks)} chunks from text of {text_length} characters")
        return chunks
    
    def _generate_summary(self, text: str) -> str:
        """Generate a basic summary (placeholder)"""
        # For now, just take first few sentences
        sentences = text.split('. ')
        summary_sentences = sentences[:3]  # First 3 sentences
        summary = '. '.join(summary_sentences)
        
        if len(summary) > 500:
            summary = summary[:500] + "..."
        
        return summary
    
    async def save_document(self, document: Document, db) -> ObjectId:
        """Save document to database"""
        
        try:
            # Convert to dict for MongoDB
            doc_dict = document.model_dump(by_alias=True, exclude={"id"})
            
            # Insert into database
            result = await db[Collections.BOOKS].insert_one(doc_dict)
            
            logger.info(f"Document saved to database with ID: {result.inserted_id}")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            raise
    
    async def get_document(self, document_id: str, db) -> Optional[Dict]:
        """Get document by ID"""
        
        try:
            doc = await db[Collections.BOOKS].find_one({"_id": ObjectId(document_id)})
            
            if doc:
                doc["id"] = str(doc["_id"])
                doc["chunks_count"] = len(doc.get("chunks", []))
            
            return doc
            
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    async def list_documents(
        self, 
        user_id: Optional[str] = None,
        limit: int = 20,
        skip: int = 0,
        db=None
    ) -> List[Dict]:
        """List documents with pagination"""
        
        try:
            # Build query
            query = {}
            if user_id:
                query["user_id"] = user_id
            
            # Get documents
            cursor = db[Collections.BOOKS].find(query).sort("uploaded_at", -1).skip(skip).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            # Add computed fields
            for doc in documents:
                doc["id"] = str(doc["_id"])
                doc["chunks_count"] = len(doc.get("chunks", []))
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    async def delete_document(self, document_id: str, db) -> bool:
        """Delete document by ID"""
        
        try:
            result = await db[Collections.BOOKS].delete_one({"_id": ObjectId(document_id)})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    async def reprocess_document(self, document_id: str, db) -> Optional[Dict]:
        """Reprocess existing document"""
        
        try:
            # Get existing document
            doc = await self.get_document(document_id, db)
            if not doc:
                return None
            
            # Reprocess content
            processed = await self.process_document(
                text=doc["content"],
                filename=doc["title"],
                file_type=doc["metadata"]["file_type"],
                user_id=doc.get("user_id")
            )
            
            # Update document
            update_data = {
                "chunks": [chunk.model_dump() for chunk in processed.chunks],
                "summary": processed.summary,
                "processed_at": datetime.utcnow(),
                "status": "completed"
            }
            
            await db[Collections.BOOKS].update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data}
            )
            
            return {"chunks_count": len(processed.chunks)}
            
        except Exception as e:
            logger.error(f"Failed to reprocess document {document_id}: {e}")
            return None