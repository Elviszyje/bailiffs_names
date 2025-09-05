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
    """Match a single raw name against the bailiffs dictionary using multiple algorithms."""
    print(f"🔍 DEBUG run_matching: Rozpoczynanie dopasowywania dla '{raw_name.raw_text}'")
    print(f"🔍 DEBUG run_matching: Normalized text: '{raw_name.normalized_text}'")
    print(f"🔍 DEBUG run_matching: Source city: '{raw_name.source_city}'")
    
    if not raw_name.normalized_text:
        print("❌ DEBUG run_matching: Brak znormalizowanego tekstu!")
        return []
    
    # Prepare search text - try multiple variants
    search_text = raw_name.normalized_text
    
    # Create alternative search texts
    search_variants = [search_text]
    
    # Add lastname + firstname combination if available
    if raw_name.extracted_lastname and raw_name.extracted_firstname:
        lastname_firstname = f"{raw_name.extracted_lastname} {raw_name.extracted_firstname}".lower()
        firstname_lastname = f"{raw_name.extracted_firstname} {raw_name.extracted_lastname}".lower()
        search_variants.extend([lastname_firstname, firstname_lastname])
    
    print(f"🔍 DEBUG run_matching: Search variants: {search_variants}")
    
    # Create list of bailiff texts for matching
    bailiff_texts = []
    bailiff_lookup = {}
    
    for bailiff in bailiffs_dict:
        # Create multiple representations of each bailiff
        bailiff_variants = []
        
        if bailiff.normalized_fullname:
            bailiff_variants.append(bailiff.normalized_fullname)
        
        # Add lastname + firstname variant
        if bailiff.normalized_lastname and bailiff.normalized_firstname:
            lastname_firstname = f"{bailiff.normalized_lastname} {bailiff.normalized_firstname}"
            firstname_lastname = f"{bailiff.normalized_firstname} {bailiff.normalized_lastname}"
            bailiff_variants.extend([lastname_firstname, firstname_lastname])
        elif bailiff.normalized_lastname:
            bailiff_variants.append(bailiff.normalized_lastname)
            
        # Add original name variants
        if bailiff.original_nazwisko and bailiff.original_imie:
            original_full = f"{bailiff.original_nazwisko.lower()} {bailiff.original_imie.lower()}"
            bailiff_variants.append(original_full)
        
        # Store all variants
        for variant in bailiff_variants:
            if variant and variant not in bailiff_lookup:
                bailiff_texts.append(variant)
                bailiff_lookup[variant] = bailiff
    
    print(f"✅ DEBUG run_matching: Przygotowano {len(bailiff_texts)} tekstów komorników do dopasowania")
    
    if not bailiff_texts:
        print("❌ DEBUG run_matching: Brak tekstów komorników do dopasowania!")
        return []
    
    # Try multiple matching algorithms
    all_matches = {}
    
    for search_variant in search_variants:
        print(f"🔍 DEBUG run_matching: Testowanie wariantu: '{search_variant}'")
        
        # Algorithm 1: Standard ratio
        matches_ratio = process.extract(
            search_variant, 
            bailiff_texts, 
            scorer=fuzz.ratio,
            limit=20
        )
        
        # Algorithm 2: Token sort ratio (better for reordered words)
        matches_token_sort = process.extract(
            search_variant, 
            bailiff_texts, 
            scorer=fuzz.token_sort_ratio,
            limit=20
        )
        
        # Algorithm 3: Partial ratio (better for partial matches)
        matches_partial = process.extract(
            search_variant, 
            bailiff_texts, 
            scorer=fuzz.partial_ratio,
            limit=20
        )
        
        # Combine all matches
        for match_text, score, _ in matches_ratio:
            bailiff_id = bailiff_lookup[match_text].id
            if bailiff_id not in all_matches:
                all_matches[bailiff_id] = {'bailiff': bailiff_lookup[match_text], 'scores': []}
            all_matches[bailiff_id]['scores'].append(('ratio', score))
            
        for match_text, score, _ in matches_token_sort:
            bailiff_id = bailiff_lookup[match_text].id
            if bailiff_id not in all_matches:
                all_matches[bailiff_id] = {'bailiff': bailiff_lookup[match_text], 'scores': []}
            all_matches[bailiff_id]['scores'].append(('token_sort', score))
            
        for match_text, score, _ in matches_partial:
            bailiff_id = bailiff_lookup[match_text].id
            if bailiff_id not in all_matches:
                all_matches[bailiff_id] = {'bailiff': bailiff_lookup[match_text], 'scores': []}
            all_matches[bailiff_id]['scores'].append(('partial', score))
    
    print(f"✅ DEBUG run_matching: Znaleziono {len(all_matches)} unikalnych kandydatów")
    
    suggestions = []
    
    for bailiff_id, match_data in all_matches.items():
        bailiff = match_data['bailiff']
        scores = match_data['scores']
        
        # Calculate best scores for each algorithm
        best_ratio = max([s[1] for s in scores if s[0] == 'ratio'], default=0)
        best_token_sort = max([s[1] for s in scores if s[0] == 'token_sort'], default=0)
        best_partial = max([s[1] for s in scores if s[0] == 'partial'], default=0)
        
        # Use the best overall fullname score
        fullname_score = max(best_ratio, best_token_sort, best_partial)
        
        # Skip very low scores
        if fullname_score < 40:
            continue
        
        # Calculate individual component scores
        lastname_score = 0.0
        firstname_score = 0.0
        
        if raw_name.extracted_lastname and bailiff.normalized_lastname:
            # Use multiple algorithms for lastname too
            lastname_ratio = fuzz.ratio(raw_name.extracted_lastname.lower(), bailiff.normalized_lastname.lower())
            lastname_partial = fuzz.partial_ratio(raw_name.extracted_lastname.lower(), bailiff.normalized_lastname.lower())
            lastname_score = max(lastname_ratio, lastname_partial)
        
        if raw_name.extracted_firstname and bailiff.normalized_firstname:
            # Use multiple algorithms for firstname too
            firstname_ratio = fuzz.ratio(raw_name.extracted_firstname.lower(), bailiff.normalized_firstname.lower())
            firstname_partial = fuzz.partial_ratio(raw_name.extracted_firstname.lower(), bailiff.normalized_firstname.lower())
            firstname_score = max(firstname_ratio, firstname_partial)
        
        # Calculate city score
        city_score = calculate_city_score(raw_name.source_city, bailiff.original_miasto)
        
        # Improved combined score calculation with proper weights (max 100%)
        combined_score = (
            fullname_score * 0.5 +      # 50% weight for full name
            lastname_score * 0.25 +     # 25% weight for last name  
            firstname_score * 0.15 +    # 15% weight for first name
            city_score * 0.1           # 10% weight for city
        )
        
        # City bonus as multiplier (up to 10% boost for excellent city match)
        city_multiplier = 1.0
        if city_bonus and city_score >= 80:
            city_multiplier = 1.1  # 10% boost
        elif city_bonus and city_score >= 60:
            city_multiplier = 1.05  # 5% boost
        
        # Algorithm bonus as multiplier for better algorithms
        algorithm_multiplier = 1.0
        if best_token_sort > best_ratio:
            algorithm_multiplier = 1.05  # 5% boost
            algorithm_used = 'rapidfuzz_token_sort_ratio'
        elif best_partial > best_ratio:
            algorithm_multiplier = 1.03  # 3% boost
            algorithm_used = 'rapidfuzz_partial_ratio'
        else:
            algorithm_used = 'rapidfuzz_ratio'
        
        # Apply multipliers and cap at 100%
        combined_score = combined_score * city_multiplier * algorithm_multiplier
        combined_score = min(combined_score, 100.0)  # Cap at 100%
        
        # Determine confidence level with improved thresholds
        if combined_score >= 85:
            confidence = 'high'
        elif combined_score >= 65:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        if len(suggestions) < 3:  # Debug first few suggestions
            print(f"🔍 DEBUG run_matching: Sugestia dla '{bailiff.original_nazwisko}': fullname={fullname_score:.1f}, combined={combined_score:.1f}, confidence={confidence}")
        
        suggestion = MatchSuggestions(
            raw_id=raw_name.id,
            bailiff_id=bailiff.id,
            session_id=session_id,
            fullname_score=fullname_score,
            lastname_score=lastname_score,
            firstname_score=firstname_score,
            city_score=city_score,
            combined_score=combined_score,
            algorithm_used=algorithm_used,
            confidence_level=confidence
        )
        
        suggestions.append(suggestion)
    
    # Sort by combined score
    suggestions.sort(key=lambda x: x.combined_score, reverse=True)
    print(f"✅ DEBUG run_matching: Wygenerowano {len(suggestions)} sugestii dla '{raw_name.raw_text}'")
    
    # Return top 5 suggestions
    final_suggestions = suggestions[:5]
    if final_suggestions:
        print(f"🔍 DEBUG run_matching: Najlepsza sugestia: wynik={final_suggestions[0].combined_score:.1f}")
    
    return final_suggestions

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
