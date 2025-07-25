import os
import logging
from fastapi import UploadFile, HTTPException

# Import con try/except per gestire libmagic opzionale
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    magic = None

from ..config import settings

logger = logging.getLogger(__name__)

class FileValidationError(Exception):
    """Custom exception for file validation errors"""
    pass

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file against security and format requirements"""
    
    try:
        # Check if file exists
        if not file:
            raise FileValidationError("No file provided")
        
        # Check filename
        if not file.filename:
            raise FileValidationError("Filename is required")
        
        # Validate file size
        _validate_file_size(file)
        
        # Validate file extension
        _validate_file_extension(file.filename)
        
        # Validate content type
        _validate_content_type(file.content_type)
        
        logger.info(f"File validation passed for: {file.filename}")
        
    except FileValidationError as e:
        logger.warning(f"File validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during file validation: {e}")
        raise HTTPException(status_code=500, detail="File validation failed")

def _validate_file_size(file: UploadFile) -> None:
    """Validate file size"""
    
    # Get file size (this might require reading the file)
    if hasattr(file, 'size') and file.size:
        file_size = file.size
    else:
        # If size is not available, we'll check after reading
        # For now, skip size validation during upload
        return
    
    if file_size > settings.MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        max_size_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
        raise FileValidationError(
            f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb:.1f}MB)"
        )

def _validate_file_extension(filename: str) -> None:
    """Validate file extension"""
    
    file_ext = os.path.splitext(filename)[1].lower()
    
    if not file_ext:
        raise FileValidationError("File must have an extension")
    
    if file_ext not in settings.ALLOWED_FILE_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_FILE_EXTENSIONS)
        raise FileValidationError(
            f"File extension '{file_ext}' not allowed. Allowed extensions: {allowed}"
        )

def _validate_content_type(content_type: str) -> None:
    """Validate MIME content type"""
    
    if not content_type:
        raise FileValidationError("Content type is required")
    
    if content_type not in settings.ALLOWED_FILE_TYPES:
        allowed = ", ".join(settings.ALLOWED_FILE_TYPES)
        raise FileValidationError(
            f"Content type '{content_type}' not allowed. Allowed types: {allowed}"
        )

def validate_file_content(file_content: bytes, filename: str) -> None:
    """Validate file content after reading"""
    
    try:
        # Check file size after reading
        if len(file_content) > settings.MAX_FILE_SIZE:
            size_mb = len(file_content) / (1024 * 1024)
            max_size_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
            raise FileValidationError(
                f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb:.1f}MB)"
            )
        
        # Check if file is not empty
        if len(file_content) == 0:
            raise FileValidationError("File is empty")
        
        # Validate file signature/magic bytes (if libmagic is available)
        if HAS_MAGIC:
            try:
                detected_type = magic.from_buffer(file_content, mime=True)
                logger.info(f"Detected MIME type for {filename}: {detected_type}")
                
                # You can add additional validation based on detected type
                _validate_magic_bytes(file_content, filename)
                
            except Exception as e:
                logger.warning(f"Could not detect file type for {filename}: {e}")
                # Continue without magic byte validation if libmagic fails
        else:
            logger.info("libmagic not available, skipping magic byte validation")
        
        logger.info(f"File content validation passed for: {filename}")
        
    except FileValidationError as e:
        logger.warning(f"File content validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during file content validation: {e}")
        raise HTTPException(status_code=500, detail="File content validation failed")

def _validate_magic_bytes(file_content: bytes, filename: str) -> None:
    """Validate file based on magic bytes/signature"""
    
    # Check for common malicious file signatures
    malicious_signatures = [
        b'\x4D\x5A',  # Windows executable (PE)
        b'\x7F\x45\x4C\x46',  # Linux executable (ELF)
        b'\xCA\xFE\xBA\xBE',  # Java class file
        b'\xFE\xED\xFA\xCE',  # Mach-O binary (macOS)
    ]
    
    for signature in malicious_signatures:
        if file_content.startswith(signature):
            raise FileValidationError(f"File appears to be an executable, which is not allowed")
    
    # Validate specific file type signatures
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext == '.pdf':
        if not file_content.startswith(b'%PDF-'):
            raise FileValidationError("File does not appear to be a valid PDF")
    
    elif file_ext == '.epub':
        # EPUB files are ZIP files with specific structure
        if not file_content.startswith(b'PK'):
            raise FileValidationError("File does not appear to be a valid EPUB")
    
    elif file_ext == '.docx':
        # DOCX files are also ZIP files
        if not file_content.startswith(b'PK'):
            raise FileValidationError("File does not appear to be a valid DOCX")

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    
    import re
    
    # Remove path separators and special characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext
    
    # Ensure it's not empty or whitespace-only
    if not sanitized or not sanitized.strip():
        sanitized = "document.txt"
    
    return sanitized

def get_file_info(file_content: bytes, filename: str) -> dict:
    """Get file information for logging/debugging"""
    
    return {
        "filename": filename,
        "size_bytes": len(file_content),
        "size_mb": round(len(file_content) / (1024 * 1024), 2),
        "extension": os.path.splitext(filename)[1].lower(),
        "is_empty": len(file_content) == 0,
        "first_bytes": file_content[:20].hex() if len(file_content) >= 20 else file_content.hex()
    }