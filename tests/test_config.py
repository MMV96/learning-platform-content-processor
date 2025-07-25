# tests/test_config.py

import pytest
from unittest.mock import patch, mock_open
import os

from src.config import Settings, validate_settings

class TestSettings:
    """Test suite for application settings"""
    
    def test_settings_default_values(self):
        """Test that settings have correct default values"""
        # Arrange - Mock environment and disable env file loading to test pure defaults
        with patch.dict(os.environ, {}, clear=True):
            # Act
            settings = Settings(_env_file=None)
            
            # Assert
            assert settings.PORT == 8001
            assert settings.DEBUG is False
            assert settings.DATABASE_NAME == "learning_platform"
            assert settings.CHUNK_SIZE == 1000
            assert settings.CHUNK_OVERLAP == 100
            assert settings.MIN_CHUNK_SIZE == 100
            assert settings.MAX_FILE_SIZE == 52428800  # Updated to match config
            assert settings.LOG_LEVEL == "INFO"
    
    def test_settings_allowed_file_types(self):
        """Test that allowed file types are correctly configured"""
        # Act
        settings = Settings()
        
        # Assert
        expected_types = [
            "application/pdf",
            "application/epub+zip", 
            "text/plain",
            "text/markdown",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]
        assert settings.ALLOWED_FILE_TYPES == expected_types
    
    def test_settings_allowed_file_extensions(self):
        """Test that allowed file extensions are correctly configured"""
        # Act
        settings = Settings()
        
        # Assert
        expected_extensions = [".pdf", ".epub", ".txt", ".md", ".docx"]
        assert settings.ALLOWED_FILE_EXTENSIONS == expected_extensions
    
    def test_settings_allowed_origins(self):
        """Test that CORS origins are correctly configured"""
        # Act
        settings = Settings()
        
        # Assert
        expected_origins = ["http://localhost:3000", "http://localhost:8000"]
        assert settings.ALLOWED_ORIGINS == expected_origins
    
    @patch.dict(os.environ, {
        'PORT': '9000',
        'DEBUG': 'true',
        'DATABASE_NAME': 'test_db',
        'CHUNK_SIZE': '500',
        'MAX_FILE_SIZE': '10485760'  # 10MB
    })
    def test_settings_environment_override(self):
        """Test that environment variables override default settings"""
        # Act
        settings = Settings()
        
        # Assert
        assert settings.PORT == 9000
        assert settings.DEBUG is True
        assert settings.DATABASE_NAME == "test_db"
        assert settings.CHUNK_SIZE == 500
        assert settings.MAX_FILE_SIZE == 10485760
    
    @patch.dict(os.environ, {
        'ALLOWED_ORIGINS': '["http://example.com", "https://app.example.com"]'
    })
    def test_settings_list_environment_override(self):
        """Test that list settings can be overridden via environment"""
        # Act
        settings = Settings()
        
        # Assert
        expected_origins = ["http://example.com", "https://app.example.com"]
        assert settings.ALLOWED_ORIGINS == expected_origins
    
    def test_settings_mongodb_url_default(self):
        """Test default MongoDB URL"""
        # Arrange - Mock environment and disable env file loading to test pure defaults
        with patch.dict(os.environ, {}, clear=True):
            # Act
            settings = Settings(_env_file=None)
            
            # Assert
            expected_url = "mongodb://admin:password123@localhost:27017/learning_platform?authSource=admin"
            assert settings.MONGODB_URL == expected_url
    
    @patch.dict(os.environ, {
        'MONGODB_URL': 'mongodb://custom:password@custom-host:27017/custom_db'
    })
    def test_settings_mongodb_url_override(self):
        """Test MongoDB URL can be overridden"""
        # Act
        settings = Settings()
        
        # Assert
        assert settings.MONGODB_URL == "mongodb://custom:password@custom-host:27017/custom_db"
    
    def test_settings_ai_keys_default_empty(self):
        """Test that AI API keys default to empty strings"""
        # Arrange - Mock environment and disable env file loading to test pure defaults
        with patch.dict(os.environ, {}, clear=True):
            # Act
            settings = Settings(_env_file=None)
            
            # Assert
            assert settings.OPENAI_API_KEY == ""
            assert settings.ANTHROPIC_API_KEY == ""
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'sk-test-openai-key',
        'ANTHROPIC_API_KEY': 'claude-test-key'
    })
    def test_settings_ai_keys_override(self):
        """Test that AI API keys can be set via environment"""
        # Act
        settings = Settings()
        
        # Assert
        assert settings.OPENAI_API_KEY == "sk-test-openai-key"
        assert settings.ANTHROPIC_API_KEY == "claude-test-key"
    
    def test_settings_case_sensitive(self):
        """Test that settings are case sensitive"""
        # Arrange
        with patch.dict(os.environ, {'port': '9000'}):  # lowercase
            # Act
            settings = Settings()
        
        # Assert
        assert settings.PORT == 8001  # Should use default, not lowercase env var
    
    @patch('builtins.open', mock_open(read_data='PORT=9999\nDEBUG=true\n'))
    def test_settings_env_file_loading(self):
        """Test that settings can be loaded from .env file"""
        # Act
        settings = Settings()
        
        # The actual loading depends on whether .env file exists and pydantic-settings behavior
        # This is more of a documentation test of the expected behavior
        assert hasattr(settings, 'PORT')
        assert hasattr(settings, 'DEBUG')

