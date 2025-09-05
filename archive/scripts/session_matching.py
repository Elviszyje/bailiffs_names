"""
Run matching algorithm for a specific session.
"""

import sys
sys.path.append('.')
sys.path.append('scripts')

from scripts.run_matching import match_single_name, RawNames, BailiffDict, MatchSuggestions
from scripts.add_session_support import AnalysisSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time

def run_matching_for_session(session_id, max_suggestions=5):
    """Run fuzzy matching for all unprocessed names in a specific session."""
    
    engine = create_engine('sqlite:///bailiffs_matching.db', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Get session info
        analysis_session = session.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
        if not analysis_session:
            return False, "Session not found"
        
        print(f"🎯 Starting matching for session: {analysis_session.session_name}")
        
        # Update session status
        analysis_session.status = 'matching'
        session.commit()
        
        # Get all bailiffs for matching
        bailiffs = session.query(BailiffDict).all()
        print(f"📖 Loaded {len(bailiffs)} bailiffs from dictionary")
        
        # Get unprocessed raw names from this session
        raw_names = session.query(RawNames).filter(
            RawNames.session_id == session_id,
            RawNames.is_processed == False
        ).all()
        
        if not raw_names:
            print("✅ All names in this session already processed")
            analysis_session.status = 'completed'
            session.commit()
            return True, "No unprocessed names found"
        
        print(f"🔍 Processing {len(raw_names)} names...")
        
        total_suggestions = 0
        start_time = time.time()
        
        for i, raw_name in enumerate(raw_names, 1):
            if i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"Progress: {i}/{len(raw_names)} ({rate:.1f} names/sec)")
            
            # Clear any existing suggestions for this raw_name
            session.query(MatchSuggestions).filter(
                MatchSuggestions.raw_id == raw_name.id
            ).delete()
            
            # Get top matches
            suggestions = match_single_name(raw_name, bailiffs, city_bonus=True, session_id=session_id)
            
            # Limit to max_suggestions
            suggestions = suggestions[:max_suggestions]
            
            # Save suggestions to database
            for suggestion in suggestions:
                session.add(suggestion)
                total_suggestions += 1
            
            # Mark as processed
            raw_name.is_processed = True
            
            # Commit in batches
            if i % 50 == 0:
                session.commit()
        
        # Final commit
        session.commit()
        
        # Update session stats
        analysis_session.processed_records = len(raw_names)
        analysis_session.status = 'completed'
        session.commit()
        
        elapsed = time.time() - start_time
        rate = len(raw_names) / elapsed if elapsed > 0 else 0
        
        print(f"✅ Matching completed!")
        print(f"📊 Generated {total_suggestions} suggestions for {len(raw_names)} names")
        print(f"⚡ Processing rate: {rate:.1f} names/second")
        
        return True, f"Generated {total_suggestions} suggestions in {elapsed:.1f}s"
        
    except Exception as e:
        session.rollback()
        # Update session status to error
        try:
            analysis_session.status = 'error'
            session.commit()
        except:
            pass
        return False, f"Error during matching: {e}"
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        session_id = int(sys.argv[1])
        success, message = run_matching_for_session(session_id)
        print(f"Result: {message}")
    else:
        print("Usage: python session_matching.py <session_id>")
