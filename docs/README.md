# Documents Directory

Place your source documents here for processing.

## Supported File Types

- **PDF files** (`.pdf`) - Reports, contracts, court documents
- **Excel files** (`.xlsx`) - Spreadsheets, financial data, asset lists
- **CSV files** (`.csv`) - Data exports, tables

## Usage

1. **Add your documents** to this directory
2. **Run the extraction tool**:
   ```bash
   python extract_docs.py
   ```
3. **Find processed files** in the `build/` directory:
   - `build/md/` - Markdown files (per page/sheet)
   - `build/csv/` - CSV files (tables and data)
   - `build/logs/` - Processing logs

## Examples

After adding documents, your structure might look like:

```
docs/
├── divorce_agreement.pdf
├── asset_valuation.xlsx
├── property_list.csv
└── court_transcript.pdf
```

The tool will process these and create outputs like:

```
build/
├── md/
│   ├── divorce_agreement_p1.md
│   ├── divorce_agreement_p2.md
│   ├── asset_valuation_Sheet1.md
│   ├── property_list.md
│   └── court_transcript_p1.md
├── csv/
│   ├── divorce_agreement_p1_table0.csv
│   ├── asset_valuation_Sheet1.csv
│   └── property_list.csv
└── logs/
    └── extraction_20240722_123456.log
```

## Tips

- **File names**: Use descriptive names without special characters
- **File size**: Large files may take longer to process
- **Organization**: You can create subdirectories for organization
- **Formats**: The tool handles both text-based and scanned PDFs 