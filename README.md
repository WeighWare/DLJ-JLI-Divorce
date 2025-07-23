# Document Extraction Tool

A comprehensive Python tool for extracting content from divorce-related documents. Processes PDFs, Excel files, and CSVs into structured Markdown and CSV outputs.

## Features

- **Multi-format Support**: PDF, Excel (.xlsx), and CSV files
- **Advanced PDF Processing**: Uses MarkItDown, Docling, pdfplumber, and Camelot
- **Per-page Extraction**: Creates individual Markdown files for each PDF page
- **Table Extraction**: Extracts tables to separate CSV files
- **Excel Processing**: Handles all sheets in Excel workbooks
- **Document Categorization**: Automatically tags documents as transcript, financial, legal, or other
- **Chunk Metadata**: Embeds traceability metadata in all Markdown files
- **Duplicate Detection**: SHA-256 hashing prevents reprocessing identical files
- **Summary Reporting**: Visual status table showing processing results
- **Per-document Organization**: Creates subfolders for each document's outputs
- **Vector Embeddings**: Document chunking and embedding with OpenAI API
- **Vector Search**: Semantic search using ChromaDB or FAISS
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
- Automatically categorize documents (financial, legal, transcript, other)
- Create category-organized folders in `build/md/` and `build/csv/`
- Generate per-document processing logs in `build/logs/`
- Create a master `build/index.json` with metadata
- Display a summary table with processing results

### Command Line Options

```bash
python extract_docs.py [options]
```

**Options:**
- `--input, -i <dir>`: Input directory (default: `docs`)
- `--output, -o <dir>`: Output directory (default: `build`)
- `--verbose, -v`: Enable verbose logging
- `--embed`: Enable document chunking and embedding (requires OpenAI API key)
- `--embedding-model <model>`: OpenAI embedding model (default: `text-embedding-3-small`)
- `--vector-db <db>`: Vector database: `chromadb` or `faiss` (default: `chromadb`)
- `--chunk-size <size>`: Text chunk size for embedding (default: `1000`)
- `--chunk-overlap <overlap>`: Overlap between chunks (default: `200`)
- `--search <query>`: Test search query after processing (requires `--embed`)
- `--help`: Show help message

### Examples

```bash
# Extract from custom input directory
python extract_docs.py --input my_documents

# Use custom output directory with verbose logging
python extract_docs.py --input docs --output results --verbose

# Enable document embedding with OpenAI
python extract_docs.py --embed

# Use specific embedding model and vector database
python extract_docs.py --embed --embedding-model text-embedding-3-large --vector-db faiss

# Process and test search functionality
python extract_docs.py --embed --search "financial statements"

# Process specific directory structure
python extract_docs.py -i /path/to/files -o /path/to/output -v
```

### Vector Embeddings and Search

When enabled with `--embed`, the tool provides advanced semantic search capabilities:

```bash
# Basic embedding (requires OPENAI_API_KEY environment variable)
python extract_docs.py --embed

# Customize embedding parameters
python extract_docs.py --embed \
  --embedding-model text-embedding-3-small \
  --vector-db chromadb \
  --chunk-size 1000 \
  --chunk-overlap 200

# Test search after processing
python extract_docs.py --embed --search "custody arrangements"
```

**Requirements for embeddings:**
- OpenAI API key (set `OPENAI_API_KEY` environment variable)
- Internet connection for API calls
- Additional dependencies: `langchain`, `chromadb` or `faiss-cpu`

## Directory Structure

