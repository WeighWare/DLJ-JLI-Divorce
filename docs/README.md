# Documents Directory

Place your source documents here for processing with automatic categorization and optional vector search capabilities.

## Supported File Types

- **PDF files** (`.pdf`) - Reports, contracts, court documents, transcripts
- **Excel files** (`.xlsx`) - Spreadsheets, financial data, asset lists
- **CSV files** (`.csv`) - Data exports, tables, financial records

## Automatic Categorization

The tool automatically organizes your documents by type:

- **💰 financial/**: Files containing "bank", "statement", "tax" → Bank statements, financial reports
- **⚖️ legal/**: Files containing "report", "exhibit", "affidavit" → Legal documents, court filings
- **📄 transcript/**: Files containing "transcript" → Court transcripts, depositions
- **📁 other/**: All other document types

## Usage

### Basic Processing
```bash
# Process all documents with category organization
python extract_docs.py
```

### With Vector Embeddings (requires OpenAI API key)
```bash
# Enable semantic search capabilities
python extract_docs.py --embed

# Advanced configuration
python extract_docs.py --embed \
  --embedding-model text-embedding-3-large \
  --vector-db faiss \
  --search "financial statements"
```

### Via GitHub Actions
1. Add documents to this folder
2. Commit and push changes
3. Go to **Actions** → **"Document Extraction Workflow with Embeddings"**
4. Click **"Run workflow"** with desired options

## Example Input/Output

### Input Structure
```
docs/
├── bank_statement_2024.pdf        # → financial/
├── custody_agreement.pdf           # → legal/
├── expert_report_final.pdf         # → legal/
├── hearing_transcript.pdf          # → transcript/
└── asset_valuation.xlsx           # → financial/
```

### Output Structure (Category-Based)
```
build/
├── md/                             # Markdown files by category
│   ├── financial/
│   │   ├── bank_statement_2024_p1.md
│   │   ├── bank_statement_2024_p2.md
│   │   └── asset_valuation_Sheet1.md
│   ├── legal/
│   │   ├── custody_agreement_p1.md
│   │   ├── expert_report_final_p1.md
│   │   └── expert_report_final_p2.md
│   ├── transcript/
│   │   └── hearing_transcript_p1.md
│   └── other/
├── csv/                            # CSV data by category
│   ├── financial/
│   │   ├── bank_statement_2024_table1.csv
│   │   └── asset_valuation_Sheet1.csv
│   ├── legal/
│   │   └── expert_report_final_table1.csv
│   └── transcript/
├── vectors/                        # Vector database (if --embed enabled)
│   ├── chroma.sqlite3
│   └── index.faiss
├── logs/                          # Processing logs per document
│   ├── bank_statement_2024.log
│   ├── custody_agreement.log
│   └── expert_report_final.log
└── index.json                    # Master metadata index
```

## Advanced Features

### Vector Search (with --embed)
- **Semantic queries**: Find content by meaning, not just keywords
- **Cross-document search**: Search across all processed documents
- **Rich metadata**: Results include source, page, category, similarity scores

### Metadata Tracking
- **SHA-256 hashing**: Prevents duplicate processing
- **Category tagging**: Automatic document classification  
- **Chunk metadata**: Embedded traceability in all files
- **Master index**: Complete processing history in `index.json`

## Tips

- **File names**: Use descriptive names without special characters
- **Organization**: Documents automatically categorized, no manual sorting needed
- **Large files**: Processing time scales with document size and page count
- **Embeddings**: Requires OpenAI API key but enables powerful search capabilities
- **GitHub Actions**: Easiest way to process documents without local setup