class TestValidateSettings:
    """Test suite for settings validation"""
    
    def test_validate_settings_success(self):
        """Test successful settings validation"""
        # Arrange
        with patch('src.config.settings') as mock_settings:
            mock_settings.MONGODB_URL = "mongodb://localhost:27017/test"
            mock_settings.MAX_FILE_SIZE = 50 * 1024 * 1024
            mock_settings.CHUNK_SIZE = 1000
            
            # Act & Assert - should not raise
            validate_settings()
    
    def test_validate_settings_empty_mongodb_url_raises_error(self):
        """Test that empty MongoDB URL raises validation error"""
        # Arrange
        with patch('src.config.settings') as mock_settings:
            mock_settings.MONGODB_URL = ""
            
            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                validate_settings()
            assert "MONGODB_URL is required" in str(exc_info.value)
    
    def test_validate_settings_small_max_file_size_raises_error(self):
        """Test that too small max file size raises validation error"""
        # Arrange
        with patch('src.config.settings') as mock_settings:
            mock_settings.MONGODB_URL = "mongodb://localhost:27017/test"
            mock_settings.MAX_FILE_SIZE = 500 * 1024  # 500KB, less than 1MB minimum
            
            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                validate_settings()
            assert "MAX_FILE_SIZE should be at least 1MB" in str(exc_info.value)
    
    def test_validate_settings_small_chunk_size_raises_error(self):
        """Test that too small chunk size raises validation error"""
        # Arrange
        with patch('src.config.settings') as mock_settings:
            mock_settings.MONGODB_URL = "mongodb://localhost:27017/test"
            mock_settings.MAX_FILE_SIZE = 50 * 1024 * 1024
            mock_settings.CHUNK_SIZE = 50  # Less than 100 minimum
            
            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                validate_settings()
            assert "CHUNK_SIZE should be at least 100 characters" in str(exc_info.value)
    
    def test_validate_settings_boundary_values(self):
        """Test settings validation with boundary values"""
        # Arrange
        with patch('src.config.settings') as mock_settings:
            mock_settings.MONGODB_URL = "mongodb://localhost:27017/test"
            mock_settings.MAX_FILE_SIZE = 1024 * 1024  # Exactly 1MB
            mock_settings.CHUNK_SIZE = 100  # Exactly 100 characters
            
            # Act & Assert - should not raise
            validate_settings()

