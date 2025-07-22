#!/usr/bin/env python3
"""
Document Extraction Tool

A comprehensive tool for extracting content from divorce-related documents.
Processes PDFs, Excel files, and CSVs into structured Markdown and CSV outputs.

Supported formats: PDF, Excel (.xlsx), CSV
Output: Per-page Markdown files and per-table CSV files
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from dotenv import load_dotenv

# Import document processing libraries with graceful fallbacks
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False
    
try:
    import pdfplumber
    import camelot
    PDFTOOLS_AVAILABLE = True
except ImportError:
    PDFTOOLS_AVAILABLE = False

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False


class DocumentExtractor:
    """Main document extraction class with multiple processing strategies."""
    
    def __init__(self, input_dir: str = "docs", output_dir: str = "build", 
                 logger: logging.Logger = None):
        """
        Initialize the document extractor.
        
        Args:
            input_dir: Input directory containing documents
            output_dir: Output directory for processed files
            logger: Logger instance
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.logger = logger or logging.getLogger(__name__)
        
        # Create output directories
        self.md_dir = self.output_dir / "md"
        self.csv_dir = self.output_dir / "csv"
        
        for dir_path in [self.md_dir, self.csv_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Initialize processors
        self._init_processors()
    
    def _init_processors(self):
        """Initialize available processing tools."""
        self.processors = {}
        
        if MARKITDOWN_AVAILABLE:
            self.processors["markitdown"] = MarkItDown()
            
        if DOCLING_AVAILABLE:
            self.processors["docling"] = DocumentConverter()
            
        available = list(self.processors.keys())
        if PDFTOOLS_AVAILABLE:
            available.extend(["pdfplumber", "camelot"])
            
        self.logger.info(f"Available processors: {available}")
    
    def discover_files(self) -> List[Path]:
        """
        Discover all supported files in the input directory.
        
        Returns:
            List of file paths to process
        """
        supported_extensions = {".pdf", ".xlsx", ".csv"}
        files = []
        
        if not self.input_dir.exists():
            self.logger.warning(f"Input directory {self.input_dir} does not exist")
            return files
        
        for ext in supported_extensions:
            files.extend(self.input_dir.glob(f"**/*{ext}"))
            
        self.logger.info(f"Discovered {len(files)} files: {[f.name for f in files]}")
        return files
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file operations."""
        name = Path(filename).stem
        safe_chars = "".join(c for c in name if c.isalnum() or c in "._-")
        return safe_chars[:100]
    
    def extract_pdf_pages(self, pdf_path: Path) -> List[Dict]:
        """
        Extract individual pages from PDF using pdfplumber.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of page information dictionaries
        """
        pages_info = []
        
        if not PDFTOOLS_AVAILABLE:
            self.logger.warning("pdfplumber not available for page extraction")
            return pages_info
            
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    
                    pages_info.append({
                        "page_number": page_num,
                        "text": text,
                        "text_length": len(text)
                    })
                    
        except Exception as e:
            self.logger.error(f"Failed to extract pages from {pdf_path}: {e}")
            
        return pages_info
    
    def process_pdf_with_markitdown(self, pdf_path: Path, pages_info: List[Dict]) -> Dict:
        """
        Process PDF using MarkItDown for content conversion.
        
        Args:
            pdf_path: Path to PDF file
            pages_info: Page information from pdfplumber
            
        Returns:
            Processing results dictionary
        """
        results = {"pages": [], "success": False}
        
        if not MARKITDOWN_AVAILABLE:
            return results
            
        try:
            safe_name = self.sanitize_filename(pdf_path.name)
            converter = self.processors["markitdown"]
            
            # Convert entire PDF
            result = converter.convert(str(pdf_path))
            
            if result and result.text_content:
                # Create per-page markdown files
                content_lines = result.text_content.split('\n')
                
                for page_info in pages_info:
                    page_num = page_info["page_number"]
                    md_file = self.md_dir / f"{safe_name}_p{page_num}.md"
                    
                    # Use page-specific text if available, otherwise estimate from full content
                    if page_info["text_length"] > 0:
                        page_content = page_info["text"]
                    else:
                        # Rough estimation for page content distribution
                        lines_per_page = max(1, len(content_lines) // len(pages_info))
                        start_line = (page_num - 1) * lines_per_page
                        end_line = min(page_num * lines_per_page, len(content_lines))
                        page_content = '\n'.join(content_lines[start_line:end_line])
                    
                    md_content = f"""# {pdf_path.name} - Page {page_num}

## Content
{page_content}

## Processing Information
- Extracted using: MarkItDown
- Text length: {len(page_content)} characters
- Processing timestamp: {datetime.now().isoformat()}
"""
                    
                    with open(md_file, "w", encoding="utf-8") as f:
                        f.write(md_content)
                    
                    results["pages"].append({
                        "page": page_num,
                        "md_file": md_file,
                        "text_length": len(page_content)
                    })
                
                results["success"] = True
                self.logger.info(f"MarkItDown processed {len(pages_info)} pages from {pdf_path.name}")
        
        except Exception as e:
            self.logger.error(f"MarkItDown failed for {pdf_path}: {e}")
            
        return results
    
    def process_pdf_with_docling(self, pdf_path: Path) -> Dict:
        """
        Process PDF using Docling for enhanced extraction.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Processing results dictionary
        """
        results = {"pages": [], "tables": [], "success": False}
        
        if not DOCLING_AVAILABLE:
            return results
            
        try:
            safe_name = self.sanitize_filename(pdf_path.name)
            converter = self.processors["docling"]
            
            # Convert with Docling
            doc = converter.convert(str(pdf_path))
            
            # Extract content per page
            for page_num, page in enumerate(doc.pages, 1):
                md_file = self.md_dir / f"{safe_name}_p{page_num}.md"
                
                # Get page content
                page_text = page.text if hasattr(page, 'text') else str(page)
                
                md_content = f"""# {pdf_path.name} - Page {page_num}

## Content
{page_text}

## Processing Information
- Extracted using: Docling
- Text length: {len(page_text)} characters
- Processing timestamp: {datetime.now().isoformat()}
"""
                
                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(md_content)
                
                results["pages"].append({
                    "page": page_num,
                    "md_file": md_file,
                    "text_length": len(page_text)
                })
            
            # Extract tables if available
            if hasattr(doc, 'tables'):
                for table_idx, table in enumerate(doc.tables):
                    page_num = getattr(table, 'page_number', 1)
                    csv_file = self.csv_dir / f"{safe_name}_p{page_num}_table{table_idx}.csv"
                    
                    # Convert table to DataFrame
                    if hasattr(table, 'to_dataframe'):
                        df = table.to_dataframe()
                        df.to_csv(csv_file, index=False)
                        
                        results["tables"].append({
                            "page": page_num,
                            "table_idx": table_idx,
                            "csv_file": csv_file,
                            "rows": len(df)
                        })
            
            results["success"] = True
            self.logger.info(f"Docling processed {len(results['pages'])} pages and {len(results['tables'])} tables")
            
        except Exception as e:
            self.logger.error(f"Docling failed for {pdf_path}: {e}")
            
        return results
    
    def extract_tables_with_camelot(self, pdf_path: Path) -> Dict:
        """
        Extract tables using Camelot.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Table extraction results
        """
        results = {"tables": [], "success": False}
        
        if not PDFTOOLS_AVAILABLE:
            return results
            
        try:
            safe_name = self.sanitize_filename(pdf_path.name)
            
            # Extract tables with camelot
            tables = camelot.read_pdf(str(pdf_path), flavor="stream")
            
            for table_idx, table in enumerate(tables):
                page_num = table.page
                csv_file = self.csv_dir / f"{safe_name}_p{page_num}_table{table_idx}.csv"
                
                # Save table as CSV
                table.to_csv(str(csv_file))
                
                results["tables"].append({
                    "page": page_num,
                    "table_idx": table_idx,
                    "csv_file": csv_file,
                    "rows": len(table.df)
                })
            
            results["success"] = len(results["tables"]) > 0
            if results["success"]:
                self.logger.info(f"Camelot extracted {len(results['tables'])} tables from {pdf_path.name}")
                
        except Exception as e:
            self.logger.warning(f"Camelot table extraction failed for {pdf_path}: {e}")
            
        return results
    
    def process_pdf(self, pdf_path: Path) -> Dict:
        """
        Process PDF file using available strategies.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Comprehensive processing results
        """
        self.logger.info(f"Processing PDF: {pdf_path.name}")
        
        results = {
            "file": pdf_path,
            "total_pages": 0,
            "total_tables": 0,
            "methods_used": [],
            "success": False
        }
        
        # Extract page information
        pages_info = self.extract_pdf_pages(pdf_path)
        if not pages_info:
            self.logger.error(f"Could not extract page information from {pdf_path}")
            return results
        
        # Try different processing methods
        processed_pages = False
        
        # Method 1: MarkItDown
        markitdown_results = self.process_pdf_with_markitdown(pdf_path, pages_info)
        if markitdown_results["success"]:
            results["methods_used"].append("markitdown")
            results["total_pages"] = len(markitdown_results["pages"])
            processed_pages = True
        
        # Method 2: Docling (as alternative or supplement)
        if not processed_pages:
            docling_results = self.process_pdf_with_docling(pdf_path)
            if docling_results["success"]:
                results["methods_used"].append("docling")
                results["total_pages"] = len(docling_results["pages"])
                results["total_tables"] += len(docling_results["tables"])
                processed_pages = True
        
        # Method 3: Camelot for table extraction
        camelot_results = self.extract_tables_with_camelot(pdf_path)
        if camelot_results["success"]:
            results["methods_used"].append("camelot")
            results["total_tables"] += len(camelot_results["tables"])
        
        # Fallback: pdfplumber for basic text extraction
        if not processed_pages and PDFTOOLS_AVAILABLE:
            safe_name = self.sanitize_filename(pdf_path.name)
            for page_info in pages_info:
                page_num = page_info["page_number"]
                md_file = self.md_dir / f"{safe_name}_p{page_num}.md"
                
                md_content = f"""# {pdf_path.name} - Page {page_num}

## Content
{page_info["text"]}

## Processing Information
- Extracted using: pdfplumber (fallback)
- Text length: {page_info["text_length"]} characters
- Processing timestamp: {datetime.now().isoformat()}
"""
                
                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(md_content)
            
            results["methods_used"].append("pdfplumber")
            results["total_pages"] = len(pages_info)
            processed_pages = True
        
        results["success"] = processed_pages
        
        self.logger.info(f"PDF processing complete: {pdf_path.name} - "
                        f"Pages: {results['total_pages']}, "
                        f"Tables: {results['total_tables']}, "
                        f"Methods: {results['methods_used']}")
        
        return results
    
    def process_excel(self, excel_path: Path) -> Dict:
        """
        Process Excel file by extracting all sheets.
        
        Args:
            excel_path: Path to Excel file
            
        Returns:
            Processing results dictionary
        """
        self.logger.info(f"Processing Excel: {excel_path.name}")
        
        results = {
            "file": excel_path,
            "sheets": [],
            "success": False
        }
        
        try:
            safe_name = self.sanitize_filename(excel_path.name)
            excel_file = pd.ExcelFile(excel_path)
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                
                # Sanitize sheet name
                safe_sheet = "".join(c for c in sheet_name if c.isalnum() or c in "._-")
                
                # Save CSV
                csv_file = self.csv_dir / f"{safe_name}_{safe_sheet}.csv"
                df.to_csv(csv_file, index=False)
                
                # Create Markdown summary
                md_file = self.md_dir / f"{safe_name}_{safe_sheet}.md"
                
                md_content = f"""# {excel_path.name} - Sheet: {sheet_name}

## Summary
- Rows: {len(df)}
- Columns: {len(df.columns)}
- CSV File: {csv_file.name}

## Column Information
{df.dtypes.to_string()}

## Sample Data (First 5 rows)
{df.head().to_markdown(index=False) if len(df) > 0 else "No data"}

## Processing Information
- Extracted using: pandas
- Processing timestamp: {datetime.now().isoformat()}
"""
                
                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(md_content)
                
                results["sheets"].append({
                    "sheet_name": sheet_name,
                    "csv_file": csv_file,
                    "md_file": md_file,
                    "rows": len(df),
                    "columns": len(df.columns)
                })
            
            results["success"] = len(results["sheets"]) > 0
            self.logger.info(f"Excel processing complete: {len(results['sheets'])} sheets")
            
        except Exception as e:
            self.logger.error(f"Excel processing failed for {excel_path}: {e}")
        
        return results
    
    def process_csv(self, csv_path: Path) -> Dict:
        """
        Process CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Processing results dictionary
        """
        self.logger.info(f"Processing CSV: {csv_path.name}")
        
        results = {
            "file": csv_path,
            "success": False
        }
        
        try:
            safe_name = self.sanitize_filename(csv_path.name)
            df = pd.read_csv(csv_path)
            
            # Copy to output directory
            csv_file = self.csv_dir / f"{safe_name}.csv"
            df.to_csv(csv_file, index=False)
            
            # Create Markdown summary
            md_file = self.md_dir / f"{safe_name}.md"
            
            md_content = f"""# {csv_path.name}

## Summary
- Rows: {len(df)}
- Columns: {len(df.columns)}
- CSV File: {csv_file.name}

## Column Information
{df.dtypes.to_string()}

## Sample Data (First 5 rows)
{df.head().to_markdown(index=False) if len(df) > 0 else "No data"}

## Processing Information
- Extracted using: pandas
- Processing timestamp: {datetime.now().isoformat()}
"""
            
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            results.update({
                "csv_file": csv_file,
                "md_file": md_file,
                "rows": len(df),
                "columns": len(df.columns),
                "success": True
            })
            
            self.logger.info(f"CSV processing complete: {len(df)} rows, {len(df.columns)} columns")
            
        except Exception as e:
            self.logger.error(f"CSV processing failed for {csv_path}: {e}")
        
        return results
    
    def process_file(self, file_path: Path) -> Dict:
        """
        Process a single file based on its extension.
        
        Args:
            file_path: Path to file to process
            
        Returns:
            Processing results dictionary
        """
        try:
            if file_path.suffix.lower() == ".pdf":
                return self.process_pdf(file_path)
            elif file_path.suffix.lower() == ".xlsx":
                return self.process_excel(file_path)
            elif file_path.suffix.lower() == ".csv":
                return self.process_csv(file_path)
            else:
                self.logger.warning(f"Unsupported file type: {file_path}")
                return {"file": file_path, "success": False, "error": "Unsupported file type"}
                
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return {"file": file_path, "success": False, "error": str(e)}
    
    def extract_all(self) -> Dict:
        """
        Extract all documents from the input directory.
        
        Returns:
            Summary of extraction results
        """
        start_time = time.time()
        
        files = self.discover_files()
        if not files:
            self.logger.warning("No supported files found in input directory")
            return {"total_files": 0, "successful": 0, "failed": 0, "processing_time": 0}
        
        results = []
        for file_path in files:
            result = self.process_file(file_path)
            results.append(result)
        
        # Calculate statistics
        end_time = time.time()
        processing_time = end_time - start_time
        
        successful = sum(1 for r in results if r.get("success", False))
        total_pages = sum(r.get("total_pages", 0) for r in results)
        total_tables = sum(r.get("total_tables", 0) for r in results)
        
        summary = {
            "total_files": len(files),
            "successful": successful,
            "failed": len(files) - successful,
            "total_pages": total_pages,
            "total_tables": total_tables,
            "processing_time": processing_time
        }
        
        self.logger.info("=" * 60)
        self.logger.info("EXTRACTION COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Total files processed: {summary['total_files']}")
        self.logger.info(f"Successful: {summary['successful']}")
        self.logger.info(f"Failed: {summary['failed']}")
        self.logger.info(f"Total pages extracted: {summary['total_pages']}")
        self.logger.info(f"Total tables extracted: {summary['total_tables']}")
        self.logger.info(f"Processing time: {summary['processing_time']:.2f} seconds")
        
        return summary


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    logs_dir = Path("build") / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"extraction_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("extract_docs")
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger


def main():
    """Main CLI entry point."""
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Document Extraction Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_docs.py                    # Extract all files from docs/
  python extract_docs.py --input my_docs   # Extract from custom input directory
  python extract_docs.py --verbose         # Enable verbose logging
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=os.getenv("INPUT_DIR", "docs"),
        help="Input directory containing documents (default: docs)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=os.getenv("OUTPUT_DIR", "build"),
        help="Output directory for processed files (default: build)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = setup_logging(log_level)
    
    # Log configuration
    logger.info("Starting document extraction")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {args.output}")
    
    # Create input directory if it doesn't exist
    input_path = Path(args.input)
    if not input_path.exists():
        logger.warning(f"Input directory {input_path} does not exist. Creating it.")
        input_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Place your PDF, Excel, and CSV files in {input_path}")
        return
    
    # Initialize extractor and run
    extractor = DocumentExtractor(
        input_dir=args.input,
        output_dir=args.output,
        logger=logger
    )
    
    summary = extractor.extract_all()
    
    if summary["successful"] == 0:
        logger.warning("No files were successfully processed.")
        logger.info(f"Check that you have supported files (.pdf, .xlsx, .csv) in {args.input}")
    
    return 0 if summary["successful"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main()) 