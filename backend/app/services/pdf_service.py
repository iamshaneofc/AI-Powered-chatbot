"""
services/pdf_service.py — PDF extraction service.
"""

from pathlib import Path

class PDFService:
    @staticmethod
    def extract_text(file_path: Path) -> str:
        """
        Extract plain text from a PDF file using PyPDF2.
        
        Args:
            file_path: Path to the PDF file.
            
        Returns:
            Extracted text as a string.
        """
        try:
            import PyPDF2
        except ImportError:
            raise RuntimeError("PyPDF2 is not installed. Please install it to use PDF extraction.")

        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text.strip()

# Singleton instance
pdf_service = PDFService()
