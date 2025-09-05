"""
Run matching algorithm for a specific session.
"""

import sys
sys.path.append('.')
sys.path.append('scripts')

from run_matching import match_single_name, RawNames, BailiffDict, MatchSuggestions
from add_session_support import AnalysisSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time

def run_matching_for_session(session_id, max_suggestions=5):
    """Run matching algorithm for all unprocessed names in a session."""
    print(f"🔍 DEBUG session_matching: Rozpoczynanie dopasowywania dla sesji {session_id}")
    
    try:
        print("🔍 DEBUG session_matching: Próba połączenia z bazą danych...")
        engine = create_engine("sqlite:///bailiffs_matching.db", echo=False)
        print("✅ DEBUG session_matching: Połączenie z bazą danych utworzone")
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        print("✅ DEBUG session_matching: Sesja bazy danych utworzona")
        
        # Get analysis session
        print(f"🔍 DEBUG session_matching: Szukanie sesji analizy o ID {session_id}...")
        analysis_session = session.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
        if not analysis_session:
            print(f"❌ DEBUG session_matching: Nie znaleziono sesji o ID {session_id}")
            return False, f"Session {session_id} not found"
        print(f"✅ DEBUG session_matching: Znaleziono sesję: {analysis_session.session_name}")
        
        # Get all bailiffs for matching
        print("🔍 DEBUG session_matching: Ładowanie komorników z bazy...")
        bailiffs = session.query(BailiffDict).all()
        print(f"✅ DEBUG session_matching: Załadowano {len(bailiffs)} komorników")
        
        if not bailiffs:
            print("❌ DEBUG session_matching: Brak komorników w bazie danych!")
            return False, "No bailiffs found in database"
        
        # Get unprocessed raw names for this session
        print(f"🔍 DEBUG session_matching: Szukanie nieprzetworowych nazwisk w sesji {session_id}...")
        raw_names = session.query(RawNames).filter(
            RawNames.session_id == session_id,
            RawNames.is_processed == False
        ).all()
        print(f"✅ DEBUG session_matching: Znaleziono {len(raw_names)} nieprzetworonych nazwisk")
        
        if not raw_names:
            print("✅ DEBUG session_matching: All names in this session already processed")
            analysis_session.status = 'completed'
            session.commit()
            return True, "No unprocessed names found"
        
        print(f"🔍 DEBUG session_matching: Processing {len(raw_names)} names...")
        
        total_suggestions = 0
        start_time = time.time()
        
        for i, raw_name in enumerate(raw_names, 1):
            if i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"🔍 DEBUG session_matching: Progress: {i}/{len(raw_names)} ({rate:.1f} names/sec)")
            elif i <= 5:  # Debug first 5 names
                print(f"🔍 DEBUG session_matching: Przetwarzanie nazwiska {i}: '{raw_name.raw_text}'")
            
            # Clear any existing suggestions for this raw_name
            existing_count = session.query(MatchSuggestions).filter(
                MatchSuggestions.raw_id == raw_name.id
            ).count()
            if existing_count > 0:
                print(f"🔍 DEBUG session_matching: Usuwanie {existing_count} istniejących sugestii dla '{raw_name.raw_text}'")
            
            session.query(MatchSuggestions).filter(
                MatchSuggestions.raw_id == raw_name.id
            ).delete()
            
            # Get top matches
            print(f"🔍 DEBUG session_matching: Wywołanie match_single_name dla '{raw_name.raw_text}'...")
            suggestions = match_single_name(raw_name, bailiffs, city_bonus=True, session_id=session_id)
            print(f"✅ DEBUG session_matching: Otrzymano {len(suggestions)} sugestii dla '{raw_name.raw_text}'")
            
            # Limit to max_suggestions
            suggestions = suggestions[:max_suggestions]
            
            # Save suggestions to database
            for j, suggestion in enumerate(suggestions):
                if i <= 3:  # Debug first 3 names
                    print(f"🔍 DEBUG session_matching: Zapisywanie sugestii {j+1}: bailiff_id={suggestion.bailiff_id}, score={suggestion.combined_score}")
                session.add(suggestion)
                total_suggestions += 1
            
            # Mark as processed
            raw_name.is_processed = True
            if i <= 3:  # Debug first 3 names
                print(f"✅ DEBUG session_matching: Oznaczono '{raw_name.raw_text}' jako przetworzone")
            
            # Commit in batches
            if i % 50 == 0:
                session.commit()
        
        # Final commit
        print("🔍 DEBUG session_matching: Wykonywanie końcowego commit...")
        session.commit()
        print("✅ DEBUG session_matching: Commit zakończony pomyślnie")
        
        # Update session stats
        analysis_session.processed_records = len(raw_names)
        analysis_session.status = 'completed'
        session.commit()
        
        elapsed = time.time() - start_time
        rate = len(raw_names) / elapsed if elapsed > 0 else 0
        
        print(f"✅ DEBUG session_matching: Matching completed!")
        print(f"📊 DEBUG session_matching: Generated {total_suggestions} suggestions for {len(raw_names)} names")
        print(f"⚡ DEBUG session_matching: Processing rate: {rate:.1f} names/second")
        
        return True, f"Generated {total_suggestions} suggestions in {elapsed:.1f}s"
        
    except Exception as e:
        print(f"❌ DEBUG session_matching: Błąd podczas dopasowywania: {e}")
        print(f"❌ DEBUG session_matching: Typ błędu: {type(e).__name__}")
        import traceback
        print(f"❌ DEBUG session_matching: Traceback: {traceback.format_exc()}")
        
        try:
            session.rollback()
            # Update session status to error
            analysis_session.status = 'error'
            session.commit()
        except Exception as commit_error:
            print(f"❌ DEBUG session_matching: Błąd podczas rollback/commit: {commit_error}")
        
        return False, f"Error during matching: {e}"
    finally:
        print("🔍 DEBUG session_matching: Zamykanie sesji bazy danych...")
        try:
            session.close()
            print("✅ DEBUG session_matching: Sesja zamknięta")
        except Exception as close_error:
            print(f"❌ DEBUG session_matching: Błąd podczas zamykania sesji: {close_error}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        session_id = int(sys.argv[1])
        success, message = run_matching_for_session(session_id)
        print(f"Result: {message}")
    else:
        print("Usage: python session_matching.py <session_id>")
