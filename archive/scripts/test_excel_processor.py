#!/usr/bin/env python3
"""
Test script for Excel processor functionality.
Creates a sample Excel file and tests the processing pipeline.
"""

import pandas as pd
import tempfile
import os
from pathlib import Path
import sys

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from matching.excel_processor import excel_processor
from database.models import db_manager
from config import config

def create_sample_excel_file():
    """Create a sample Excel file with test names."""
    
    # Sample data with various name formats
    sample_data = {
        'Nazwiska': [
            'Jan Kowalski',
            'Anna Nowak-Klejnowska', 
            'Dr hab. Marek Wiśniewski',
            'Agata Zielińska komornik sądowy',
            'Józef Dąbrowski nr 15/2023',
            'Katarzyna Król-Majewska',
            'Prof. dr hab. Stanisław Wójcik',
            'Magdalena Stępień przy Sądzie Rejonowym',
            'Paweł Szymański komornik przy SR w Krakowie',
            'Dorota Lewandowska',
            '',  # Empty cell
            'Adam Piotrowski komornik sądowy nr 5',
            'Beata Adamczyk przy Sądzie Okręgowym w Poznaniu'
        ],
        'Miasto': [
            'Warszawa', 'Kraków', 'Gdańsk', 'Wrocław', 'Poznań', 
            'Łódź', 'Szczecin', 'Bydgoszcz', 'Lublin', 'Katowice',
            'Białystok', 'Częstochowa', 'Rzeszów'
        ],
        'Numer': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    }
    
    df = pd.DataFrame(sample_data)
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    temp_file.close()
    
    df.to_excel(temp_file.name, index=False)
    print(f"✅ Created sample Excel file: {temp_file.name}")
    
    return temp_file.name

def create_sample_csv_file():
    """Create a sample CSV file."""
    sample_data = {
        'Names': [
            'Maria Kowalczyk',
            'Tomasz Jankowski komornik sądowy',
            'Dr Ewa Mazurek',
            'Michał Wójcik przy SR w Gdańsku',
            'Alicja Nowakowska'
        ]
    }
    
    df = pd.DataFrame(sample_data)
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
    temp_file.close()
    
    df.to_csv(temp_file.name, index=False)
    print(f"✅ Created sample CSV file: {temp_file.name}")
    
    return temp_file.name

def test_file_validation():
    """Test file validation functionality."""
    print("\n🔍 Testing file validation...")
    
    # Test non-existent file
    result = excel_processor.validate_file("non_existent_file.xlsx")
    assert not result, "Should reject non-existent file"
    print("✅ Non-existent file validation works")
    
    # Test unsupported format
    temp_txt = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    temp_txt.write(b"Some text")
    temp_txt.close()
    
    result = excel_processor.validate_file(temp_txt.name)
    assert not result, "Should reject unsupported format"
    os.unlink(temp_txt.name)
    print("✅ Unsupported format validation works")

def test_excel_reading():
    """Test Excel file reading."""
    print("\n📖 Testing Excel file reading...")
    
    excel_file = create_sample_excel_file()
    
    try:
        # Test reading Excel file
        df = excel_processor.read_excel_file(excel_file)
        assert not df.empty, "DataFrame should not be empty"
        assert 'Nazwiska' in df.columns, "Should contain 'Nazwiska' column"
        print(f"✅ Read Excel file: {len(df)} rows, {len(df.columns)} columns")
        
        # Test sheet names
        sheet_names = excel_processor.get_sheet_names(excel_file)
        assert len(sheet_names) > 0, "Should have at least one sheet"
        print(f"✅ Found sheets: {sheet_names}")
        
        # Test text column detection
        text_columns = excel_processor.extract_text_columns(df)
        assert 'Nazwiska' in text_columns, "Should detect 'Nazwiska' as text column"
        print(f"✅ Detected text columns: {text_columns}")
        
    finally:
        os.unlink(excel_file)

