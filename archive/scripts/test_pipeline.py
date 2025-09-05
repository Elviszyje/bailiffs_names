#!/usr/bin/env python3
"""
Quick test of database initialization without PostgreSQL.
Uses in-memory SQLite for testing.
"""
import sys
import os
from datetime import datetime

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.database.models import Base, BailiffDict
    from src.api.dane_gov_client import DaneGovAPIClient
    from src.matching.normalizer import normalizer
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_with_sqlite():
    """Test the full pipeline with SQLite in memory."""
    print("🧪 Testing database pipeline with SQLite...")
    
    # Create in-memory SQLite database
    engine = create_engine('sqlite:///:memory:', echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    
    print("✅ In-memory database created")
    
    # Fetch sample data from API
    print("📡 Fetching sample bailiffs data...")
    client = DaneGovAPIClient()
    bailiffs = client.get_bailiffs_page(1)['data'][:5]  # Just 5 records for test
    
    session = Session()
    
    # Process and insert data
    print("💾 Processing and inserting data...")
    for item in bailiffs:
        attrs = item['attributes']
        
        # Normalize data
        bailiff_data = {
            'nazwisko': attrs['col3']['val'],
            'imie': attrs['col4']['val'],
            'miasto': attrs['col5']['val']
        }
        
        normalized = normalizer.normalize_bailiff_record(bailiff_data)
        
        # Create database record
        db_record = BailiffDict(
            # Original API data
            apelacja=attrs['col1']['val'],
            sad_rejonowy_nr=attrs['col2']['val'],
            nazwisko=attrs['col3']['val'],
            imie=attrs['col4']['val'],
            miasto=attrs['col5']['val'],
            ulica=attrs['col6']['val'],
            kod_pocztowy=attrs['col7']['val'],
            
            # Normalized fields
            normalized_fullname=normalized['normalized_fullname'],
            normalized_lastname=normalized['normalized_lastname'],
            normalized_firstname=normalized['normalized_firstname'],
            normalized_city=normalized['normalized_city'],
            
            # API metadata
            api_row_id=item['id'],
            api_row_no=item['meta']['row_no'],
            api_updated_at=datetime.fromisoformat(item['meta']['updated_at'].replace('Z', '+00:00'))
        )
        
        session.add(db_record)
    
    session.commit()
    
    # Verify data
    print("✅ Verifying inserted data...")
    count = session.query(BailiffDict).count()
    print(f"   Records in database: {count}")
    
    # Show sample records
    records = session.query(BailiffDict).all()
    for i, record in enumerate(records, 1):
        print(f"   {i}. {record.imie} {record.nazwisko}")
        print(f"      Original: {record.imie} {record.nazwisko} ({record.miasto})")
        print(f"      Normalized: '{record.normalized_fullname}' ('{record.normalized_city}')")
        print(f"      Sąd: {record.sad_rejonowy_nr}")
        print()
    
    session.close()
    print("✅ SQLite test completed successfully!")
    
    return True

def main():
    """Main test function."""
    print("🚀 Testing Database Pipeline")
    print("=" * 40)
    
    try:
        success = test_with_sqlite()
        
        if success:
            print("\n🎉 Pipeline test successful!")
            print("\n📋 Ready for PostgreSQL setup:")
            print("1. Install PostgreSQL")
            print("2. Run: psql -U postgres -f sql/01_setup.sql")
            print("3. Update .env with your database credentials")
            print("4. Run: python scripts/init_database.py")
        else:
            print("\n❌ Pipeline test failed")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
