import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from src.utils.file_validator import (
    validate_file,
    validate_file_content,
    sanitize_filename,
    get_file_info,
    FileValidationError,
    _validate_file_size,
    _validate_file_extension,
    _validate_content_type,
    _validate_magic_bytes
)

class TestFileValidator:
    """Test suite for file validation utilities"""
    
    def test_validate_file_success(self, mock_upload_file, mock_settings):
        """Test successful file validation"""
        # Arrange
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert - should not raise
            validate_file(mock_upload_file)
    
    def test_validate_file_no_file_raises_error(self, mock_settings):
        """Test that no file raises validation error"""
        # Arrange
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                validate_file(None)
            assert exc_info.value.status_code == 400
            assert "No file provided" in str(exc_info.value.detail)
    
    def test_validate_file_no_filename_raises_error(self, mock_settings):
        """Test that missing filename raises validation error"""
        # Arrange
        file = MagicMock()
        file.filename = None
        
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                validate_file(file)
            assert "Filename is required" in str(exc_info.value.detail)
    
    @pytest.mark.parametrize("extension,should_pass", [
        (".pdf", True),
        (".txt", True),
        (".epub", True),
        (".docx", True),
        (".exe", False),
        (".jpg", False),
        ("", False),
    ])
    def test_validate_file_extension(self, extension, should_pass, mock_settings):
        """Test file extension validation"""
        # Arrange
        filename = f"test{extension}"
        
        with patch('src.utils.file_validator.settings', mock_settings):
            if should_pass:
                # Act & Assert - should not raise
                _validate_file_extension(filename)
            else:
                # Act & Assert
                with pytest.raises(FileValidationError):
                    _validate_file_extension(filename)
    
    @pytest.mark.parametrize("content_type,should_pass", [
        ("application/pdf", True),
        ("text/plain", True),
        ("application/epub+zip", True),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", True),
        ("image/jpeg", False),
        ("application/executable", False),
        (None, False),
    ])
    def test_validate_content_type(self, content_type, should_pass, mock_settings):
        """Test content type validation"""
        # Arrange
        with patch('src.utils.file_validator.settings', mock_settings):
            if should_pass:
                # Act & Assert - should not raise
                _validate_content_type(content_type)
            else:
                # Act & Assert
                with pytest.raises(FileValidationError):
                    _validate_content_type(content_type)
    
    def test_validate_file_size_within_limit(self, mock_settings):
        """Test file size validation within limits"""
        # Arrange
        file = MagicMock()
        file.size = 1024 * 1024  # 1MB
        
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert - should not raise
            _validate_file_size(file)
    
    def test_validate_file_size_exceeds_limit(self, mock_settings):
        """Test file size validation exceeding limits"""
        # Arrange
        file = MagicMock()
        file.size = 100 * 1024 * 1024  # 100MB (exceeds 50MB limit)
        
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert
            with pytest.raises(FileValidationError) as exc_info:
                _validate_file_size(file)
            assert "exceeds maximum allowed size" in str(exc_info.value)
    
    def test_validate_file_size_no_size_attribute(self, mock_settings):
        """Test file size validation when size attribute is missing"""
        # Arrange
        file = MagicMock()
        del file.size  # Remove size attribute
        
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert - should not raise (skips validation)
            _validate_file_size(file)
    
    def test_validate_file_content_success(self, sample_text, mock_settings):
        """Test successful file content validation"""
        # Arrange
        content = sample_text.encode('utf-8')
        filename = "test.txt"
        
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert - should not raise
            validate_file_content(content, filename)
    
    def test_validate_file_content_empty_file_raises_error(self, mock_settings):
        """Test that empty file content raises validation error"""
        # Arrange
        content = b""
        filename = "empty.txt"
        
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                validate_file_content(content, filename)
            assert "File is empty" in str(exc_info.value.detail)
    
    def test_validate_file_content_size_exceeds_limit(self, mock_settings):
        """Test file content size validation exceeding limits"""
        # Arrange
        content = b"A" * (100 * 1024 * 1024)  # 100MB
        filename = "large.txt"
        
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                validate_file_content(content, filename)
            assert "exceeds maximum allowed size" in str(exc_info.value.detail)
    
    @patch('src.utils.file_validator.HAS_MAGIC', True)
    @patch('src.utils.file_validator.magic')
    def test_validate_file_content_with_magic_detection(self, mock_magic, mock_settings, sample_text):
        """Test file content validation with magic type detection"""
        # Arrange
        content = sample_text.encode('utf-8')
        filename = "test.txt"
        mock_magic.from_buffer.return_value = "text/plain"
        
        with patch('src.utils.file_validator.settings', mock_settings):
            # Act & Assert - should not raise
            validate_file_content(content, filename)
            mock_magic.from_buffer.assert_called_once_with(content, mime=True)
    
    def test_validate_file_content_without_magic(self, mock_settings, sample_text):
        """Test file content validation without magic library"""
        # Arrange
        content = sample_text.encode('utf-8')
        filename = "test.txt"
        
        with patch('src.utils.file_validator.HAS_MAGIC', False):
            with patch('src.utils.file_validator.settings', mock_settings):
                # Act & Assert - should not raise
                validate_file_content(content, filename)
    
    @pytest.mark.parametrize("file_content,filename,should_pass", [
        (b"%PDF-1.4", "test.pdf", True),
        (b"PK", "test.epub", True),
        (b"PK", "test.docx", True),
        (b"hello world", "test.pdf", False),
        (b"not zip", "test.epub", False),
    ])
    def test_validate_magic_bytes(self, file_content, filename, should_pass):
        """Test magic bytes validation for different file types"""
        if should_pass:
            # Act & Assert - should not raise
            _validate_magic_bytes(file_content, filename)
        else:
            # Act & Assert
            with pytest.raises(FileValidationError):
                _validate_magic_bytes(file_content, filename)
    
    @pytest.mark.parametrize("malicious_content", [
        b'\x4D\x5A',  # Windows executable
        b'\x7F\x45\x4C\x46',  # Linux executable
        b'\xCA\xFE\xBA\xBE',  # Java class file
        b'\xFE\xED\xFA\xCE',  # Mach-O binary
    ])
    def test_validate_magic_bytes_rejects_executables(self, malicious_content):
        """Test that magic bytes validation rejects executable files"""
        # Act & Assert
        with pytest.raises(FileValidationError) as exc_info:
            _validate_magic_bytes(malicious_content, "malicious.exe")
        assert "executable" in str(exc_info.value)
    
    @pytest.mark.parametrize("input_filename,expected", [
        ("normal_file.txt", "normal_file.txt"),
        ("file with spaces.pdf", "file with spaces.pdf"),
        ("file<>:\"/\\|?*.txt", "file.txt"),  # Special chars removed
        ("file\x00\x1f\x7f.txt", "file.txt"),  # Control chars removed
        ("a" * 300 + ".txt", "a" * 251 + ".txt"),  # Length limited
        ("", "document.txt"),  # Empty filename
        ("   ", "document.txt"),  # Whitespace only
    ])
    def test_sanitize_filename(self, input_filename, expected):
        """Test filename sanitization"""
        # Act
        result = sanitize_filename(input_filename)
        
        # Assert
        assert result == expected
        assert len(result) <= 255
    
    def test_get_file_info_returns_complete_info(self, sample_text):
        """Test that get_file_info returns complete file information"""
        # Arrange
        content = sample_text.encode('utf-8')
        filename = "test.txt"
        
        # Act
        info = get_file_info(content, filename)
        
        # Assert
        assert info["filename"] == filename
        assert info["size_bytes"] == len(content)
        assert info["size_mb"] == round(len(content) / (1024 * 1024), 2)
        assert info["extension"] == ".txt"
        assert info["is_empty"] is False
        assert "first_bytes" in info
        assert isinstance(info["first_bytes"], str)
    
    def test_get_file_info_empty_file(self):
        """Test file info for empty file"""
        # Arrange
        content = b""
        filename = "empty.txt"
        
        # Act
        info = get_file_info(content, filename)
        
        # Assert
        assert info["is_empty"] is True
        assert info["size_bytes"] == 0
        assert info["size_mb"] == 0.0
        assert info["first_bytes"] == ""
    
    def test_get_file_info_short_file(self):
        """Test file info for file shorter than 20 bytes"""
        # Arrange
        content = b"short"
        filename = "short.txt"
        
        # Act
        info = get_file_info(content, filename)
        
        # Assert
        assert info["first_bytes"] == content.hex()
        assert len(info["first_bytes"]) == len(content) * 2  # hex encoding
    
    def test_file_validation_error_inheritance(self):
        """Test that FileValidationError is properly inherited from Exception"""
        # Arrange & Act
        error = FileValidationError("Test error")
        
        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "Test error"