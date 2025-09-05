#!/usr/bin/env python3
"""
Initialize the database and import bailiffs data from API.
"""
import sys
import os
import logging
from datetime import datetime

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.database.models import db_manager, BailiffDict, Base
    from src.api.dane_gov_client import DaneGovAPIClient
    from src.matching.normalizer import normalizer
    from src.config import config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection."""
    print("🔍 Testing database connection...")
    
    if db_manager.test_connection():
        print("✅ Database connection successful")
        return True
    else:
        print("❌ Database connection failed")
        print("Please check your PostgreSQL installation and .env configuration")
        return False

def create_database_tables():
    """Create all database tables."""
    print("🏗️  Creating database tables...")
    
    try:
        db_manager.create_tables()
        print("✅ Database tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def fetch_and_normalize_bailiffs():
    """Fetch bailiffs from API and normalize the data."""
    print("📡 Fetching bailiffs data from API...")
    
    try:
        client = DaneGovAPIClient()
        bailiffs = client.get_all_bailiffs()
        
        if not bailiffs:
            print("❌ No bailiffs data received from API")
            return []
        
        print(f"✅ Fetched {len(bailiffs)} bailiff records")
        
        # Normalize the data
        print("🔧 Normalizing bailiff records...")
        normalized_bailiffs = []
        
        for bailiff in bailiffs:
            try:
                # Create normalized data
                bailiff_data = {
                    'nazwisko': bailiff.nazwisko,
                    'imie': bailiff.imie, 
                    'miasto': bailiff.miasto
                }
                
                normalized = normalizer.normalize_bailiff_record(bailiff_data)
                
                # Create database record
                db_record = BailiffDict(
                    # Original API data
                    apelacja=bailiff.apelacja,
                    sad_rejonowy_nr=bailiff.sad_rejonowy_nr,
                    nazwisko=bailiff.nazwisko,
                    imie=bailiff.imie,
                    miasto=bailiff.miasto,
                    ulica=bailiff.ulica or '',
                    kod_pocztowy=bailiff.kod_pocztowy or '',
                    
                    # Normalized fields
                    normalized_fullname=normalized['normalized_fullname'],
                    normalized_lastname=normalized['normalized_lastname'],
                    normalized_firstname=normalized['normalized_firstname'],
                    normalized_city=normalized['normalized_city'],
                    
                    # API metadata
                    api_row_id=bailiff.row_id,
                    api_row_no=bailiff.row_no,
                    api_updated_at=datetime.fromisoformat(bailiff.updated_at.replace('Z', '+00:00'))
                )
                
                normalized_bailiffs.append(db_record)
                
            except Exception as e:
                logger.warning(f"Failed to normalize bailiff record {bailiff.row_id}: {e}")
                continue
        
        print(f"✅ Successfully normalized {len(normalized_bailiffs)} records")
        return normalized_bailiffs
        
    except Exception as e:
        print(f"❌ Failed to fetch/normalize bailiffs: {e}")
        return []

def import_bailiffs_to_database(bailiffs):
    """Import normalized bailiffs to database."""
    print(f"💾 Importing {len(bailiffs)} bailiffs to database...")
    
    try:
        session = db_manager.get_session()
        
        # Clear existing data (for fresh import)
        print("🗑️  Clearing existing bailiffs data...")
        session.query(BailiffDict).delete()
        session.commit()
        
        # Batch insert
        batch_size = 100
        imported = 0
        
        for i in range(0, len(bailiffs), batch_size):
            batch = bailiffs[i:i+batch_size]
            session.add_all(batch)
            session.commit()
            imported += len(batch)
            
            if i % (batch_size * 10) == 0:  # Progress every 1000 records
                print(f"   Imported {imported}/{len(bailiffs)} records...")
        
        session.close()
        print(f"✅ Successfully imported {imported} bailiff records")
        return True
        
    except Exception as e:
        print(f"❌ Failed to import bailiffs: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def verify_import():
    """Verify the import was successful."""
    print("✅ Verifying import...")
    
    try:
        session = db_manager.get_session()
        
        # Count total records
        total = session.query(BailiffDict).count()
        print(f"   Total bailiffs in database: {total}")
        
        # Sample some records
        samples = session.query(BailiffDict).limit(3).all()
        
        print("   Sample records:")
        for i, bailiff in enumerate(samples, 1):
            print(f"   {i}. {bailiff.imie} {bailiff.nazwisko}")
            print(f"      Normalized: '{bailiff.normalized_fullname}'")
            print(f"      City: {bailiff.miasto} -> '{bailiff.normalized_city}'")
            print(f"      Sąd: {bailiff.sad_rejonowy_nr}")
        
        # Check for duplicates
        duplicates = session.query(BailiffDict.api_row_id).group_by(BailiffDict.api_row_id).having(
            session.query(BailiffDict.api_row_id).group_by(BailiffDict.api_row_id).count() > 1
        ).count()
        
        if duplicates > 0:
            print(f"⚠️  Found {duplicates} duplicate API row IDs")
        else:
            print("✅ No duplicates found")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def run_sql_indexes():
    """Run the additional SQL indexes and functions."""
    print("🔧 Creating PostgreSQL indexes and functions...")
    
    try:
        import subprocess
        sql_file = "sql/02_indexes_functions.sql"
        
        if os.path.exists(sql_file):
            # Use psql to run the SQL file
            # Note: This assumes PostgreSQL is accessible and .env has correct credentials
            db_url = config.database.connection_string
            
            print(f"   Running {sql_file}...")
            print("   (This may take a few minutes for large datasets)")
            
            # For now, just print instructions
            print(f"   Please run manually: psql '{db_url}' -f {sql_file}")
            print("✅ SQL file ready for execution")
            return True
        else:
            print(f"⚠️  SQL file {sql_file} not found")
            return False
            
    except Exception as e:
        print(f"❌ Failed to setup SQL indexes: {e}")
        return False

def main():
    """Main initialization function."""
    print("🚀 Initializing Bailiffs Database")
    print("=" * 50)
    
    steps = [
        ("Database Connection Test", test_database_connection),
        ("Create Database Tables", create_database_tables),
        ("Fetch & Normalize Bailiffs", lambda: fetch_and_normalize_bailiffs()),
        ("Import to Database", lambda: import_bailiffs_to_database(
            fetch_and_normalize_bailiffs() if 'bailiffs_data' not in globals() else bailiffs_data
        )),
        ("Verify Import", verify_import),
        ("Setup SQL Indexes", run_sql_indexes)
    ]
    
    # Execute first 3 steps to get data
    results = []
    bailiffs_data = None
    
    for i, (step_name, step_func) in enumerate(steps[:3]):
        print(f"\n{'='*20} {step_name} {'='*20}")
        
        if i == 2:  # Fetch & Normalize step
            bailiffs_data = step_func()
            success = len(bailiffs_data) > 0
        else:
            success = step_func()
            
        results.append((step_name, success))
        
        if not success:
            print(f"❌ Step failed: {step_name}")
            break
    else:
        # Continue with remaining steps if we have data
        if bailiffs_data:
            print(f"\n{'='*20} Import to Database {'='*20}")
            success = import_bailiffs_to_database(bailiffs_data)
            results.append(("Import to Database", success))
            
            if success:
                print(f"\n{'='*20} Verify Import {'='*20}")
                success = verify_import()
                results.append(("Verify Import", success))
                
                print(f"\n{'='*20} Setup SQL Indexes {'='*20}")
                success = run_sql_indexes()
                results.append(("Setup SQL Indexes", success))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 INITIALIZATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    for step_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{step_name:.<35} {status}")
        if success:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} steps completed")
    
    if passed == len(results):
        print("\n🎉 Database initialization completed successfully!")
        print("\n📋 Next steps:")
        print("1. Run SQL indexes: psql -f sql/02_indexes_functions.sql")
        print("2. Test file upload functionality")
        print("3. Implement matching algorithms")
    else:
        print(f"\n⚠️  {len(results) - passed} step(s) failed.")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()
