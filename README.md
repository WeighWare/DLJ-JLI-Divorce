# Document Extraction Script

A comprehensive Python script for extracting and organizing divorce-related documents from mixed file formats (PDF, Excel, CSV) into clean Markdown and CSV files suitable for analysis.

## Features

- **PDF Processing**: Handles both text-based and scanned PDFs with automatic OCR
- **Table Extraction**: Extracts tables using pdfplumber and camelot-py
- **Excel Support**: Processes all sheets in Excel files
- **CSV Handling**: Preserves and organizes CSV data
- **Clean Output**: Generates organized Markdown with YAML front-matter
- **Security**: Sanitizes filenames and prevents path traversal
- **Logging**: Comprehensive logging with timestamps
- **Performance**: Optional multi-processing support

## Installation

### Prerequisites

1. **Python 3.8+**
2. **Tesseract OCR** (required for scanned PDF processing)

#### Installing Tesseract OCR

**Windows:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH environment variable

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr
```

**Linux (CentOS/RHEL):**
```bash
sudo yum install tesseract
```

### Python Dependencies

1. **Clone or download the script files**
2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python extract_documents.py --input ./docs --output ./build
```

### Advanced Usage

```bash
python extract_documents.py \
    --input ./docs \
    --output ./build \
    --ocr-lang eng \
    --workers 4 \
    --log-level DEBUG
```

### Command Line Options

- `--input, -i`: Input directory containing source documents (required)
- `--output, -o`: Output directory for extracted files (required)
- `--ocr-lang`: Language for OCR processing (default: eng)
- `--workers, -w`: Number of worker processes (default: 1)
- `--log-level`: Logging level - DEBUG, INFO, WARNING, ERROR (default: INFO)

### Directory Structure

The script creates the following output structure:

```
/build/
├── md/          # Extracted Markdown files
├── csv/         # Extracted CSV tables
└── logs/        # Processing logs
```

## Output Format

### Markdown Files

Each page is saved as a separate Markdown file with YAML front-matter:

```yaml
---
source: "document.pdf#page=1"
extracted_at: "2024-01-15T10:30:00"
has_tables: true
table_files:
  - document_p1_t1.csv
  - document_p1_t2.csv
---

Extracted text content here...
```

### CSV Files

Tables are extracted and saved as CSV files with naming convention:
- `{original_filename}_p{page_number}_t{table_number}.csv`

## Configuration

Copy `env.example` to `.env` and modify settings as needed:

```bash
cp env.example .env
```

Key configuration options:
- `OCR_LANGUAGE`: Language for OCR processing
- `DEFAULT_WORKERS`: Number of worker processes
- `TABLE_DETECTION_CONFIDENCE`: Confidence threshold for table detection
- `MAX_FILENAME_LENGTH`: Maximum filename length

## Supported File Types

- **PDF**: Text-based and scanned documents
- **Excel**: .xlsx and .xls files (all sheets)
- **CSV**: Comma-separated value files

## Processing Details

### PDF Processing

1. **Text Extraction**: Uses pdfplumber for text-based PDFs
2. **OCR Detection**: Automatically detects scanned pages
3. **Table Extraction**: 
   - Primary: pdfplumber table extraction
   - Fallback: camelot-py stream flavor
4. **Text Cleaning**: Removes headers/footers, normalizes whitespace

### Excel Processing

- Processes all sheets in the workbook
- Saves each sheet as a separate CSV file
- Creates Markdown reference files

### CSV Processing

- Copies original CSV to output directory
- Creates Markdown reference file
- Preserves original structure

## Troubleshooting

### Common Issues

1. **Tesseract not found**
   - Install Tesseract OCR (see Installation section)
   - Ensure it's in your system PATH

2. **Missing dependencies**
   - Run: `pip install -r requirements.txt`
   - Check Python version (requires 3.8+)

3. **Permission errors**
   - Ensure write permissions for output directory
   - Check file permissions for input documents

4. **Memory issues with large files**
   - Reduce number of workers: `--workers 1`
   - Process files in smaller batches

### Performance Tips

- Use `--workers` for parallel processing (CPU cores - 1)
- Set `--log-level DEBUG` for detailed processing information
- For large files, process in smaller batches

### OCR Quality

- Ensure good image quality for scanned documents
- Use appropriate OCR language (`--ocr-lang`)
- Consider preprocessing scanned documents for better results

## Security Features

- Filename sanitization to prevent path traversal
- Local processing only (no data upload)
- Input validation and error handling
- Secure file handling practices

## Logging

Logs are saved to `/build/logs/run_YYYYMMDD_HHMMSS.log` with:
- Processing progress
- Error details
- Performance statistics
- File processing results

## Example Workflow

1. **Prepare documents:**
   ```bash
   mkdir docs
   # Copy your PDF, Excel, and CSV files to docs/
   ```

2. **Run extraction:**
   ```bash
   python extract_documents.py --input ./docs --output ./build
   ```

3. **Review results:**
   ```bash
   ls build/md/    # Check extracted Markdown files
   ls build/csv/   # Check extracted CSV tables
   cat build/logs/run_*.log  # Review processing logs
   ```

4. **Use extracted data:**
   - Import CSV files into analysis tools
   - Use Markdown files with ChatGPT or other AI tools
   - Process with data analysis pipelines

## License

This script is provided as-is for document processing purposes. Ensure you have proper authorization to process the documents in your use case. 