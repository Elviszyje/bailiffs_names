#!/usr/bin/env python3
"""
Script to remove duplicates from the bailiff dictionary.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
sys.path.append('scripts')
from run_matching import BailiffDict, MatchSuggestions

def setup_database():
    """Setup database connection."""
    database_url = "sqlite:///bailiffs_matching.db"
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal

def remove_duplicates(session_class):
    """Remove duplicate bailiffs and regenerate suggestions."""
    session = session_class()
    
    try:
        print("🧹 Usuwanie duplikatów ze słownika komorników...")
        
        # Get count before cleanup
        total_before = session.query(BailiffDict).count()
        print(f"   Rekordów przed czyszczeniem: {total_before}")
        
        # Find duplicates based on normalized_fullname
        duplicates = session.execute(text('''
            SELECT normalized_fullname, COUNT(*) as cnt, MIN(id) as keep_id
            FROM bailiffs_dict 
            WHERE normalized_fullname IS NOT NULL 
            GROUP BY normalized_fullname 
            HAVING COUNT(*) > 1
        ''')).fetchall()
        
        print(f"   Znalezione grupy duplikatów: {len(duplicates)}")
        
        deleted_count = 0
        for fullname, count, keep_id in duplicates:
            # Delete all except the first one (with MIN id)
            deleted = session.execute(text('''
                DELETE FROM bailiffs_dict 
                WHERE normalized_fullname = :fullname AND id != :keep_id
            '''), {'fullname': fullname, 'keep_id': keep_id})
            
            deleted_count += deleted.rowcount
            print(f"   Usunięto {deleted.rowcount} duplikatów dla: {fullname}")
        
        session.commit()
        
        # Get count after cleanup
        total_after = session.query(BailiffDict).count()
        print(f"   Rekordów po czyszczeniu: {total_after}")
        print(f"   Usunięto łącznie: {deleted_count} duplikatów")
        
        # Now remove orphaned suggestions
        print(f"\n🧹 Usuwanie nieaktualnych sugestii...")
        
        # Delete suggestions that reference non-existent bailiffs
        orphaned = session.execute(text('''
            DELETE FROM match_suggestions 
            WHERE bailiff_id NOT IN (SELECT id FROM bailiffs_dict)
        '''))
        
        print(f"   Usunięto {orphaned.rowcount} nieaktualnych sugestii")
        session.commit()
        
        return deleted_count
        
    except Exception as e:
        session.rollback()
        print(f"❌ Błąd podczas usuwania duplikatów: {e}")
        raise
    finally:
        session.close()

def regenerate_suggestions(session_class):
    """Regenerate match suggestions after cleanup."""
    print("\n🔄 Regenerowanie sugestii dopasowań...")
    
    # Import and run the matching algorithm
    from run_matching import run_matching_algorithm
    
    session = session_class()
    try:
        # Clear all existing suggestions
        session.query(MatchSuggestions).delete()
        session.commit()
        print("   Wyczyszczono poprzednie sugestie")
        
        # Run matching algorithm again
        run_matching_algorithm(session_class, batch_size=50)
        
    finally:
        session.close()

def main():
    """Main cleanup process."""
    print("🧹 Czyszczenie duplikatów w bazie danych")
    print("=" * 50)
    
    try:
        # Setup database
        engine, session_class = setup_database()
        
        # Remove duplicates
        deleted_count = remove_duplicates(session_class)
        
        if deleted_count > 0:
            # Regenerate suggestions
            regenerate_suggestions(session_class)
        
        print(f"\n🎉 Czyszczenie zakończone pomyślnie!")
        print(f"   Usunięto {deleted_count} duplikatów")
        print(f"\nTeraz propozycje dopasowań powinny być unikalne.")
        
    except Exception as e:
        print(f"\n❌ Błąd podczas czyszczenia: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