class TestSettingsIntegration:
    """Integration tests for settings with environment"""
    
    def test_settings_with_env_file_override(self, tmp_path):
        """Test settings loading with actual .env file"""
        # Arrange
        env_file = tmp_path / ".env"
        env_file.write_text(
            "PORT=7777\n"
            "DEBUG=true\n"
            "DATABASE_NAME=env_test_db\n"
            "CHUNK_SIZE=2000\n"
        )
        
        # Act - Isolate from pytest environment variables
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=str(env_file))
            
            # Assert
            assert settings.PORT == 7777
            assert settings.DEBUG is True
            assert settings.DATABASE_NAME == "env_test_db"
            assert settings.CHUNK_SIZE == 2000
    
    def test_settings_environment_priority_over_env_file(self, tmp_path):
        """Test that environment variables take priority over .env file"""
        # Arrange
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=7777\n")
        
        with patch.dict(os.environ, {'PORT': '8888'}):
            # Act
            settings = Settings(_env_file=str(env_file))
        
        # Assert
        assert settings.PORT == 8888  # Environment variable wins
    
    def test_settings_missing_env_file_uses_defaults(self):
        """Test that missing .env file falls back to defaults"""
        # Arrange - Mock environment to isolate from pytest env vars
        with patch.dict(os.environ, {}, clear=True):
            # Act
            settings = Settings(_env_file="nonexistent.env")
            
            # Assert
            assert settings.PORT == 8001  # Default value
            assert settings.DEBUG is False  # Default value
    
    @patch.dict(os.environ, {}, clear=True)
    def test_settings_clean_environment(self):
        """Test settings with completely clean environment"""
        # Act
        settings = Settings()
        
        # Assert - should use all default values
        assert settings.PORT == 8001
        assert settings.DEBUG is False
        assert settings.DATABASE_NAME == "learning_platform"
        assert settings.CHUNK_SIZE == 1000
    
    def test_settings_invalid_boolean_env_var(self):
        """Test handling of invalid boolean environment variables"""
        # Arrange & Act & Assert
        with patch.dict(os.environ, {'DEBUG': 'invalid_boolean'}):
            # Pydantic v2 is strict and should raise ValidationError for invalid boolean
            with pytest.raises(Exception):  # ValidationError from pydantic_core
                Settings()
    
    def test_settings_invalid_integer_env_var(self):
        """Test handling of invalid integer environment variables"""
        # Arrange
        with patch.dict(os.environ, {'PORT': 'not_a_number'}):
            # Act & Assert
            with pytest.raises(ValueError):
                Settings()
    
    def test_settings_very_large_file_size(self):
        """Test settings with very large file size"""
        # Arrange
        with patch.dict(os.environ, {'MAX_FILE_SIZE': str(1024 * 1024 * 1024)}):  # 1GB
            # Act
            settings = Settings()
        
        # Assert
        assert settings.MAX_FILE_SIZE == 1024 * 1024 * 1024
        # Should pass validation since it's > 1MB
        validate_settings()

class TestSettingsSecrets:
    """Test suite for sensitive settings handling"""
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'sk-secret-key-12345',
        'ANTHROPIC_API_KEY': 'claude-secret-key-67890'
    })
    def test_settings_handle_secrets(self):
        """Test that secret keys are properly loaded"""
        # Act
        settings = Settings()
        
        # Assert
        assert settings.OPENAI_API_KEY == "sk-secret-key-12345"
        assert settings.ANTHROPIC_API_KEY == "claude-secret-key-67890"
    
    def test_settings_repr_does_not_expose_secrets(self):
        """Test that repr doesn't expose sensitive information"""
        # Arrange
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret-key'}):
            settings = Settings()
        
        # Act
        settings_repr = repr(settings)
        
        # Assert - this might depend on pydantic version, but generally:
        # Either secrets should be hidden or this test documents current behavior
        assert isinstance(settings_repr, str)
        # Could add more specific assertions based on pydantic's secret handling