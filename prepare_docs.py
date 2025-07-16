#!/usr/bin/env python3
"""
Prepare divorce documents for extraction.

This script restructures the scattered divorce documents into a clean docs directory,
handling duplicates and nested folders.
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Set
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocPreparer:
    """Prepare documents for extraction by restructuring and deduplicating."""
    
    def __init__(self, source_dir: str = ".", docs_dir: str = "./docs"):
        self.source_dir = Path(source_dir)
        self.docs_dir = Path(docs_dir)
        self.file_hashes: Dict[str, str] = {}  # hash -> original_path
        self.duplicates: List[tuple] = []
        self.processed_files = 0
        self.skipped_files = 0
        
        # Create docs directory
        self.docs_dir.mkdir(exist_ok=True)
        
        # Supported file extensions
        self.supported_extensions = {'.pdf', '.xlsx', '.xls', '.csv'}
    
    def get_file_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of file content."""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Could not hash {filepath}: {e}")
            return ""
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe copying."""
        # Remove or replace dangerous characters
        sanitized = filename.replace('<', '_').replace('>', '_').replace(':', '_')
        sanitized = sanitized.replace('"', '_').replace('|', '_').replace('?', '_').replace('*', '_')
        # Limit length
        if len(sanitized) > 200:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:200-len(ext)] + ext
        return sanitized
    
    def copy_file_safely(self, source_path: Path, target_filename: str) -> bool:
        """Copy file to docs directory with duplicate handling."""
        try:
            # Skip if file is too small (likely empty/corrupted)
            if source_path.stat().st_size < 100:  # Less than 100 bytes
                logger.warning(f"Skipping small file: {source_path}")
                self.skipped_files += 1
                return False
            
            # Calculate hash
            file_hash = self.get_file_hash(source_path)
            if not file_hash:
                return False
            
            # Check for duplicates
            if file_hash in self.file_hashes:
                original_path = self.file_hashes[file_hash]
                self.duplicates.append((str(source_path), original_path))
                logger.info(f"Duplicate found: {source_path} -> {original_path}")
                self.skipped_files += 1
                return False
            
            # Copy file
            target_path = self.docs_dir / target_filename
            shutil.copy2(source_path, target_path)
            
            # Store hash
            self.file_hashes[file_hash] = str(source_path)
            self.processed_files += 1
            
            logger.info(f"Copied: {source_path} -> {target_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying {source_path}: {e}")
            return False
    
    def process_directory(self, directory: Path, prefix: str = "") -> None:
        """Recursively process directory and copy supported files."""
        try:
            for item in directory.iterdir():
                if item.is_file():
                    # Check if it's a supported file type
                    if item.suffix.lower() in self.supported_extensions:
                        # Create a descriptive filename
                        if prefix:
                            filename = f"{prefix}_{item.name}"
                        else:
                            filename = item.name
                        
                        # Sanitize filename
                        safe_filename = self.sanitize_filename(filename)
                        
                        # Handle potential filename conflicts
                        counter = 1
                        original_safe_filename = safe_filename
                        while (self.docs_dir / safe_filename).exists():
                            name, ext = os.path.splitext(original_safe_filename)
                            safe_filename = f"{name}_{counter}{ext}"
                            counter += 1
                        
                        self.copy_file_safely(item, safe_filename)
                
                elif item.is_dir():
                    # Skip certain directories
                    if item.name in {'.git', '__pycache__', 'build', 'docs', 'venv', 'env'}:
                        continue
                    
                    # Process subdirectory with prefix
                    sub_prefix = f"{prefix}_{item.name}" if prefix else item.name
                    self.process_directory(item, sub_prefix)
                    
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")
    
    def run(self) -> None:
        """Run the document preparation process."""
        logger.info(f"Starting document preparation from {self.source_dir}")
        logger.info(f"Output directory: {self.docs_dir}")
        
        # Process the source directory
        self.process_directory(self.source_dir)
        
        # Summary
        logger.info("=" * 50)
        logger.info("DOCUMENT PREPARATION COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Files processed: {self.processed_files}")
        logger.info(f"Files skipped (duplicates/empty): {self.skipped_files}")
        logger.info(f"Duplicates found: {len(self.duplicates)}")
        logger.info(f"Total files in docs directory: {len(list(self.docs_dir.glob('*')))}")
        
        if self.duplicates:
            logger.info("\nDuplicate files:")
            for duplicate, original in self.duplicates[:10]:  # Show first 10
                logger.info(f"  {duplicate} -> {original}")
            if len(self.duplicates) > 10:
                logger.info(f"  ... and {len(self.duplicates) - 10} more")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare divorce documents for extraction")
    parser.add_argument(
        "--source", "-s",
        default=".",
        help="Source directory (default: current directory)"
    )
    parser.add_argument(
        "--docs", "-d",
        default="./docs",
        help="Output docs directory (default: ./docs)"
    )
    
    args = parser.parse_args()
    
    # Create preparer and run
    preparer = DocPreparer(source_dir=args.source, docs_dir=args.docs)
    preparer.run()


if __name__ == "__main__":
    main() 