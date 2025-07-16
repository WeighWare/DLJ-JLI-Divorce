#!/usr/bin/env python3
"""
Test script for document extraction functionality.

This script tests the basic functionality of the document extractor
without requiring actual document files.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract_documents import DocumentExtractor


def test_basic_functionality():
    """Test basic functionality of the DocumentExtractor class."""
    print("Testing DocumentExtractor basic functionality...")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        
        # Create input directory
        input_dir.mkdir()
        
        # Test extractor initialization
        try:
            extractor = DocumentExtractor(
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                ocr_lang="eng",
                workers=1,
                log_level="INFO"
            )
            print("✓ DocumentExtractor initialized successfully")
        except Exception as e:
            print(f"✗ Failed to initialize DocumentExtractor: {e}")
            return False
        
        # Test directory creation
        if extractor.md_dir.exists():
            print("✓ Markdown directory created")
        else:
            print("✗ Markdown directory not created")
            return False
        
        if extractor.csv_dir.exists():
            print("✓ CSV directory created")
        else:
            print("✗ CSV directory not created")
            return False
        
        if extractor.logs_dir.exists():
            print("✓ Logs directory created")
        else:
            print("✗ Logs directory not created")
            return False
        
        # Test filename sanitization
        test_filenames = [
            "normal_file.pdf",
            "file with spaces.pdf",
            "file<with>special:chars?.pdf",
            "very_long_filename_" + "a" * 300 + ".pdf"
        ]
        
        for filename in test_filenames:
            sanitized = extractor._sanitize_filename(filename)
            if len(sanitized) <= 200 and not any(char in sanitized for char in '<>:"/\\|?*'):
                print(f"✓ Filename sanitization works: {filename[:30]}...")
            else:
                print(f"✗ Filename sanitization failed: {filename}")
                return False
        
        # Test text cleaning
        test_text = """
        Page 1 of 5
        
        This is some test text with    multiple    spaces.
        
        Another paragraph here.
        
        10:30:45 AM
        01/15/2024
        """
        
        cleaned = extractor._clean_text(test_text)
        if "Page 1 of 5" not in cleaned and "10:30:45 AM" not in cleaned:
            print("✓ Text cleaning works")
        else:
            print("✗ Text cleaning failed")
            return False
        
        print("✓ All basic functionality tests passed")
        return True


def test_dependencies():
    """Test if all required dependencies are available."""
    print("\nTesting dependencies...")
    
    dependencies = [
        ("pdfplumber", "pdfplumber"),
        ("pytesseract", "pytesseract"),
        ("camelot", "camelot"),
        ("cv2", "opencv-python"),
        ("pandas", "pandas"),
        ("yaml", "PyYAML"),
        ("dotenv", "python-dotenv")
    ]
    
    missing_deps = []
    
    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
            print(f"✓ {package_name} available")
        except ImportError:
            print(f"✗ {package_name} missing")
            missing_deps.append(package_name)
    
    if missing_deps:
        print(f"\nMissing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✓ All dependencies available")
    return True


def main():
    """Run all tests."""
    print("Document Extraction Test Suite")
    print("=" * 40)
    
    # Test dependencies first
    if not test_dependencies():
        print("\n❌ Dependency test failed")
        return 1
    
    # Test basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality test failed")
        return 1
    
    print("\n✅ All tests passed!")
    print("\nNext steps:")
    print("1. Install Tesseract OCR if not already installed")
    print("2. Create a 'docs' directory and add your documents")
    print("3. Run: python extract_documents.py --input ./docs --output ./build")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 