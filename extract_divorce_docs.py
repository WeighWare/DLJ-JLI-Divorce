#!/usr/bin/env python3
"""
Robust script to extract and organize divorce-related documents (PDFs, Excel, CSVs) into Markdown and CSV for further analysis.
Supports OCR fallback, forced OCR, parallelization, logging, and CLI options.
"""
import os
import sys
import argparse
import logging
import multiprocessing
from pathlib import Path
from typing import List, Optional

# PDF and OCR imports
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import csv
import shutil

# Table extraction
import camelot
import tabula

# Excel/CSV
import openpyxl
import xlrd

# For progress
from tqdm import tqdm

# --- CONFIG ---
DEFAULT_OCR_LANG = "eng"
DEFAULT_OCR_THRESHOLD = 50  # percent of non-extractable text to trigger OCR
DEFAULT_WORKERS = max(1, multiprocessing.cpu_count() - 1)

# --- LOGGING ---
def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# --- UTILS ---
def is_pdf(file: Path) -> bool:
    return file.suffix.lower() == ".pdf"

def is_excel(file: Path) -> bool:
    return file.suffix.lower() in {".xls", ".xlsx"}

def is_csv(file: Path) -> bool:
    return file.suffix.lower() == ".csv"

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

# --- OCR ---
def set_tesseract_path():
    # Try to set tesseract path from environment or common install locations
    tesseract_path = os.environ.get("TESSERACT_PATH")
    if tesseract_path and Path(tesseract_path).exists():
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        return
    # Windows common locations
    for p in [
        r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"
    ]:
        if Path(p).exists():
            pytesseract.pytesseract.tesseract_cmd = p
            return
    # Otherwise, rely on PATH
    pass

set_tesseract_path()

# --- PDF Extraction ---
def extract_text_from_pdf(pdf_path: Path) -> List[str]:
    doc = fitz.open(str(pdf_path))
    return [page.get_text("text") for page in doc]

def percent_empty_text(pages: List[str]) -> float:
    empty = sum(1 for t in pages if not t.strip())
    return 100.0 * empty / len(pages) if pages else 0.0

def ocr_pdf(pdf_path: Path, lang: str, pages: Optional[List[int]] = None) -> List[str]:
    images = convert_from_path(str(pdf_path), first_page=(pages[0]+1 if pages else None), last_page=(pages[-1]+1 if pages else None))
    texts = []
    for img in images:
        text = pytesseract.image_to_string(img, lang=lang)
        texts.append(text)
    return texts

# --- Table Extraction ---
def extract_tables_from_pdf(pdf_path: Path, pages: str = "all") -> List[pd.DataFrame]:
    try:
        tables = camelot.read_pdf(str(pdf_path), pages=pages, flavor='stream')
        return [t.df for t in tables]
    except Exception as e:
        logging.warning(f"Camelot failed: {e}, trying tabula...")
        try:
            tables = tabula.read_pdf(str(pdf_path), pages=pages, multiple_tables=True)
            return tables
        except Exception as e2:
            logging.error(f"Tabula also failed: {e2}")
            return []

# --- Excel/CSV Extraction ---
def extract_from_excel(file: Path) -> List[pd.DataFrame]:
    try:
        return pd.read_excel(file, sheet_name=None).values()
    except Exception as e:
        logging.error(f"Excel extraction failed: {e}")
        return []

def extract_from_csv(file: Path) -> List[pd.DataFrame]:
    try:
        return [pd.read_csv(file)]
    except Exception as e:
        logging.error(f"CSV extraction failed: {e}")
        return []

