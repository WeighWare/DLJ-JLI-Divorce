#!/usr/bin/env python3
"""
Document Extraction Tool

A comprehensive tool for extracting content from divorce-related documents.
Processes PDFs, Excel files, and CSVs into structured Markdown and CSV outputs
with document-level batching, metadata tracking, and duplicate detection.

Supported formats: PDF, Excel (.xlsx), CSV
Output: Per-document subdirectories with page-specific Markdown and CSV files
"""

import argparse
import hashlib
import json
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
    """Main document extraction class with enhanced batching and metadata tracking."""
    
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
        
        # Create base output directories
        self.md_dir = self.output_dir / "md"
        self.csv_dir = self.output_dir / "csv"
        self.logs_dir = self.output_dir / "logs"
        
        for dir_path in [self.md_dir, self.csv_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Initialize master index
        self.index_file = self.output_dir / "index.json"
        self.index_data = self._load_index()
        
        # Initialize processors
        self._init_processors()
    
    def _load_index(self) -> Dict:
        """Load or create the master index file."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Could not load index file: {e}. Creating new index.")
        
        return {}
    
    def _save_index(self):
        """Save the master index file."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.logger.error(f"Failed to save index file: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except IOError as e:
            self.logger.error(f"Failed to hash file {file_path}: {e}")
            return ""
    
    def _get_doc_id(self, file_path: Path) -> str:
        """Generate document ID from filename (without extension)."""
        return self.sanitize_filename(file_path.name)
    
    def _setup_document_logging(self, doc_id: str) -> logging.Logger:
        """Set up per-document logging."""
        doc_log_file = self.logs_dir / f"{doc_id}.log"
        
        # Create document-specific logger
        doc_logger = logging.getLogger(f"extract_docs.{doc_id}")
        doc_logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        doc_logger.handlers.clear()
        
        # Add file handler for this document
        file_handler = logging.FileHandler(doc_log_file, mode='w')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        doc_logger.addHandler(file_handler)
        
        return doc_logger
    
    def _check_duplicate(self, file_path: Path, doc_id: str) -> bool:
        """Check if file is a duplicate based on hash."""
        current_hash = self._calculate_file_hash(file_path)
        
        if doc_id in self.index_data:
            stored_hash = self.index_data[doc_id].get("hash", "")
            if stored_hash == current_hash:
                return True
        
        return False
    
    def _infer_category(self, filename: str) -> str:
        """Infer document category from filename."""
        filename_lower = filename.lower()
        
        if "transcript" in filename_lower:
            return "transcript"
        elif "bank" in filename_lower or "statement" in filename_lower:
            return "financial"
        elif any(term in filename_lower for term in ["report", "exhibit", "affidavit"]):
            return "legal"
        else:
            return "other"
    
    def _create_chunk_metadata(self, doc_id: str, filename: str, page_num: int, category: str, file_hash: str) -> str:
        """Create chunk metadata HTML comment for markdown files."""
        chunk_id = f"{doc_id}_p{page_num}"
        return f"""<!--
chunk_id: {chunk_id}
source: {filename}
page: {page_num}
category: {category}
hash: {file_hash}
-->"""
    
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
    
    def process_pdf_with_markitdown(self, pdf_path: Path, pages_info: List[Dict], doc_id: str, doc_logger: logging.Logger) -> Dict:
        """
        Process PDF using MarkItDown for content conversion.
        
        Args:
            pdf_path: Path to PDF file
            pages_info: Page information from pdfplumber
            doc_id: Document identifier
            doc_logger: Document-specific logger
            
        Returns:
            Processing results dictionary
        """
        results = {"pages": [], "success": False}
        
        if not MARKITDOWN_AVAILABLE:
            doc_logger.warning("MarkItDown not available")
            return results
            
        try:
            # Create document-specific subdirectory
            doc_md_dir = self.md_dir / doc_id
            doc_md_dir.mkdir(exist_ok=True)
            
            converter = self.processors["markitdown"]
            
            # Convert entire PDF
            result = converter.convert(str(pdf_path))
            
            if result and result.text_content:
                # Create per-page markdown files
                content_lines = result.text_content.split('\n')
                
                for page_info in pages_info:
                    page_num = page_info["page_number"]
                    md_file = doc_md_dir / f"p{page_num}.md"
                    
                    # Use page-specific text if available, otherwise estimate from full content
                    if page_info["text_length"] > 0:
                        page_content = page_info["text"]
                    else:
                        # Rough estimation for page content distribution
                        lines_per_page = max(1, len(content_lines) // len(pages_info))
                        start_line = (page_num - 1) * lines_per_page
                        end_line = min(page_num * lines_per_page, len(content_lines))
                        page_content = '\n'.join(content_lines[start_line:end_line])
                    
                    # Create chunk metadata
                    chunk_metadata = self._create_chunk_metadata(
                        doc_id, pdf_path.name, page_num, 
                        self._infer_category(pdf_path.name), 
                        self._calculate_file_hash(pdf_path)
                    )
                    
                    md_content = f"""{chunk_metadata}

# {pdf_path.name} - Page {page_num}

## Content
{page_content}

## Processing Information
- Document ID: {doc_id}
- Extracted using: MarkItDown
- Text length: {len(page_content)} characters
- Processing timestamp: {datetime.now().isoformat()}
"""
                    
                    with open(md_file, "w", encoding="utf-8") as f:
                        f.write(md_content)
                    
                    results["pages"].append({
                        "page": page_num,
                        "md_file": str(md_file.relative_to(self.output_dir)),
                        "text_length": len(page_content)
                    })
                
                results["success"] = True
                doc_logger.info(f"MarkItDown processed {len(pages_info)} pages")
        
        except Exception as e:
            doc_logger.error(f"MarkItDown failed: {e}")
            
        return results
    
    def process_pdf_with_docling(self, pdf_path: Path, doc_id: str, doc_logger: logging.Logger) -> Dict:
        """
        Process PDF using Docling for enhanced extraction.
        
        Args:
            pdf_path: Path to PDF file
            doc_id: Document identifier
            doc_logger: Document-specific logger
            
        Returns:
            Processing results dictionary
        """
        results = {"pages": [], "tables": [], "success": False}
        
        if not DOCLING_AVAILABLE:
            doc_logger.warning("Docling not available")
            return results
            
        try:
            # Create document-specific subdirectories
            doc_md_dir = self.md_dir / doc_id
            doc_csv_dir = self.csv_dir / doc_id
            doc_md_dir.mkdir(exist_ok=True)
            doc_csv_dir.mkdir(exist_ok=True)
            
            converter = self.processors["docling"]
            
            # Convert with Docling
            doc = converter.convert(str(pdf_path))
            
            # Extract content per page
            for page_num, page in enumerate(doc.pages, 1):
                md_file = doc_md_dir / f"p{page_num}.md"
                
                # Get page content
                page_text = page.text if hasattr(page, 'text') else str(page)
                
                # Create chunk metadata
                chunk_metadata = self._create_chunk_metadata(
                    doc_id, pdf_path.name, page_num, 
                    self._infer_category(pdf_path.name), 
                    self._calculate_file_hash(pdf_path)
                )
                
                md_content = f"""{chunk_metadata}

# {pdf_path.name} - Page {page_num}

## Content
{page_text}

## Processing Information
- Document ID: {doc_id}
- Extracted using: Docling
- Text length: {len(page_text)} characters
- Processing timestamp: {datetime.now().isoformat()}
"""
                
                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(md_content)
                
                results["pages"].append({
                    "page": page_num,
                    "md_file": str(md_file.relative_to(self.output_dir)),
                    "text_length": len(page_text)
                })
            
            # Extract tables if available
            if hasattr(doc, 'tables'):
                for table_idx, table in enumerate(doc.tables):
                    page_num = getattr(table, 'page_number', 1)
                    csv_file = doc_csv_dir / f"table{table_idx + 1}.csv"
                    
                    # Convert table to DataFrame
                    if hasattr(table, 'to_dataframe'):
                        df = table.to_dataframe()
                        df.to_csv(csv_file, index=False)
                        
                        results["tables"].append({
                            "page": page_num,
                            "table_idx": table_idx + 1,
                            "csv_file": str(csv_file.relative_to(self.output_dir)),
                            "rows": len(df)
                        })
            
            results["success"] = True
            doc_logger.info(f"Docling processed {len(results['pages'])} pages and {len(results['tables'])} tables")
            
        except Exception as e:
            doc_logger.error(f"Docling failed: {e}")
            
        return results
    
    def extract_tables_with_camelot(self, pdf_path: Path, doc_id: str, doc_logger: logging.Logger) -> Dict:
        """
        Extract tables using Camelot.
        
        Args:
            pdf_path: Path to PDF file
            doc_id: Document identifier
            doc_logger: Document-specific logger
            
        Returns:
            Table extraction results
        """
        results = {"tables": [], "success": False}
        
        if not PDFTOOLS_AVAILABLE:
            doc_logger.warning("Camelot not available")
            return results
            
        try:
            # Create document-specific subdirectory
            doc_csv_dir = self.csv_dir / doc_id
            doc_csv_dir.mkdir(exist_ok=True)
            
            # Extract tables with camelot
            tables = camelot.read_pdf(str(pdf_path), flavor="stream")
            
            for table_idx, table in enumerate(tables):
                page_num = table.page
                csv_file = doc_csv_dir / f"table{table_idx + 1}.csv"
                
                # Save table as CSV
                table.to_csv(str(csv_file))
                
                results["tables"].append({
                    "page": page_num,
                    "table_idx": table_idx + 1,
                    "csv_file": str(csv_file.relative_to(self.output_dir)),
                    "rows": len(table.df)
                })
            
            results["success"] = len(results["tables"]) > 0
            if results["success"]:
                doc_logger.info(f"Camelot extracted {len(results['tables'])} tables")
                
        except Exception as e:
            doc_logger.error(f"Camelot table extraction failed: {e}")
            
        return results
    
    def process_pdf(self, pdf_path: Path) -> Dict:
        """
        Process PDF file using available strategies.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Comprehensive processing results
        """
        doc_id = self._get_doc_id(pdf_path)
        doc_logger = self._setup_document_logging(doc_id)
        
        doc_logger.info(f"Starting PDF processing: {pdf_path.name}")
        
        # Check for duplicates
        if self._check_duplicate(pdf_path, doc_id):
            self.logger.info(f"Skipping duplicate file: {pdf_path.name}")
            doc_logger.info(f"File skipped - duplicate detected (same SHA-256 hash)")
            return self.index_data[doc_id]
        
        file_hash = self._calculate_file_hash(pdf_path)
        category = self._infer_category(pdf_path.name)
        
        results = {
            "filename": pdf_path.name,
            "hash": file_hash,
            "type": "pdf",
            "category": category,
            "pages": 0,
            "output_md": [],
            "output_csv": [],
            "log": str((self.logs_dir / f"{doc_id}.log").relative_to(self.output_dir)),
            "status": "processing",
            "created": datetime.now().isoformat()
        }
        
        try:
            # Extract page information
            pages_info = self.extract_pdf_pages(pdf_path)
            if not pages_info:
                doc_logger.error("Could not extract page information")
                results["status"] = "failed"
                return results
            
            results["pages"] = len(pages_info)
            
            # Try different processing methods
            processed_pages = False
            
            # Method 1: MarkItDown
            markitdown_results = self.process_pdf_with_markitdown(pdf_path, pages_info, doc_id, doc_logger)
            if markitdown_results["success"]:
                results["output_md"].extend([p["md_file"] for p in markitdown_results["pages"]])
                processed_pages = True
            
            # Method 2: Docling (as alternative or supplement)
            if not processed_pages:
                docling_results = self.process_pdf_with_docling(pdf_path, doc_id, doc_logger)
                if docling_results["success"]:
                    results["output_md"].extend([p["md_file"] for p in docling_results["pages"]])
                    results["output_csv"].extend([t["csv_file"] for t in docling_results["tables"]])
                    processed_pages = True
            
            # Method 3: Camelot for table extraction
            camelot_results = self.extract_tables_with_camelot(pdf_path, doc_id, doc_logger)
            if camelot_results["success"]:
                results["output_csv"].extend([t["csv_file"] for t in camelot_results["tables"]])
            
            # Fallback: pdfplumber for basic text extraction
            if not processed_pages and PDFTOOLS_AVAILABLE:
                doc_md_dir = self.md_dir / doc_id
                doc_md_dir.mkdir(exist_ok=True)
                
                for page_info in pages_info:
                    page_num = page_info["page_number"]
                    md_file = doc_md_dir / f"p{page_num}.md"
                    
                    # Create chunk metadata
                    chunk_metadata = self._create_chunk_metadata(
                        doc_id, pdf_path.name, page_num, 
                        category, file_hash
                    )
                    
                    md_content = f"""{chunk_metadata}

# {pdf_path.name} - Page {page_num}

## Content
{page_info["text"]}

## Processing Information
- Document ID: {doc_id}
- Extracted using: pdfplumber (fallback)
- Text length: {page_info["text_length"]} characters
- Processing timestamp: {datetime.now().isoformat()}
"""
                    
                    with open(md_file, "w", encoding="utf-8") as f:
                        f.write(md_content)
                    
                    results["output_md"].append(str(md_file.relative_to(self.output_dir)))
                
                doc_logger.info(f"Fallback pdfplumber processed {len(pages_info)} pages")
                processed_pages = True
            
            results["status"] = "completed" if processed_pages else "failed"
            
            doc_logger.info(f"PDF processing complete - Status: {results['status']}, "
                           f"Pages: {results['pages']}, "
                           f"MD files: {len(results['output_md'])}, "
                           f"CSV files: {len(results['output_csv'])}")
            
        except Exception as e:
            doc_logger.error(f"PDF processing failed with exception: {e}")
            results["status"] = "failed"
        
        # Update index
        self.index_data[doc_id] = results
        self._save_index()
        
        return results
    
    def process_excel(self, excel_path: Path) -> Dict:
        """
        Process Excel file by extracting all sheets.
        
        Args:
            excel_path: Path to Excel file
            
        Returns:
            Processing results dictionary
        """
        doc_id = self._get_doc_id(excel_path)
        doc_logger = self._setup_document_logging(doc_id)
        
        doc_logger.info(f"Starting Excel processing: {excel_path.name}")
        
        # Check for duplicates
        if self._check_duplicate(excel_path, doc_id):
            self.logger.info(f"Skipping duplicate file: {excel_path.name}")
            doc_logger.info(f"File skipped - duplicate detected (same SHA-256 hash)")
            return self.index_data[doc_id]
        
        file_hash = self._calculate_file_hash(excel_path)
        category = self._infer_category(excel_path.name)
        
        results = {
            "filename": excel_path.name,
            "hash": file_hash,
            "type": "excel",
            "category": category,
            "pages": 0,  # sheets for Excel
            "output_md": [],
            "output_csv": [],
            "log": str((self.logs_dir / f"{doc_id}.log").relative_to(self.output_dir)),
            "status": "processing",
            "created": datetime.now().isoformat()
        }
        
        try:
            # Create document-specific subdirectories
            doc_md_dir = self.md_dir / doc_id
            doc_csv_dir = self.csv_dir / doc_id
            doc_md_dir.mkdir(exist_ok=True)
            doc_csv_dir.mkdir(exist_ok=True)
            
            excel_file = pd.ExcelFile(excel_path)
            
            for sheet_idx, sheet_name in enumerate(excel_file.sheet_names, 1):
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                
                # Sanitize sheet name
                safe_sheet = "".join(c for c in sheet_name if c.isalnum() or c in "._-")
                
                # Save CSV
                csv_file = doc_csv_dir / f"{safe_sheet}.csv"
                df.to_csv(csv_file, index=False)
                
                # Create Markdown summary
                md_file = doc_md_dir / f"{safe_sheet}.md"
                
                # Create chunk metadata (using sheet index as page number)
                chunk_metadata = self._create_chunk_metadata(
                    doc_id, excel_path.name, sheet_idx, 
                    category, file_hash
                )
                
                md_content = f"""{chunk_metadata}

# {excel_path.name} - Sheet: {sheet_name}

## Summary
- Document ID: {doc_id}
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
                
                results["output_md"].append(str(md_file.relative_to(self.output_dir)))
                results["output_csv"].append(str(csv_file.relative_to(self.output_dir)))
                
                doc_logger.info(f"Processed sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns")
            
            results["pages"] = len(excel_file.sheet_names)
            results["status"] = "completed"
            
            doc_logger.info(f"Excel processing complete: {len(excel_file.sheet_names)} sheets processed")
            
        except Exception as e:
            doc_logger.error(f"Excel processing failed: {e}")
            results["status"] = "failed"
        
        # Update index
        self.index_data[doc_id] = results
        self._save_index()
        
        return results
    
    def process_csv(self, csv_path: Path) -> Dict:
        """
        Process CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Processing results dictionary
        """
        doc_id = self._get_doc_id(csv_path)
        doc_logger = self._setup_document_logging(doc_id)
        
        doc_logger.info(f"Starting CSV processing: {csv_path.name}")
        
        # Check for duplicates
        if self._check_duplicate(csv_path, doc_id):
            self.logger.info(f"Skipping duplicate file: {csv_path.name}")
            doc_logger.info(f"File skipped - duplicate detected (same SHA-256 hash)")
            return self.index_data[doc_id]
        
        file_hash = self._calculate_file_hash(csv_path)
        category = self._infer_category(csv_path.name)
        
        results = {
            "filename": csv_path.name,
            "hash": file_hash,
            "type": "csv",
            "category": category,
            "pages": 1,
            "output_md": [],
            "output_csv": [],
            "log": str((self.logs_dir / f"{doc_id}.log").relative_to(self.output_dir)),
            "status": "processing",
            "created": datetime.now().isoformat()
        }
        
        try:
            # Create document-specific subdirectories
            doc_md_dir = self.md_dir / doc_id
            doc_csv_dir = self.csv_dir / doc_id
            doc_md_dir.mkdir(exist_ok=True)
            doc_csv_dir.mkdir(exist_ok=True)
            
            df = pd.read_csv(csv_path)
            
            # Copy to output directory
            csv_file = doc_csv_dir / f"{doc_id}.csv"
            df.to_csv(csv_file, index=False)
            
            # Create Markdown summary
            md_file = doc_md_dir / f"{doc_id}.md"
            
            # Create chunk metadata (CSV files are single page)
            chunk_metadata = self._create_chunk_metadata(
                doc_id, csv_path.name, 1, 
                category, file_hash
            )
            
            md_content = f"""{chunk_metadata}

# {csv_path.name}

## Summary
- Document ID: {doc_id}
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
            
            results["output_md"].append(str(md_file.relative_to(self.output_dir)))
            results["output_csv"].append(str(csv_file.relative_to(self.output_dir)))
            results["status"] = "completed"
            
            doc_logger.info(f"CSV processing complete: {len(df)} rows, {len(df.columns)} columns")
            
        except Exception as e:
            doc_logger.error(f"CSV processing failed: {e}")
            results["status"] = "failed"
        
        # Update index
        self.index_data[doc_id] = results
        self._save_index()
        
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
                return {"filename": file_path.name, "status": "failed", "error": "Unsupported file type"}
                
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return {"filename": file_path.name, "status": "failed", "error": str(e)}
    
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
            return {"total_files": 0, "successful": 0, "failed": 0, "skipped": 0, "processing_time": 0}
        
        results = []
        skipped_files = []
        
        for file_path in files:
            doc_id = self._get_doc_id(file_path)
            
            # Quick duplicate check before processing
            if self._check_duplicate(file_path, doc_id):
                self.logger.info(f"Skipping duplicate: {file_path.name}")
                skipped_files.append(file_path.name)
                continue
                
            result = self.process_file(file_path)
            results.append(result)
        
        # Calculate statistics
        end_time = time.time()
        processing_time = end_time - start_time
        
        successful = sum(1 for r in results if r.get("status") == "completed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        total_pages = sum(r.get("pages", 0) for r in results)
        total_md = sum(len(r.get("output_md", [])) for r in results)
        total_csv = sum(len(r.get("output_csv", [])) for r in results)
        
        summary = {
            "total_files": len(files),
            "processed": len(results),
            "successful": successful,
            "failed": failed,
            "skipped": len(skipped_files),
            "total_pages": total_pages,
            "total_md_files": total_md,
            "total_csv_files": total_csv,
            "processing_time": processing_time
        }
        
        self.logger.info("=" * 60)
        self.logger.info("EXTRACTION COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Total files discovered: {summary['total_files']}")
        self.logger.info(f"Files processed: {summary['processed']}")
        self.logger.info(f"Successful: {summary['successful']}")
        self.logger.info(f"Failed: {summary['failed']}")
        self.logger.info(f"Skipped (duplicates): {summary['skipped']}")
        self.logger.info(f"Total pages/sheets extracted: {summary['total_pages']}")
        self.logger.info(f"Total MD files created: {summary['total_md_files']}")
        self.logger.info(f"Total CSV files created: {summary['total_csv_files']}")
        self.logger.info(f"Processing time: {summary['processing_time']:.2f} seconds")
        self.logger.info(f"Index file: {self.index_file}")
        
        # Print summary table
        self._print_summary_table(results, skipped_files)
        
        return summary
    
    def _print_summary_table(self, results: List[Dict], skipped_files: List[str]):
        """Print a formatted summary table of processing results."""
        # Collect all processed files and their statuses
        table_data = []
        
        # Add processed files
        for result in results:
            filename = result.get("filename", "Unknown")
            status = result.get("status", "unknown")
            
            if status == "completed":
                status_symbol = "✅ OK"
            elif status == "failed":
                status_symbol = "❌ Failed"
            else:
                status_symbol = "❓ Unknown"
                
            table_data.append((filename, status_symbol))
        
        # Add skipped files
        for filename in skipped_files:
            table_data.append((filename, "⚠️ Skipped"))
        
        if not table_data:
            return
            
        # Print table
        print("\n" + "=" * 50)
        print("| {:<30} | {:<12} |".format("File", "Status"))
        print("|" + "-" * 32 + "|" + "-" * 14 + "|")
        
        for filename, status in table_data:
            # Truncate long filenames
            display_name = filename[:28] + ".." if len(filename) > 30 else filename
            print("| {:<30} | {:<12} |".format(display_name, status))
            
        print("=" * 50)


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
        description="Enhanced Document Extraction Tool with Batching and Metadata Tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_docs.py                    # Extract all files from docs/
  python extract_docs.py --input my_docs   # Extract from custom input directory
  python extract_docs.py --verbose         # Enable verbose logging

Features:
  - Document-level batching with per-document subdirectories
  - SHA-256 hash-based duplicate detection
  - Master index.json for metadata tracking
  - Per-document logging
  - Preserves all existing extraction capabilities
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
    logger.info("Starting enhanced document extraction")
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
    
    if summary["successful"] == 0 and summary["skipped"] == 0:
        logger.warning("No files were successfully processed.")
        logger.info(f"Check that you have supported files (.pdf, .xlsx, .csv) in {args.input}")
    
    return 0 if summary["successful"] > 0 or summary["skipped"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main()) 