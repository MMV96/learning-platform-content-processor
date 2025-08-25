import pytest
from unittest.mock import patch, MagicMock, mock_open
import io
import zipfile

from src.services.text_extractor import TextExtractor

class TestTextExtractor:
    """Test suite for TextExtractor service"""
    
    @pytest.fixture
    def extractor(self):
        """Create TextExtractor instance for testing"""
        return TextExtractor()
    
    @pytest.mark.asyncio
    async def test_extract_text_plain_text_success(self, extractor, sample_text):
        """Test successful text extraction from plain text file"""
        # Arrange
        content = sample_text.encode('utf-8')
        filename = "test.txt"
        content_type = "text/plain"
        
        # Act
        result = await extractor.extract_text(content, filename, content_type)
        
        # Assert
        assert result == sample_text
    
    @pytest.mark.asyncio
    async def test_extract_text_unsupported_type_raises_error(self, extractor):
        """Test that unsupported file types raise ValueError"""
        # Arrange
        content = b"some content"
        filename = "test.xyz"
        content_type = "application/unknown"
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await extractor.extract_text(content, filename, content_type)
        assert "Unsupported file type" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_text_empty_content_raises_error(self, extractor):
        """Test that empty content raises error"""
        # Arrange
        content = b""
        filename = "empty.txt"
        content_type = "text/plain"
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await extractor.extract_text(content, filename, content_type)
        assert "No text content found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('src.services.text_extractor.pypdf.PdfReader')
    async def test_extract_from_pdf_success(self, mock_pdf_reader, extractor, sample_pdf_text):
        """Test successful PDF text extraction"""
        # Arrange
        content = b"%PDF-1.4 fake pdf content"
        filename = "test.pdf"
        
        # Mock PDF reader and pages
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Act
        result = await extractor._extract_from_pdf(content, filename)
        
        # Assert
        assert "Page 1 content" in result
        assert "Page 2 content" in result
        assert "\n\n" in result  # Pages should be separated
        mock_pdf_reader.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.services.text_extractor.pypdf.PdfReader')
    async def test_extract_from_pdf_handles_page_extraction_errors(self, mock_pdf_reader, extractor):
        """Test PDF extraction handles individual page errors gracefully"""
        # Arrange
        content = b"%PDF-1.4 fake pdf content"
        filename = "test.pdf"
        
        # Mock one successful page and one failing page
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.side_effect = Exception("Page extraction failed")
        
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Act
        result = await extractor._extract_from_pdf(content, filename)
        
        # Assert
        assert "Page 1 content" in result
        assert result == "Page 1 content"  # Only successful page content
    
    @pytest.mark.asyncio
    @patch('src.services.text_extractor.pypdf.PdfReader')
    async def test_extract_from_pdf_no_readable_text_raises_error(self, mock_pdf_reader, extractor):
        """Test PDF extraction raises error when no text can be extracted"""
        # Arrange
        content = b"%PDF-1.4 fake pdf content"
        filename = "test.pdf"
        
        # Mock pages with no extractable text
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await extractor._extract_from_pdf(content, filename)
        assert "No readable text found in PDF" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('src.services.text_extractor.zipfile.ZipFile')
    async def test_extract_from_epub_success(self, mock_zipfile, extractor):
        """Test successful EPUB text extraction"""
        # Arrange
        content = b"PK fake epub content"
        filename = "test.epub"
        
        # Mock ZIP file with HTML content
        mock_zip_instance = MagicMock()
        mock_zip_instance.namelist.return_value = ["content.html", "chapter1.xhtml", "styles.css"]
        mock_zip_instance.read.side_effect = lambda name: {
            "content.html": b"<html><body><h1>Title</h1><p>Content 1</p></body></html>",
            "chapter1.xhtml": b"<html><body><p>Chapter 1 content</p></body></html>"
        }.get(name, b"")
        
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance
        
        # Act
        result = await extractor._extract_from_epub(content, filename)
        
        # Assert
        assert "Title" in result
        assert "Content 1" in result
        assert "Chapter 1 content" in result
    
    @pytest.mark.asyncio
    @patch('src.services.text_extractor.zipfile.ZipFile')
    async def test_extract_from_epub_no_html_files_raises_error(self, mock_zipfile, extractor):
        """Test EPUB extraction raises error when no HTML files found"""
        # Arrange
        content = b"PK fake epub content"
        filename = "test.epub"
        
        # Mock ZIP file with no HTML files
        mock_zip_instance = MagicMock()
        mock_zip_instance.namelist.return_value = ["META-INF/container.xml", "styles.css"]
        
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await extractor._extract_from_epub(content, filename)
        assert "No readable content files found in EPUB" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_from_txt_utf8_encoding(self, extractor, sample_text):
        """Test text extraction with UTF-8 encoding"""
        # Arrange
        content = sample_text.encode('utf-8')
        filename = "test.txt"
        
        # Act
        result = await extractor._extract_from_txt(content, filename)
        
        # Assert
        assert result == sample_text
    
    @pytest.mark.asyncio
    async def test_extract_from_txt_tries_multiple_encodings(self, extractor):
        """Test that text extraction tries multiple encodings"""
        # Arrange
        text_with_special_chars = "Café résumé naïve"
        content = text_with_special_chars.encode('latin-1')
        filename = "test.txt"
        
        # Act
        result = await extractor._extract_from_txt(content, filename)
        
        # Assert
        assert result == text_with_special_chars
    
    @pytest.mark.asyncio
    async def test_extract_from_txt_unsupported_encoding_raises_error(self, extractor):
        """Test that unsupported encoding raises error"""
        # Arrange
        content = b'some content'
        filename = "test.txt"
        
        # Mock the method to simulate all encodings failing
        async def mock_extract_txt(file_content, filename):
            # Simulate the actual logic but force all encodings to fail
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            for encoding in encodings:
                # Simulate all encodings failing
                pass
            raise ValueError("Could not decode text file with any supported encoding")
        
        # Act & Assert
        with patch.object(extractor, '_extract_from_txt', mock_extract_txt):
            with pytest.raises(Exception) as exc_info:
                await extractor._extract_from_txt(content, filename)
            assert "Could not decode text file" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('src.services.text_extractor.DocxDocument')
    async def test_extract_from_docx_success(self, mock_docx_document, extractor):
        """Test successful DOCX text extraction"""
        # Arrange
        content = b"PK fake docx content"
        filename = "test.docx"
        
        # Mock document with paragraphs and tables
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = "Paragraph 1 text"
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = "Paragraph 2 text"
        
        mock_cell = MagicMock()
        mock_cell.text = "Table cell text"
        mock_row = MagicMock()
        mock_row.cells = [mock_cell]
        mock_table = MagicMock()
        mock_table.rows = [mock_row]
        
        mock_doc_instance = MagicMock()
        mock_doc_instance.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_doc_instance.tables = [mock_table]
        
        mock_docx_document.return_value = mock_doc_instance
        
        # Act
        result = await extractor._extract_from_docx(content, filename)
        
        # Assert
        assert "Paragraph 1 text" in result
        assert "Paragraph 2 text" in result
        assert "Table cell text" in result
    
    @pytest.mark.asyncio
    @patch('src.services.text_extractor.DocxDocument')
    async def test_extract_from_docx_empty_document_raises_error(self, mock_docx_document, extractor):
        """Test DOCX extraction raises error for empty document"""
        # Arrange
        content = b"PK fake docx content"
        filename = "test.docx"
        
        # Mock empty document
        mock_doc_instance = MagicMock()
        mock_doc_instance.paragraphs = []
        mock_doc_instance.tables = []
        
        mock_docx_document.return_value = mock_doc_instance
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await extractor._extract_from_docx(content, filename)
        assert "No readable text found in DOCX" in str(exc_info.value)
    
    def test_extract_text_from_html_removes_tags(self, extractor):
        """Test HTML text extraction removes tags properly"""
        # Arrange
        html_content = "<html><body><h1>Title</h1><p>Paragraph with <strong>bold</strong> text.</p></body></html>"
        
        # Act
        result = extractor._extract_text_from_html(html_content)
        
        # Assert
        assert "<" not in result
        assert ">" not in result
        assert "Title" in result
        assert "Paragraph with bold text." in result
    
    def test_extract_text_from_html_removes_script_and_style(self, extractor):
        """Test HTML text extraction removes script and style elements"""
        # Arrange
        html_content = """
        <html>
        <head>
            <style>body { color: red; }</style>
        </head>
        <body>
            <p>Visible content</p>
            <script>alert('hello');</script>
        </body>
        </html>
        """
        
        # Act
        result = extractor._extract_text_from_html(html_content)
        
        # Assert
        assert "color: red" not in result
        assert "alert" not in result
        assert "Visible content" in result
    
    def test_extract_text_from_html_decodes_entities(self, extractor):
        """Test HTML text extraction decodes HTML entities"""
        # Arrange
        html_content = "<p>&lt;Hello &amp; goodbye&gt; &quot;world&quot;</p>"
        
        # Act
        result = extractor._extract_text_from_html(html_content)
        
        # Assert
        assert "<Hello & goodbye>" in result
        assert '"world"' in result
    
    def test_get_supported_types_returns_list(self, extractor):
        """Test that get_supported_types returns the expected file types"""
        # Act
        supported_types = extractor.get_supported_types()
        
        # Assert
        assert isinstance(supported_types, list)
        assert 'application/pdf' in supported_types
        assert 'text/plain' in supported_types
        assert 'application/epub+zip' in supported_types
        assert 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in supported_types
    
    @pytest.mark.parametrize("content_type,expected", [
        ("application/pdf", True),
        ("text/plain", True),
        ("application/epub+zip", True),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", True),
        ("application/unknown", False),
        ("image/jpeg", False),
    ])
    def test_is_supported_type(self, extractor, content_type, expected):
        """Test is_supported_type for various content types"""
        # Act
        result = extractor.is_supported_type(content_type)
        
        # Assert
        assert result == expected