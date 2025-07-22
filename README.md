# Document Extraction Tool

A comprehensive Python tool for extracting content from divorce-related documents. Processes PDFs, Excel files, and CSVs into structured Markdown and CSV outputs.

## Features

- **Multi-format Support**: PDF, Excel (.xlsx), and CSV files
- **Advanced PDF Processing**: Uses MarkItDown, Docling, pdfplumber, and Camelot
- **Per-page Extraction**: Creates individual Markdown files for each PDF page
- **Table Extraction**: Extracts tables to separate CSV files
- **Excel Processing**: Handles all sheets in Excel workbooks
- **Automated Workflow**: GitHub Actions support for CI/CD processing

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Optional: Environment Configuration

Copy the example environment file and customize:

```bash
cp env.example .env
# Edit .env with your preferred settings
```

## Usage

### Basic Usage

Place your documents in the `docs/` directory and run:

```bash
python extract_docs.py
```

This will:
- Process all PDF, Excel, and CSV files in `docs/`
- Create Markdown files in `build/md/`
- Create CSV files in `build/csv/`
- Generate processing logs in `build/logs/`

### Command Line Options

```bash
python extract_docs.py [options]
```

**Options:**
- `--input, -i <dir>`: Input directory (default: `docs`)
- `--output, -o <dir>`: Output directory (default: `build`)
- `--verbose, -v`: Enable verbose logging
- `--help`: Show help message

### Examples

```bash
# Extract from custom input directory
python extract_docs.py --input my_documents

# Use custom output directory with verbose logging
python extract_docs.py --input docs --output results --verbose

# Process specific directory structure
python extract_docs.py -i /path/to/files -o /path/to/output -v
```

## Directory Structure

```
project/
├── docs/                    # Input directory
│   ├── document1.pdf
│   ├── spreadsheet.xlsx
│   └── data.csv
├── build/                   # Output directory
│   ├── md/                  # Markdown files (per page/sheet)
│   ├── csv/                 # CSV files (tables and data)
│   └── logs/                # Processing logs
├── extract_docs.py          # Main extraction script
├── requirements.txt         # Python dependencies
├── env.example             # Environment configuration template
└── README.md               # This file
```

## Output Format

### PDF Processing

For each PDF page, creates:
- `build/md/<filename>_p<page>.md` - Markdown content
- `build/csv/<filename>_p<page>_table<idx>.csv` - Extracted tables (if any)

### Excel Processing

For each Excel sheet, creates:
- `build/md/<filename>_<sheet>.md` - Markdown summary
- `build/csv/<filename>_<sheet>.csv` - Sheet data

### CSV Processing

For each CSV file, creates:
- `build/md/<filename>.md` - Markdown summary
- `build/csv/<filename>.csv` - Processed data

## Processing Methods

The tool uses multiple extraction methods with intelligent fallbacks:

1. **MarkItDown**: Primary PDF content extraction with formatting preservation
2. **Docling**: Advanced document understanding and structure extraction
3. **Camelot**: Table extraction from PDFs using computer vision
4. **pdfplumber**: Fallback text extraction for challenging PDFs
5. **pandas**: Excel and CSV processing with data type inference

## GitHub Actions Integration

The repository includes a GitHub Actions workflow for automated processing:

### Manual Trigger

1. Go to your repository's Actions tab
2. Select "Document Extraction Workflow"
3. Click "Run workflow"
4. The workflow will process files and create artifacts

### Workflow Features

- Runs on `workflow_dispatch` (manual trigger)
- Processes documents in the repository
- Creates downloadable artifacts with results
- Includes detailed logs and processing summary

## Configuration

### Environment Variables

Set these in your `.env` file or environment:

- `INPUT_DIR`: Input directory path (default: `docs`)
- `OUTPUT_DIR`: Output directory path (default: `build`)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: `INFO`)

### Processing Behavior

The tool automatically:
- Detects file types by extension
- Creates output directories as needed
- Handles duplicate filenames safely
- Provides detailed logging of all operations
- Generates processing statistics

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Input Directory Not Found**
   - The tool will create `docs/` if it doesn't exist
   - Place your files in the input directory

3. **Processing Failures**
   - Check logs in `build/logs/`
   - Ensure files are not corrupted
   - Verify file permissions

4. **Library Installation Issues**
   ```bash
   # For Linux/Mac users with camelot issues:
   sudo apt-get install ghostscript
   
   # For Windows users:
   # Download and install Ghostscript from: 
   # https://www.ghostscript.com/download/gsdnld.html
   ```

### Performance Tips

- Process files in smaller batches for large datasets
- Use `--verbose` for detailed progress information
- Check available disk space for output files
- Consider file sizes when processing many large PDFs

## Supported File Types

| Extension | Processing Method | Output |
|-----------|------------------|---------|
| `.pdf` | MarkItDown, Docling, pdfplumber, Camelot | Per-page MD + tables CSV |
| `.xlsx` | pandas | Per-sheet MD + CSV |
| `.csv` | pandas | Summary MD + processed CSV |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with sample documents
5. Submit a pull request

## License

This project is provided as-is for document processing purposes. Ensure you have proper authorization to process the documents in your use case.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs in `build/logs/`
3. Create an issue with sample files and error messages 