# --- Main Extraction Logic ---
def process_file(
    file: Path,
    output_dir: Path,
    ocr_lang: str,
    ocr_threshold: float,
    force_ocr: Optional[str],
    log_level: str
):
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    result = {
        "file": str(file),
        "pages": 0,
        "ocr_pages": 0,
        "tables": 0,
        "errors": 0
    }
    try:
        if is_pdf(file):
            doc = fitz.open(str(file))
            n_pages = doc.page_count
            text_pages = extract_text_from_pdf(file)
            empty_pct = percent_empty_text(text_pages)
            ocr_pages = []
            # Determine which pages to OCR
            if force_ocr:
                if force_ocr.lower() == "all":
                    ocr_pages = list(range(n_pages))
                else:
                    # e.g. "MyFile.pdf:1,3,5"
                    try:
                        ocr_pages = [int(x)-1 for x in force_ocr.split(",") if x.strip().isdigit()]
                    except Exception:
                        ocr_pages = []
            elif empty_pct >= ocr_threshold:
                ocr_pages = [i for i, t in enumerate(text_pages) if not t.strip()]
            # OCR as needed
            if ocr_pages:
                ocr_texts = ocr_pdf(file, ocr_lang, ocr_pages)
                for idx, page_idx in enumerate(ocr_pages):
                    text_pages[page_idx] = ocr_texts[idx]
                result["ocr_pages"] = len(ocr_pages)
            # Save text to Markdown
            md_path = output_dir / (file.stem + ".md")
            with open(md_path, "w", encoding="utf-8") as f:
                for i, text in enumerate(text_pages):
                    f.write(f"\n\n# Page {i+1}\n\n{text}\n")
            # Extract tables
            tables = extract_tables_from_pdf(file)
            result["tables"] = len(tables)
            for i, table in enumerate(tables):
                table_path = output_dir / f"{file.stem}_table_{i+1}.csv"
                table.to_csv(table_path, index=False)
            result["pages"] = n_pages
        elif is_excel(file):
            dfs = extract_from_excel(file)
            for i, df in enumerate(dfs):
                df.to_csv(output_dir / f"{file.stem}_sheet_{i+1}.csv", index=False)
            result["tables"] = len(dfs)
        elif is_csv(file):
            dfs = extract_from_csv(file)
            for i, df in enumerate(dfs):
                df.to_csv(output_dir / f"{file.stem}_csv_{i+1}.csv", index=False)
            result["tables"] = len(dfs)
        else:
            logging.warning(f"Unsupported file type: {file}")
            result["errors"] = 1
    except Exception as e:
        logging.error(f"Error processing {file}: {e}")
        result["errors"] = 1
    return result

# --- CLI ---
def main():
    parser = argparse.ArgumentParser(description="Extract and organize divorce-related documents.")
    parser.add_argument("--input", required=True, help="Input directory containing files.")
    parser.add_argument("--output", required=True, help="Output directory for extracted data.")
    parser.add_argument("--ocr-lang", default=DEFAULT_OCR_LANG, help="OCR language (default: eng)")
    parser.add_argument("--ocr-threshold", type=float, default=DEFAULT_OCR_THRESHOLD, help="Percent of empty pages to trigger OCR fallback (default: 50)")
    parser.add_argument("--force-ocr", nargs="?", const="all", help="Force OCR on all or specific pages/files (e.g. --force-ocr or --force-ocr 1,3,5)")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Number of parallel workers (default: cpu_count-1)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")
    args = parser.parse_args()

    setup_logging(args.log_level)
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    ensure_dir(output_dir)

    files = [f for f in input_dir.iterdir() if f.is_file() and (is_pdf(f) or is_excel(f) or is_csv(f))]
    logging.info(f"Found {len(files)} files to process.")

    # Parallel processing
    with multiprocessing.Pool(args.workers) as pool:
        results = list(tqdm(pool.imap_unordered(
            lambda f: process_file(
                f,
                output_dir,
                args.ocr_lang,
                args.ocr_threshold,
                args.force_ocr,
                args.log_level
            ),
            files
        ), total=len(files)))

    # Summary
    total_pages = sum(r.get("pages", 0) for r in results)
    total_ocr = sum(r.get("ocr_pages", 0) for r in results)
    total_tables = sum(r.get("tables", 0) for r in results)
    total_errors = sum(r.get("errors", 0) for r in results)
    logging.info(f"Processed {len(files)} files: {total_pages} pages, {total_tables} tables, {total_ocr} OCR pages, {total_errors} errors.")

if __name__ == "__main__":
    main() 