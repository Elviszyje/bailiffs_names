#!/usr/bin/env python3
"""
Matching algorithm script using rapidfuzz for fuzzy matching.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, func, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from rapidfuzz import fuzz, process
import time

# Database models
Base = declarative_base()

class AnalysisSession(Base):
    """Track different analysis sessions for uploaded files."""
    __tablename__ = 'analysis_sessions'
    
    id = Column(Integer, primary_key=True)
    session_name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    total_records = Column(Integer, nullable=True)
    processed_records = Column(Integer, default=0, nullable=False)
    matched_records = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default='uploaded', nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class BailiffDict(Base):
    """Target bailiff dictionary."""
    __tablename__ = 'bailiffs_dict'
    
    id = Column(Integer, primary_key=True)
    original_nazwisko = Column(Text, nullable=False)
    original_imie = Column(String(100), nullable=True)
    original_miasto = Column(String(100), nullable=True)
    original_sad = Column(Text, nullable=True)
    adres = Column(Text, nullable=True)
    kod_pocztowy = Column(String(20), nullable=True)
    telefon = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    bank = Column(String(200), nullable=True)
    numer_konta = Column(String(100), nullable=True)
    normalized_lastname = Column(String(100), nullable=True)
    normalized_firstname = Column(String(100), nullable=True)
    normalized_fullname = Column(Text, nullable=True)
    normalized_city = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

class RawNames(Base):
    """Raw names to be matched."""
    __tablename__ = 'raw_names'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('analysis_sessions.id'), nullable=True)
    source_file = Column(String(500), nullable=False)
    source_sheet = Column(String(100), nullable=True)
    source_row = Column(Integer, nullable=True)
    source_column = Column(String(100), nullable=True)
    raw_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=True)
    extracted_lastname = Column(String(100), nullable=True)
    extracted_firstname = Column(String(100), nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False)
    processing_notes = Column(Text, nullable=True)
    source_city = Column(String(200), nullable=True)
    source_email = Column(String(200), nullable=True)
    source_phone = Column(String(50), nullable=True)
    source_address = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

class MatchSuggestions(Base):
    """Match suggestions from algorithm."""
    __tablename__ = 'match_suggestions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('analysis_sessions.id'), nullable=True)
    raw_id = Column(Integer, ForeignKey('raw_names.id'), nullable=False)
    bailiff_id = Column(Integer, ForeignKey('bailiffs_dict.id'), nullable=False)
    
    # Matching scores
    fullname_score = Column(Float, nullable=False)
    lastname_score = Column(Float, nullable=True)
    firstname_score = Column(Float, nullable=True)
    city_score = Column(Float, nullable=True)
    combined_score = Column(Float, nullable=False)
    
    # Algorithm info
    algorithm_used = Column(String(50), nullable=False)
    confidence_level = Column(String(20), nullable=False)  # 'high', 'medium', 'low'
    
    # System fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    raw_name = relationship("RawNames", backref="suggestions")
    bailiff = relationship("BailiffDict", backref="suggestions")

def setup_database():
    """Setup database connection."""
    print("🔧 Łączenie z bazą danych...")
    
    database_url = "sqlite:///bailiffs_matching.db"
    engine = create_engine(database_url, echo=False)
    
    # Create new tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    print("✅ Połączono z bazą danych")
    return engine, SessionLocal

def calculate_city_score(raw_city, bailiff_city):
    """Calculate city matching score."""
    if not raw_city or not bailiff_city:
        return 0.0
    
    # Simple city matching
    raw_city_clean = raw_city.lower().strip()
    bailiff_city_clean = bailiff_city.lower().strip()
    
    if raw_city_clean == bailiff_city_clean:
        return 100.0
    
    # Use fuzzy matching for cities
    return fuzz.ratio(raw_city_clean, bailiff_city_clean)

def match_single_name(raw_name, bailiffs_dict, city_bonus=True, session_id=None):
    """Match a single raw name against the bailiffs dictionary."""
    if not raw_name.normalized_text:
        return []
    
    # Prepare search text
    search_text = raw_name.normalized_text
    
    # Create list of bailiff texts for matching
    bailiff_texts = []
    bailiff_lookup = {}
    
    for bailiff in bailiffs_dict:
        if bailiff.normalized_fullname:
            bailiff_texts.append(bailiff.normalized_fullname)
            bailiff_lookup[bailiff.normalized_fullname] = bailiff
    
    if not bailiff_texts:
        return []
    
    # Use rapidfuzz to find top matches
    matches = process.extract(
        search_text, 
        bailiff_texts, 
        scorer=fuzz.ratio,
        limit=10  # Top 10 matches
    )
    
    suggestions = []
    
    for match_text, fullname_score, _ in matches:
        # Skip very low scores
        if fullname_score < 30:
            continue
            
        bailiff = bailiff_lookup[match_text]
        
        # Calculate individual component scores
        lastname_score = 0.0
        firstname_score = 0.0
        
        if raw_name.extracted_lastname and bailiff.normalized_lastname:
            lastname_score = fuzz.ratio(raw_name.extracted_lastname, bailiff.normalized_lastname)
        
        if raw_name.extracted_firstname and bailiff.normalized_firstname:
            firstname_score = fuzz.ratio(raw_name.extracted_firstname, bailiff.normalized_firstname)
        
        # Calculate city score
        city_score = calculate_city_score(raw_name.source_city, bailiff.original_miasto)
        
        # Calculate combined score with weights
        combined_score = (
            fullname_score * 0.6 +  # 60% weight for full name
            lastname_score * 0.2 +  # 20% weight for last name
            firstname_score * 0.1   # 10% weight for first name
        )
        
        # City bonus (add up to 10 points for good city match)
        if city_bonus and city_score > 70:
            combined_score += (city_score / 10)
        
        # Determine confidence level
        if combined_score >= 90:
            confidence = 'high'
        elif combined_score >= 70:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        suggestion = MatchSuggestions(
            raw_id=raw_name.id,
            bailiff_id=bailiff.id,
            session_id=session_id,
            fullname_score=fullname_score,
            lastname_score=lastname_score,
            firstname_score=firstname_score,
            city_score=city_score,
            combined_score=combined_score,
            algorithm_used='rapidfuzz_ratio',
            confidence_level=confidence
        )
        
        suggestions.append(suggestion)
    
    # Sort by combined score
    suggestions.sort(key=lambda x: x.combined_score, reverse=True)
    
    # Return top 5 suggestions
    return suggestions[:5]

def run_matching_algorithm(session_class, batch_size=50):
    """Run the matching algorithm for all raw names."""
    print("🚀 Uruchamianie algorytmu dopasowywania...")
    
    session = session_class()
    
    try:
        # Load all bailiffs into memory for faster matching
        print("📚 Ładowanie słownika komorników...")
        bailiffs_dict = session.query(BailiffDict).all()
        print(f"   Załadowano: {len(bailiffs_dict)} komorników")
        
        # Get all raw names to process
        print("📝 Pobieranie nazw do dopasowania...")
        raw_names = session.query(RawNames).all()
        print(f"   Do przetworzenia: {len(raw_names)} nazw")
        
        # Clear existing suggestions
        print("🧹 Czyszczenie poprzednich sugestii...")
        session.query(MatchSuggestions).delete()
        session.commit()
        
        # Process in batches
        total_processed = 0
        total_suggestions = 0
        start_time = time.time()
        
        for i in range(0, len(raw_names), batch_size):
            batch = raw_names[i:i+batch_size]
            batch_suggestions = []
            
            for raw_name in batch:
                suggestions = match_single_name(raw_name, bailiffs_dict)
                batch_suggestions.extend(suggestions)
                total_suggestions += len(suggestions)
            
            # Save batch to database
            if batch_suggestions:
                session.add_all(batch_suggestions)
                session.commit()
            
            total_processed += len(batch)
            
            # Progress update
            elapsed = time.time() - start_time
            rate = total_processed / elapsed if elapsed > 0 else 0
            eta = (len(raw_names) - total_processed) / rate if rate > 0 else 0
            
            print(f"   Postęp: {total_processed}/{len(raw_names)} "
                  f"({(total_processed/len(raw_names)*100):.1f}%) "
                  f"- {rate:.1f} nazw/sek - ETA: {eta:.0f}s")
        
        # Final stats
        elapsed = time.time() - start_time
        print(f"\n📊 Wyniki dopasowywania:")
        print(f"   Przetworzono nazw: {total_processed}")
        print(f"   Wygenerowano sugestii: {total_suggestions}")
        print(f"   Średnio sugestii na nazwę: {total_suggestions/total_processed:.1f}")
        print(f"   Czas wykonania: {elapsed:.1f} sekund")
        print(f"   Wydajność: {total_processed/elapsed:.1f} nazw/sek")
        
        # Confidence level breakdown
        print(f"\n🎯 Rozkład poziomów pewności:")
        high_conf = session.query(MatchSuggestions).filter(MatchSuggestions.confidence_level == 'high').count()
        med_conf = session.query(MatchSuggestions).filter(MatchSuggestions.confidence_level == 'medium').count()
        low_conf = session.query(MatchSuggestions).filter(MatchSuggestions.confidence_level == 'low').count()
        
        print(f"   Wysoka pewność (≥90%): {high_conf}")
        print(f"   Średnia pewność (70-89%): {med_conf}")
        print(f"   Niska pewność (<70%): {low_conf}")
        
        # Show some examples
        print(f"\n📝 Przykłady najlepszych dopasowań:")
        best_matches = session.query(MatchSuggestions).order_by(MatchSuggestions.combined_score.desc()).limit(5).all()
        
        for i, match in enumerate(best_matches, 1):
            print(f"   {i}. Wynik: {match.combined_score:.1f}% ({match.confidence_level})")
            print(f"      Oryginał: {match.raw_name.raw_text}")
            print(f"      Dopasowane: {match.bailiff.original_nazwisko}")
            print(f"      Miasto: {match.raw_name.source_city} → {match.bailiff.original_miasto}")
        
    finally:
        session.close()

def main():
    """Main matching process."""
    print("🎯 Algorytm dopasowywania komorników")
    print("=" * 50)
    
    try:
        # Setup database
        engine, session_class = setup_database()
        
        # Run matching
        run_matching_algorithm(session_class)
        
        print(f"\n🎉 Dopasowywanie zakończone pomyślnie!")
        print(f"\nNastępne kroki:")
        print("1. Uruchom aplikację Streamlit: streamlit run app.py")
        print("2. Przejrzyj i zatwierdź sugerowane dopasowania")
        print("3. Eksportuj wyniki")
        
    except Exception as e:
        print(f"\n❌ Błąd podczas dopasowywania: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