```
project/
├── docs/                    # Input directory
│   ├── document1.pdf
│   ├── spreadsheet.xlsx
│   └── data.csv
├── build/                   # Output directory
│   ├── md/                  # Markdown files (organized by category)
│   │   ├── financial/       # Financial documents
│   │   │   ├── bank_statement_p1.md
│   │   │   ├── bank_statement_p2.md
│   │   │   └── tax_return_Sheet1.md
│   │   ├── legal/           # Legal documents
│   │   │   ├── custody_agreement_p1.md
│   │   │   ├── expert_report_p1.md
│   │   │   └── expert_report_p2.md
│   │   ├── transcript/      # Transcript documents
│   │   │   ├── hearing_transcript_p1.md
│   │   │   └── deposition_transcript_p1.md
│   │   └── other/           # Other documents
│   │       └── misc_document_p1.md
│   ├── csv/                 # CSV files (organized by category)
│   │   ├── financial/       # Financial data
│   │   │   ├── bank_statement_table1.csv
│   │   │   └── tax_return_Sheet1.csv
│   │   ├── legal/           # Legal data
│   │   │   ├── expert_report_table1.csv
│   │   │   └── expert_report_table2.csv
│   │   ├── transcript/      # Transcript data
│   │   └── other/           # Other data
│   ├── vectors/             # Vector database files (when --embed enabled)
│   │   ├── chroma.sqlite3   # ChromaDB database
│   │   └── index.faiss      # FAISS index (if using FAISS)
│   ├── logs/                # Processing logs (per document)
│   │   ├── bank_statement.log
│   │   ├── expert_report.log
│   │   └── hearing_transcript.log
│   └── index.json          # Master metadata index
├── extract_docs.py          # Main extraction script
├── requirements.txt         # Python dependencies
├── env.example             # Environment configuration template
└── README.md               # This file
```

## Output Format

### PDF Processing

For each PDF document, files are organized by category:
- `build/md/<category>/<doc_id>_p1.md` - Page 1 content with metadata
- `build/md/<category>/<doc_id>_p2.md` - Page 2 content with metadata
- `build/csv/<category>/<doc_id>_table1.csv` - Extracted tables (if any)
- `build/logs/<doc_id>.log` - Processing log for this document

### Excel Processing

For each Excel workbook, files are organized by category:
- `build/md/<category>/<doc_id>_Sheet1.md` - Sheet summary with metadata
- `build/csv/<category>/<doc_id>_Sheet1.csv` - Sheet data
- `build/logs/<doc_id>.log` - Processing log for this workbook

### CSV Processing

For each CSV file, files are organized by category:
- `build/md/<category>/<doc_id>.md` - Summary with metadata
- `build/csv/<category>/<doc_id>.csv` - Processed data
- `build/logs/<doc_id>.log` - Processing log for this file

### Category Organization

