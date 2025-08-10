#!/usr/bin/env python3
"""
Test Cover Extraction Script

This script tests the cover extraction functionality from EPUB files.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from epub_parser import EpubParser

def test_cover_extraction():
    """Test cover extraction from EPUB files"""
    parser = EpubParser()
    
    # Find some EPUB files to test
    data_dir = Path(__file__).parent.parent / 'data' / 'full_library'
    epub_files = list(data_dir.rglob('*.epub'))
    
    if not epub_files:
        print("No EPUB files found for testing")
        return
    
    print(f"Found {len(epub_files)} EPUB files for testing")
    print("=" * 50)
    
    # Test first few files
    for i, epub_file in enumerate(epub_files[:5]):
        print(f"\nTesting file {i+1}: {epub_file.name}")
        print("-" * 30)
        
        try:
            # Parse book
            metadata, content, cover = parser.parse_book(str(epub_file))
            
            print(f"Title: {metadata.title}")
            print(f"Authors: {metadata.authors}")
            
            if cover:
                print(f"✓ Cover found!")
                print(f"  - MIME type: {cover.mime_type}")
                print(f"  - File name: {cover.file_name}")
                print(f"  - Base64 length: {len(cover.base64_data)}")
            else:
                print("✗ No cover found")
                
        except Exception as e:
            print(f"Error processing {epub_file.name}: {e}")
    
    print("\n" + "=" * 50)
    print("Cover extraction test completed!")

if __name__ == '__main__':
    test_cover_extraction()
