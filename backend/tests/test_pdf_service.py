import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.pdf_service import pdf_service

def test_extract_text_empty_pdf():
    """Test behavior when a PDF contains no extractable text (e.g. image-only)."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "" # Simulate empty page
    mock_reader.pages = [mock_page]
    
    with patch("builtins.open"), patch("PyPDF2.PdfReader", return_value=mock_reader):
        text = pdf_service.extract_text(Path("empty.pdf"))
        assert text == ""

def test_extract_text_no_pypdf2():
    """Test failure mode when PyPDF2 is uninstalled/missing."""
    with patch.dict('sys.modules', {'PyPDF2': None}):
        with pytest.raises(RuntimeError, match="PyPDF2 is not installed"):
            pdf_service.extract_text(Path("test.pdf"))
