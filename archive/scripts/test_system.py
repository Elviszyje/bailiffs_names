#!/usr/bin/env python3
"""
Test the API connection and fetch sample bailiffs data.
"""
import sys
import os
import json
from datetime import datetime

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.api.dane_gov_client import DaneGovAPIClient
    from src.matching.normalizer import normalizer
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please run setup.py first to install dependencies")
    sys.exit(1)

def test_api_connection():
    """Test the API connection and fetch sample data."""
    print("🌐 Testing API connection to dane.gov.pl...")
    
    try:
        client = DaneGovAPIClient()
        
        # Test metadata
        print("\n📊 Fetching metadata...")
        meta = client.get_bailiffs_meta()
        print(f"✅ Total bailiffs in database: {meta.get('count', 'unknown')}")
        
        # Test single page
        print("\n📄 Fetching first page...")
        page_data = client.get_bailiffs_page(1)
        sample_records = page_data.get('data', [])[:3]  # Get first 3 records
        
        if sample_records:
            print(f"✅ Successfully fetched {len(sample_records)} sample records")
            
            print("\n📝 Sample records:")
            for i, record in enumerate(sample_records, 1):
                attrs = record['attributes']
                print(f"\n{i}. {attrs['col4']['val']} {attrs['col3']['val']}")
                print(f"   Apelacja: {attrs['col1']['val']}")
                print(f"   Sąd: {attrs['col2']['val']}")
                print(f"   Miasto: {attrs['col5']['val']}")
                print(f"   Adres: {attrs['col6']['val']}, {attrs['col7']['val']}")
        else:
            print("❌ No records found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

def test_normalization():
    """Test the normalization functionality."""
    print("\n🔧 Testing text normalization...")
    
    test_cases = [
        "Komornik Sądowy przy Sądzie Rejonowym Jan Kowalski",
        "mgr Anna Nowak-Kowalska, Kancelaria Komornicza Nr 5",
        "Zastępca Komornika Piotr Wiśniewski",
        "Dr hab. Józef Dąbrowski - Komornik Sądowy"
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n{i}. Original: '{test_text}'")
        
        # Test normalization
        normalized = normalizer.normalize_for_matching(test_text)
        print(f"   Normalized: '{normalized}'")
        
        # Test name extraction
        result = normalizer.normalize_raw_text(test_text)
        print(f"   First name: '{result.get('extracted_firstname')}'")
        print(f"   Last name: '{result.get('extracted_lastname')}'")
    
    print("✅ Normalization tests completed")

def test_full_workflow():
    """Test the complete workflow."""
    print("\n🔄 Testing complete workflow...")
    
    try:
        client = DaneGovAPIClient()
        
        # Get a few bailiff records
        print("Fetching bailiff records...")
        page_data = client.get_bailiffs_page(1)
        bailiff_records = page_data.get('data', [])[:2]
        
        if not bailiff_records:
            print("❌ No bailiff records available")
            return False
        
        for record in bailiff_records:
            attrs = record['attributes']
            
            # Original data
            original_name = f"{attrs['col4']['val']} {attrs['col3']['val']}"
            print(f"\n🏛️ Processing: {original_name}")
            
            # Normalize bailiff record
            bailiff_data = {
                'nazwisko': attrs['col3']['val'],
                'imie': attrs['col4']['val'],
                'miasto': attrs['col5']['val']
            }
            
            normalized_bailiff = normalizer.normalize_bailiff_record(bailiff_data)
            print(f"   Normalized fullname: '{normalized_bailiff['normalized_fullname']}'")
            
            # Simulate raw text matching
            variations = [
                f"Komornik {original_name}",
                f"mgr {original_name} - Kancelaria",
                f"{attrs['col3']['val']}, {attrs['col4']['val']}"
            ]
            
            for variation in variations:
                normalized_raw = normalizer.normalize_raw_text(variation)
                print(f"   Raw text: '{variation}'")
                print(f"   -> Normalized: '{normalized_raw['normalized_text']}'")
                
                # Simple similarity check
                similarity = (normalized_bailiff['normalized_fullname'] == 
                            normalized_raw['normalized_text'])
                print(f"   -> Exact match: {'✅' if similarity else '❌'}")
        
        print("\n✅ Workflow test completed")
        return True
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        return False

def save_sample_data():
    """Save sample data to file for analysis."""
    print("\n💾 Saving sample data for analysis...")
    
    try:
        client = DaneGovAPIClient()
        page_data = client.get_bailiffs_page(1)
        sample_records = page_data.get('data', [])[:10]
        
        # Process and save
        processed_data = []
        for record in sample_records:
            attrs = record['attributes']
            processed_data.append({
                'original': {
                    'imie': attrs['col4']['val'],
                    'nazwisko': attrs['col3']['val'],
                    'miasto': attrs['col5']['val'],
                    'apelacja': attrs['col1']['val']
                },
                'normalized': normalizer.normalize_bailiff_record({
                    'nazwisko': attrs['col3']['val'],
                    'imie': attrs['col4']['val'],
                    'miasto': attrs['col5']['val']
                })
            })
        
        # Save to file
        output_file = f"sample_bailiffs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Sample data saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to save sample data: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Testing Bailiffs Matching System Components")
    print("=" * 60)
    
    tests = [
        ("API Connection", test_api_connection),
        ("Text Normalization", test_normalization),
        ("Full Workflow", test_full_workflow),
        ("Sample Data Export", save_sample_data)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if success:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! System is ready for use.")
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Please check the configuration.")

if __name__ == "__main__":
    main()
