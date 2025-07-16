#!/usr/bin/env python3
"""
Document Extraction Script for Divorce-Related Files

This script processes mixed folders of divorce-related source files (PDFs, Excel, CSV)
and outputs clean, organized Markdown and CSV files suitable for analysis.

Usage:
    python extract_documents.py --input ./docs --output ./build --ocr-lang eng
"""

import argparse
import concurrent.futures
import csv
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import warnings

import camelot
import cv2
import numpy as np
import pandas as pd
import pdfplumber
import pytesseract
import yaml
from dotenv import load_dotenv

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()


class DocumentExtractor:
    """Main class for extracting documents from various formats."""
    
    def __init__(self, input_dir: str, output_dir: str, ocr_lang: str = "eng", 
                 workers: int = 1, log_level: str = "INFO"):
        """
        Initialize the document extractor.
        
        Args:
            input_dir: Directory containing source documents
            output_dir: Directory for output files
            ocr_lang: Language for OCR processing
            workers: Number of worker processes
            log_level: Logging level
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.ocr_lang = ocr_lang
        self.workers = workers
        
        # Create output directories
        self.md_dir = self.output_dir / "md"
        self.csv_dir = self.output_dir / "csv"
        self.logs_dir = self.output_dir / "logs"
        
        for dir_path in [self.md_dir, self.csv_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging(log_level)
        
        # Check Tesseract availability
        self._check_tesseract()
        
        # Track processing statistics
        self.stats = {
            "files_processed": 0,
            "pages_processed": 0,
            "tables_extracted": 0,
            "ocr_pages": 0,
            "errors": 0
        }
    
    def _setup_logging(self, log_level: str):
        """Setup logging configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"run_{timestamp}.log"
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _check_tesseract(self):
        """Check if Tesseract is available and provide helpful message if not."""
        try:
            pytesseract.get_tesseract_version()
            self.logger.info("Tesseract OCR is available")
        except Exception as e:
            self.logger.error("Tesseract OCR not found. Please install:")
            self.logger.error("Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            self.logger.error("macOS: brew install tesseract")
            self.logger.error("Linux: sudo apt-get install tesseract-ocr")
            raise SystemExit(1)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks."""
        # Remove or replace dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(sanitized) > 200:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:200-len(ext)] + ext
        return sanitized
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing headers/footers and normalizing whitespace."""
        if not text:
            return ""
        
        # Remove page numbers and timestamps
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d{1,2}:\d{2}:\d{2}', '', text)
        text = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '', text)
        
        # Remove excessive whitespace while preserving paragraph breaks
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Collapse multiple spaces
            line = re.sub(r'\s+', ' ', line.strip())
            if line:
                cleaned_lines.append(line)
            else:
                # Preserve paragraph breaks
                if cleaned_lines and cleaned_lines[-1] != '':
                    cleaned_lines.append('')
        
        return '\n'.join(cleaned_lines).strip()
    
    def _is_scanned_page(self, page) -> bool:
        """Detect if a PDF page is scanned (no embedded text)."""
        text = page.extract_text()
        return len(text.strip()) < 50  # Threshold for minimal text
    
    def _extract_text_with_ocr(self, page) -> str:
        """Extract text from scanned page using OCR."""
        try:
            # Convert page to image
            img = page.to_image()
            img_array = np.array(img.original)
            
            # Convert to grayscale for better OCR
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply preprocessing for better OCR results
            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(enhanced, lang=self.ocr_lang)
            
            self.stats["ocr_pages"] += 1
            return text
            
        except Exception as e:
            self.logger.error(f"OCR failed: {e}")
            return ""
    
    def _extract_tables_pdfplumber(self, page) -> List[pd.DataFrame]:
        """Extract tables using pdfplumber."""
        tables = []
        try:
            extracted_tables = page.extract_tables()
            for table in extracted_tables:
                if table and len(table) > 1:  # At least header + one row
                    df = pd.DataFrame(table[1:], columns=table[0])
                    tables.append(df)
        except Exception as e:
            self.logger.debug(f"pdfplumber table extraction failed: {e}")
        
        return tables
    
    def _extract_tables_camelot(self, page) -> List[pd.DataFrame]:
        """Extract tables using camelot as fallback."""
        tables = []
        try:
            # Convert page to image for camelot
            img = page.to_image()
            img_path = f"/tmp/temp_page_{id(page)}.png"
            img.save(img_path)
            
            # Extract tables using stream flavor
            extracted_tables = camelot.read_pdf(img_path, flavor='stream', pages='1')
            
            for table in extracted_tables:
                if table.df is not None and len(table.df) > 1:
                    tables.append(table.df)
            
            # Clean up temp file
            os.remove(img_path)
            
        except Exception as e:
            self.logger.debug(f"camelot table extraction failed: {e}")
        
        return tables
    
    def _save_table_csv(self, df: pd.DataFrame, source_file: str, page_num: int, 
                       table_num: int) -> str:
        """Save table to CSV file and return filename."""
        filename = self._sanitize_filename(f"{source_file}_p{page_num}_t{table_num}.csv")
        filepath = self.csv_dir / filename
        
        try:
            df.to_csv(filepath, index=False, encoding='utf-8')
            self.stats["tables_extracted"] += 1
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save table CSV {filename}: {e}")
            return ""
    
    def _create_markdown_content(self, text: str, source_file: str, page_num: int,
                               has_tables: bool, table_files: List[str]) -> str:
        """Create markdown content with YAML front-matter."""
        # YAML front-matter
        front_matter = {
            "source": f"{source_file}#page={page_num}",
            "extracted_at": datetime.now().isoformat(),
            "has_tables": has_tables
        }
        
        if table_files:
            front_matter["table_files"] = table_files
        
        yaml_content = yaml.dump(front_matter, default_flow_style=False, sort_keys=False)
        
        # Combine front-matter and content
        content = f"---\n{yaml_content}---\n\n{text}\n"
        
        return content
    
    def _save_markdown(self, content: str, source_file: str, page_num: int) -> str:
        """Save markdown content to file and return filename."""
        filename = self._sanitize_filename(f"{source_file}_p{page_num}.md")
        filepath = self.md_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save markdown {filename}: {e}")
            return ""
    
    def process_pdf(self, filepath: Path) -> None:
        """Process a single PDF file."""
        try:
            self.logger.info(f"Processing PDF: {filepath.name}")
            
            with pdfplumber.open(filepath) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract text
                        if self._is_scanned_page(page):
                            text = self._extract_text_with_ocr(page)
                            self.logger.debug(f"Used OCR for page {page_num}")
                        else:
                            text = page.extract_text()
                        
                        text = self._clean_text(text)
                        
                        # Extract tables
                        tables = self._extract_tables_pdfplumber(page)
                        if not tables:
                            tables = self._extract_tables_camelot(page)
                        
                        # Save tables to CSV
                        table_files = []
                        for table_num, table in enumerate(tables, 1):
                            csv_filename = self._save_table_csv(
                                table, filepath.stem, page_num, table_num
                            )
                            if csv_filename:
                                table_files.append(csv_filename)
                        
                        # Create and save markdown
                        has_tables = len(table_files) > 0
                        content = self._create_markdown_content(
                            text, filepath.name, page_num, has_tables, table_files
                        )
                        
                        md_filename = self._save_markdown(content, filepath.stem, page_num)
                        
                        if md_filename:
                            self.stats["pages_processed"] += 1
                            self.logger.debug(f"Processed page {page_num}")
                        
                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num} of {filepath.name}: {e}")
                        self.stats["errors"] += 1
            
            self.stats["files_processed"] += 1
            
        except Exception as e:
            self.logger.error(f"Error processing PDF {filepath.name}: {e}")
            self.stats["errors"] += 1
    
    def process_excel(self, filepath: Path) -> None:
        """Process a single Excel file."""
        try:
            self.logger.info(f"Processing Excel: {filepath.name}")
            
            # Read all sheets
            excel_file = pd.ExcelFile(filepath)
            
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(filepath, sheet_name=sheet_name)
                    
                    # Save to CSV
                    safe_sheet_name = self._sanitize_filename(sheet_name)
                    csv_filename = f"{filepath.stem}_{safe_sheet_name}.csv"
                    csv_filepath = self.csv_dir / csv_filename
                    
                    df.to_csv(csv_filepath, index=False, encoding='utf-8')
                    self.stats["tables_extracted"] += 1
                    
                    # Create markdown with table reference
                    content = self._create_markdown_content(
                        f"Excel sheet '{sheet_name}' extracted to CSV: {csv_filename}",
                        filepath.name, 1, True, [csv_filename]
                    )
                    
                    md_filename = self._save_markdown(content, filepath.stem, 1)
                    
                    if md_filename:
                        self.stats["pages_processed"] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing sheet {sheet_name} of {filepath.name}: {e}")
                    self.stats["errors"] += 1
            
            self.stats["files_processed"] += 1
            
        except Exception as e:
            self.logger.error(f"Error processing Excel {filepath.name}: {e}")
            self.stats["errors"] += 1
    
    def process_csv(self, filepath: Path) -> None:
        """Process a single CSV file."""
        try:
            self.logger.info(f"Processing CSV: {filepath.name}")
            
            # Read CSV
            df = pd.read_csv(filepath)
            
            # Copy to output directory
            csv_filename = f"{filepath.stem}_extracted.csv"
            csv_filepath = self.csv_dir / csv_filename
            
            df.to_csv(csv_filepath, index=False, encoding='utf-8')
            self.stats["tables_extracted"] += 1
            
            # Create markdown with table reference
            content = self._create_markdown_content(
                f"CSV file extracted: {csv_filename}",
                filepath.name, 1, True, [csv_filename]
            )
            
            md_filename = self._save_markdown(content, filepath.stem, 1)
            
            if md_filename:
                self.stats["pages_processed"] += 1
            
            self.stats["files_processed"] += 1
            
        except Exception as e:
            self.logger.error(f"Error processing CSV {filepath.name}: {e}")
            self.stats["errors"] += 1
    
    def process_file(self, filepath: Path) -> None:
        """Process a single file based on its extension."""
        try:
            if filepath.suffix.lower() == '.pdf':
                self.process_pdf(filepath)
            elif filepath.suffix.lower() in ['.xlsx', '.xls']:
                self.process_excel(filepath)
            elif filepath.suffix.lower() == '.csv':
                self.process_csv(filepath)
            else:
                self.logger.warning(f"Unsupported file type: {filepath}")
                
        except Exception as e:
            self.logger.error(f"Error processing file {filepath}: {e}")
            self.stats["errors"] += 1
    
    def run(self) -> None:
        """Run the document extraction process."""
        start_time = time.time()
        
        self.logger.info(f"Starting document extraction from {self.input_dir}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"OCR language: {self.ocr_lang}")
        self.logger.info(f"Workers: {self.workers}")
        
        # Find all supported files
        supported_extensions = {'.pdf', '.xlsx', '.xls', '.csv'}
        files = [
            f for f in self.input_dir.rglob('*')
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        
        if not files:
            self.logger.warning(f"No supported files found in {self.input_dir}")
            return
        
        self.logger.info(f"Found {len(files)} files to process")
        
        # Process files
        if self.workers > 1:
            # Use ProcessPoolExecutor for parallel processing
            with concurrent.futures.ProcessPoolExecutor(max_workers=self.workers) as executor:
                # Note: ProcessPoolExecutor has limitations with class methods
                # For simplicity, we'll process sequentially for now
                for filepath in files:
                    self.process_file(filepath)
        else:
            # Sequential processing
            for filepath in files:
                self.process_file(filepath)
        
        # Log final statistics
        elapsed_time = time.time() - start_time
        self.logger.info("=" * 50)
        self.logger.info("EXTRACTION COMPLETE")
        self.logger.info("=" * 50)
        self.logger.info(f"Files processed: {self.stats['files_processed']}")
        self.logger.info(f"Pages processed: {self.stats['pages_processed']}")
        self.logger.info(f"Tables extracted: {self.stats['tables_extracted']}")
        self.logger.info(f"OCR pages: {self.stats['ocr_pages']}")
        self.logger.info(f"Errors: {self.stats['errors']}")
        self.logger.info(f"Total time: {elapsed_time:.2f} seconds")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract documents from mixed file formats to Markdown and CSV"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input directory containing source documents"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for extracted files"
    )
    parser.add_argument(
        "--ocr-lang",
        default="eng",
        help="Language for OCR processing (default: eng)"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.input):
        print(f"Error: Input directory '{args.input}' does not exist")
        sys.exit(1)
    
    # Create extractor and run
    extractor = DocumentExtractor(
        input_dir=args.input,
        output_dir=args.output,
        ocr_lang=args.ocr_lang,
        workers=args.workers,
        log_level=args.log_level
    )
    
    try:
        extractor.run()
    except KeyboardInterrupt:
        print("\nExtraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 