Documents are automatically categorized and placed in appropriate folders:
- **📝 financial/**: Bank statements, tax returns, financial reports
- **⚖️ legal/**: Legal documents, reports, exhibits, affidavits
- **📄 transcript/**: Court transcripts, depositions, hearing records
- **📁 other/**: All other document types

### Chunk Metadata

All Markdown files include embedded metadata for traceability:

```html
<!--
chunk_id: document1_p1
source: document1.pdf
page: 1
category: legal
hash: a1b2c3d4e5f678...
-->
```

### Master Index

The `build/index.json` file contains metadata for all processed documents:

```json
{
  "expert_report": {
    "doc_id": "expert_report",
    "filename": "expert_report.pdf",
    "hash": "a1b2c3d4e5f678...",
    "type": "pdf",
    "category": "legal",
    "pages": 5,
    "output_md": ["md/legal/expert_report_p1.md", "md/legal/expert_report_p2.md", ...],
    "output_csv": ["csv/legal/expert_report_table1.csv"],
    "log": "logs/expert_report.log",
    "status": "completed",
    "created": "2024-01-15T10:30:00"
  },
  "bank_statement": {
    "doc_id": "bank_statement",
    "filename": "bank_statement.xlsx",
    "hash": "b2c3d4e5f6789a...",
    "type": "excel",
    "category": "financial",
    "pages": 2,
    "output_md": ["md/financial/bank_statement_Sheet1.md", "md/financial/bank_statement_Sheet2.md"],
    "output_csv": ["csv/financial/bank_statement_Sheet1.csv", "csv/financial/bank_statement_Sheet2.csv"],
    "log": "logs/bank_statement.log",
    "status": "completed",
    "created": "2024-01-15T10:35:00"
  }
}
```

## Processing Methods

The tool uses multiple extraction methods with intelligent fallbacks:

1. **MarkItDown**: Primary PDF content extraction with formatting preservation
2. **Docling**: Advanced document understanding and structure extraction
3. **Camelot**: Table extraction from PDFs using computer vision
4. **pdfplumber**: Fallback text extraction for challenging PDFs
5. **pandas**: Excel and CSV processing with data type inference

## Document Categorization

The tool automatically categorizes documents based on filename patterns:

- **📝 Transcript**: Files containing "transcript"
- **💰 Financial**: Files containing "bank" or "statement"
- **⚖️ Legal**: Files containing "report", "exhibit", or "affidavit"
- **📄 Other**: All other files

Categories are included in the index.json metadata and chunk metadata for enhanced organization and searchability.

## Processing Results

After processing completes, the tool displays a summary table:

```
==================================================
| File                         | Status     |
|------------------------------|------------|
| expert_report.pdf            | ✅ OK       |
| bank_statement.xlsx          | ✅ OK       |
| duplicate_file.pdf           | ⚠️ Skipped  |
| corrupted_data.csv           | ❌ Failed   |
==================================================
```

Status indicators:
- **✅ OK**: Successfully processed
- **❌ Failed**: Processing encountered errors  
- **⚠️ Skipped**: Duplicate file (already processed)
- **❓ Unknown**: Unexpected status

## Vector Search Capabilities

When embeddings are enabled, the tool creates a searchable vector database of your documents:

### Automatic Processing
- **Document Chunking**: Splits documents into manageable chunks (default: 1000 characters with 200 overlap)
- **Vector Embeddings**: Creates semantic embeddings using OpenAI's API
- **Vector Storage**: Stores embeddings in ChromaDB (persistent) or FAISS (file-based)
- **Metadata Preservation**: Maintains document categories, page numbers, and source information

### Search Features
- **Semantic Search**: Find content by meaning, not just exact text matches
- **Ranked Results**: Results sorted by similarity score
- **Rich Metadata**: Each result includes source file, page number, category, and content preview
- **Fast Retrieval**: Optimized vector search for large document collections

### Example Search Results
```
Testing search with query: 'financial statements'

Search results:
  1. Score: 0.85
     Source: md/financial/bank_statement_p1.md
     Category: financial
     Content preview: The monthly bank statement shows deposits totaling $15,000...

  2. Score: 0.82
     Source: md/legal/expert_report_p5.md
     Category: legal
     Content preview: Analysis of financial records indicates significant...
```

## GitHub Actions Integration

The repository includes an enhanced GitHub Actions workflow for automated document processing with advanced features:

### Manual Trigger

1. Go to your repository's **Actions** tab
2. Select **"Document Extraction Workflow with Embeddings"**
3. Click **"Run workflow"**
4. Configure options:
   - **Input directory**: Source documents location (default: `docs`)
   - **Output directory**: Results location (default: `build`)
   - **Enable embeddings**: ✅ Enable vector search capabilities
   - **Embedding model**: Choose OpenAI model (`text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`)
   - **Vector database**: Choose storage (`chromadb`, `faiss`)
   - **Chunk size/overlap**: Configure text chunking (defaults: 1000/200)
   - **Search query**: Test search functionality (optional)
   - **Verbose logging**: Enable detailed output
5. Click **"Run workflow"**

### Workflow Features

- **🚀 One-Click Processing**: Automated document extraction and categorization
- **🧠 Vector Embeddings**: Optional semantic search capabilities with OpenAI
- **📂 Category Organization**: Automatic sorting by financial, legal, transcript, other
- **📦 Multiple Artifacts**: Organized downloads for different output types
- **🔍 Smart Detection**: Validates OpenAI API key and counts documents by type
- **📊 Enhanced Reporting**: Category breakdowns and processing statistics

### Setup Requirements

#### For Basic Processing (No API Key Needed):
- Documents in `docs/` folder
- Commit and push to trigger workflow

#### For Embeddings & Search (Requires Setup):
1. **Get OpenAI API Key**: [platform.openai.com](https://platform.openai.com)
2. **Add as Repository Secret**:
   - Go to repo **Settings** → **Secrets and variables** → **Actions**
   - Click **"New repository secret"**
   - Name: `OPENAI_API_KEY`
   - Value: Your actual API key
   - Click **"Add secret"**

### Workflow Artifacts

After processing, download these artifacts:

1. **📁 document-extraction-results.zip**:
   ```
   md/
   ├── financial/          # Bank statements, tax returns
   ├── legal/              # Reports, exhibits, affidavits  
   ├── transcript/         # Court transcripts, depositions
   └── other/              # Other document types
   csv/
   ├── financial/          # Financial data tables
   ├── legal/              # Legal document tables
   └── transcript/         # Transcript data
   index.json              # Master metadata file
   ```

2. **🧠 vector-database.zip** (if embeddings enabled):
   ```
   vectors/
   ├── chroma.sqlite3      # ChromaDB database
   └── index.faiss         # FAISS index files
   ```

3. **📋 extraction-logs.zip**:
   ```
   logs/
   ├── document1.log       # Per-document processing logs
   └── document2.log
   ```

### Processing Workflow

1. **📥 Document Detection**: Scans for PDF, Excel, CSV files
2. **🏷️ Auto-Categorization**: Classifies by filename patterns
3. **📄 Content Extraction**: Processes with multiple tools (MarkItDown, Docling, etc.)
4. **🗂️ Category Organization**: Places files in appropriate category folders
5. **🧠 Vector Embeddings** (optional): Creates searchable database
6. **📦 Artifact Creation**: Packages results for download

### Example Workflow Run

```
🔍 Found 3 documents to process
📊 Results by Category:
  📂 financial: 2 MD, 1 CSV
  📂 legal: 3 MD, 2 CSV
🧠 Vector database: 1.2MB (ChromaDB)
✅ Processing complete! Download artifacts above.
```

- Creates downloadable artifacts with results
- Includes detailed logs and processing summary

## Configuration

### Environment Variables

Set these in your `.env` file or environment:

- `INPUT_DIR`: Input directory path (default: `docs`)
- `OUTPUT_DIR`: Output directory path (default: `build`)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: `INFO`)
- `OPENAI_API_KEY`: OpenAI API key for embeddings (required for `--embed`)
- `EMBEDDING_MODEL`: OpenAI embedding model (default: `text-embedding-3-small`)
- `VECTOR_DB`: Vector database type - chromadb or faiss (default: `chromadb`)
- `CHUNK_SIZE`: Text chunk size for embedding (default: `1000`)
- `CHUNK_OVERLAP`: Overlap between text chunks (default: `200`)
- `ENABLE_EMBEDDINGS`: Enable embeddings by default - true or false (default: `false`)

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

5. **Embedding Issues**
   ```bash
   # Missing OpenAI API key
   export OPENAI_API_KEY=your_api_key_here
   
   # Install embedding dependencies
   pip install langchain langchain-openai chromadb faiss-cpu
   
   # Check embedding status in logs
   python extract_docs.py --embed --verbose
   ```

### Performance Tips

- Process files in smaller batches for large datasets
- Use `--verbose` for detailed progress information
- Check available disk space for output files
- Consider file sizes when processing many large PDFs

## Supported File Types

| Extension | Processing Method | Output | Auto-Categorization | Vector Embeddings |
|-----------|------------------|---------|-------------------|-------------------|
| `.pdf` | MarkItDown, Docling, pdfplumber, Camelot | Per-page MD + tables CSV | ✅ Based on filename | ✅ With --embed |
| `.xlsx` | pandas | Per-sheet MD + CSV | ✅ Based on filename | ✅ With --embed |
| `.csv` | pandas | Summary MD + processed CSV | ✅ Based on filename | ✅ With --embed |

All outputs include:
- **Chunk metadata** embedded in Markdown files
- **Document categorization** (transcript/financial/legal/other)
- **Duplicate detection** via SHA-256 hashing
- **Per-document organization** in subfolders
- **Vector embeddings** (when enabled) for semantic search

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