def test_csv_reading():
    """Test CSV file reading."""
    print("\n📄 Testing CSV file reading...")
    
    csv_file = create_sample_csv_file()
    
    try:
        # Test reading CSV file
        df = excel_processor.read_excel_file(csv_file)
        assert not df.empty, "DataFrame should not be empty"
        assert 'Names' in df.columns, "Should contain 'Names' column"
        print(f"✅ Read CSV file: {len(df)} rows, {len(df.columns)} columns")
        
        # Test sheet names for CSV
        sheet_names = excel_processor.get_sheet_names(csv_file)
        assert sheet_names == ['CSV'], "CSV should return ['CSV'] as sheet names"
        print(f"✅ CSV sheet names: {sheet_names}")
        
    finally:
        os.unlink(csv_file)

def test_name_extraction():
    """Test raw name extraction."""
    print("\n🏷️  Testing name extraction...")
    
    excel_file = create_sample_excel_file()
    
    try:
        # Extract names from specific column
        raw_names = excel_processor.extract_raw_names(excel_file, 'Nazwiska')
        
        # Should extract non-empty names
        assert len(raw_names) > 0, "Should extract at least some names"
        
        # Check structure of extracted names
        first_name = raw_names[0]
        required_fields = ['source_file', 'source_sheet', 'source_row', 'source_column', 'raw_text']
        for field in required_fields:
            assert field in first_name, f"Should contain {field} field"
        
        print(f"✅ Extracted {len(raw_names)} raw names")
        print(f"Sample name: {first_name['raw_text']}")
        
        # Test auto-detection
        auto_names = excel_processor.extract_raw_names(excel_file)
        assert len(auto_names) > 0, "Should auto-detect text column"
        print(f"✅ Auto-detected column extraction: {len(auto_names)} names")
        
    finally:
        os.unlink(excel_file)

def test_normalization():
    """Test name normalization."""
    print("\n🔄 Testing normalization...")
    
    # Create sample raw names
    raw_names = [
        {
            'source_file': 'test.xlsx',
            'source_sheet': 'Sheet1',
            'source_row': 1,
            'source_column': 'Nazwiska',
            'raw_text': 'Dr hab. Jan Kowalski komornik sądowy'
        },
        {
            'source_file': 'test.xlsx',
            'source_sheet': 'Sheet1', 
            'source_row': 2,
            'source_column': 'Nazwiska',
            'raw_text': 'Anna Nowak-Wiśniewska'
        }
    ]
    
    processed = excel_processor.process_and_normalize_names(raw_names)
    
    assert len(processed) == len(raw_names), "Should process all names"
    
    first_processed = processed[0]
    assert first_processed.normalized_text, "Should have normalized text"
    assert first_processed.raw_text == raw_names[0]['raw_text'], "Should preserve original text"
    
    print(f"✅ Processed {len(processed)} names")
    print(f"Original: {first_processed.raw_text}")
    print(f"Normalized: {first_processed.normalized_text}")
    if first_processed.extracted_lastname:
        print(f"Extracted lastname: {first_processed.extracted_lastname}")

def test_full_pipeline():
    """Test complete processing pipeline."""
    print("\n🚀 Testing full pipeline...")
    
    excel_file = create_sample_excel_file()
    
    try:
        # Process file without saving to database
        result = excel_processor.process_file(excel_file, 'Nazwiska', save_to_db=False)
        
        assert result['success'], f"Processing should succeed: {result.get('message', '')}"
        assert result['extracted_count'] > 0, "Should extract some names"
        assert result['processed_count'] > 0, "Should process some names"
        
        print(f"✅ Full pipeline test:")
        print(f"   Extracted: {result['extracted_count']} names")
        print(f"   Processed: {result['processed_count']} names")
        print(f"   Message: {result['message']}")
        
        # Check some processed names
        if 'processed_names' in result:
            for i, name in enumerate(result['processed_names'][:3]):
                print(f"   Name {i+1}: {name.raw_text} → {name.normalized_text}")
                
    finally:
        os.unlink(excel_file)

def main():
    """Run all tests."""
    print("🧪 Testing Excel Processor Module")
    print("=" * 50)
    
    try:
        test_file_validation()
        test_excel_reading()
        test_csv_reading()
        test_name_extraction()
        test_normalization()
        test_full_pipeline()
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
