#!/usr/bin/env python3
"""
Simple import script without complex dependencies.
"""

import pandas as pd
import re
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Simple database models
Base = declarative_base()

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

def normalize_name_simple(text):
    """Simple normalization function for names."""
    if not text or pd.isna(text):
        return ""
    
    # Convert to string and basic cleanup
    text = str(text).strip()
    
    # Remove common titles and formulas
    patterns_to_remove = [
        r'komornik\s+sądowy\s+przy\s+sądzie',
        r'zastępca\s+komornika\s+sądowego\s+przy\s+sądzie',
        r'kancelaria\s+komornicza\s+nr\s+[ivx]+',
        r'dr\s+hab\.?',
        r'prof\.?\s+dr\s+hab\.?',
        r'mgr\.?',
        r'przy\s+sądzie\s+\w+',
        r'w\s+[A-ZĄĆĘŁŃÓŚŹŻ]\w+',
        r'nr\s+[ivx]+',
        r'kancelaria\s+w\s+likwidacji',
    ]
    
    result = text.lower()
    for pattern in patterns_to_remove:
        result = re.sub(pattern, ' ', result, flags=re.IGNORECASE)
    
    # Remove Polish characters
    polish_chars = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
    }
    for polish_char, latin_char in polish_chars.items():
        result = result.replace(polish_char, latin_char)
    
    # Clean up spaces and punctuation
    result = re.sub(r'[^\w\s]', ' ', result)
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result

def extract_name_parts(normalized_text):
    """Extract first name and last name from normalized text."""
    if not normalized_text:
        return None, None
    
    # Split into tokens
    tokens = normalized_text.split()
    
    if not tokens:
        return None, None
    
    # Simple heuristic: first token is first name, last token is last name
    if len(tokens) == 1:
        return None, tokens[0]
    elif len(tokens) == 2:
        return tokens[0], tokens[1]
    else:
        # Multiple names - first token as first name, last token as last name
        return tokens[0], tokens[-1]

def setup_database():
    """Setup database connection and create tables."""
    print("🔧 Konfiguracja bazy danych...")
    
    # Use SQLite
    database_url = "sqlite:///bailiffs_matching.db"
    engine = create_engine(database_url, echo=False)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    print("✅ Baza danych skonfigurowana (SQLite)")
    return engine, SessionLocal

def import_target_dictionary(session_class):
    """Import komornicy.xlsx as target bailiff dictionary."""
    print("📖 Importuję słownik docelowy (komornicy.xlsx)...")
    
    df = pd.read_excel('files/komornicy.xlsx')
    session = session_class()
    
    imported = 0
    skipped = 0
    batch_size = 100
    
    try:
        for index, row in df.iterrows():
            nazwa_komornika = row.get('nazwa_komornika')
            if pd.notna(nazwa_komornika) and str(nazwa_komornika).strip():
                
                # Extract and normalize data
                full_name = str(nazwa_komornika).strip()
                normalized_name = normalize_name_simple(full_name)
                first_name, last_name = extract_name_parts(normalized_name)
                
                # Extract city info
                miasto = str(row.get('miasto', '')).strip() if pd.notna(row.get('miasto')) else ''
                normalized_city = normalize_name_simple(miasto)
                
                # Create database record
                bailiff_record = BailiffDict(
                    original_nazwisko=full_name,
                    original_imie='',  # Names are combined in this dataset
                    original_miasto=miasto,
                    original_sad=str(row.get('sad', '')).strip() if pd.notna(row.get('sad')) else '',
                    adres=str(row.get('adres', '')).strip() if pd.notna(row.get('adres')) else '',
                    kod_pocztowy=str(row.get('kod_pocztowy', '')).strip() if pd.notna(row.get('kod_pocztowy')) else '',
                    telefon=str(row.get('telefon', '')).strip() if pd.notna(row.get('telefon')) else '',
                    email=str(row.get('email', '')).strip() if pd.notna(row.get('email')) else '',
                    bank=str(row.get('bank', '')).strip() if pd.notna(row.get('bank')) else '',
                    numer_konta=str(row.get('numer_konta', '')).strip() if pd.notna(row.get('numer_konta')) else '',
                    normalized_lastname=last_name or '',
                    normalized_firstname=first_name or '',
                    normalized_fullname=normalized_name,
                    normalized_city=normalized_city
                )
                
                session.add(bailiff_record)
                imported += 1
                
                if imported % batch_size == 0:
                    session.commit()
                    print(f"   Postęp: {imported}/{len(df)}")
            else:
                skipped += 1
        
        session.commit()
        print(f"✅ Słownik docelowy zaimportowany: {imported} rekordów (pominięto: {skipped})")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Błąd podczas importu słownika: {e}")
        raise
    finally:
        session.close()
    
    return imported

def import_source_names(session_class):
    """Import kom.csv as raw names to be matched."""
    print("📝 Importuję listę do mapowania (kom.csv)...")
    
    df = pd.read_csv('files/kom.csv')
    session = session_class()
    
    imported = 0
    skipped = 0
    batch_size = 100
    
    try:
        for index, row in df.iterrows():
            name = row.get('name')
            if pd.notna(name) and str(name).strip():
                
                # Extract and normalize data
                raw_text = str(name).strip()
                normalized_text = normalize_name_simple(raw_text)
                first_name, last_name = extract_name_parts(normalized_text)
                
                # Processing notes
                processing_notes = []
                if len(normalized_text.split()) > 2:
                    processing_notes.append(f"Multiple name parts detected: {len(normalized_text.split())}")
                if not last_name:
                    processing_notes.append("No lastname extracted")
                
                # Create database record
                raw_record = RawNames(
                    source_file='files/kom.csv',
                    source_sheet='default',
                    source_row=int(index) + 2,  # +2 for header and 0-based index
                    source_column='name',
                    raw_text=raw_text,
                    normalized_text=normalized_text,
                    extracted_lastname=last_name,
                    extracted_firstname=first_name,
                    processing_notes='; '.join(processing_notes) if processing_notes else None,
                    is_processed=True,
                    # Additional fields from CSV
                    source_city=str(row.get('address_city', '')).strip() if pd.notna(row.get('address_city')) else '',
                    source_email=str(row.get('email', '')).strip() if pd.notna(row.get('email')) else '',
                    source_phone=str(row.get('phone_number', '')).strip() if pd.notna(row.get('phone_number')) else '',
                    source_address=str(row.get('address_street', '')).strip() if pd.notna(row.get('address_street')) else ''
                )
                
                session.add(raw_record)
                imported += 1
                
                if imported % batch_size == 0:
                    session.commit()
                    print(f"   Postęp: {imported}/{len(df)}")
            else:
                skipped += 1
        
        session.commit()
        print(f"✅ Lista do mapowania zaimportowana: {imported} rekordów (pominięto: {skipped})")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Błąd podczas importu listy: {e}")
        raise
    finally:
        session.close()
    
    return imported

def show_import_summary(session_class):
    """Show summary of imported data."""
    print("\n📊 Podsumowanie importu:")
    
    session = session_class()
    try:
        # Count records
        bailiff_count = session.query(BailiffDict).count()
        raw_count = session.query(RawNames).count()
        
        print(f"   Słownik docelowy: {bailiff_count} komorników")
        print(f"   Lista do mapowania: {raw_count} nazw")
        
        # Show some examples
        print(f"\n📖 Przykłady ze słownika docelowego:")
        bailiffs = session.query(BailiffDict).limit(3).all()
        for i, bailiff in enumerate(bailiffs, 1):
            print(f"   {i}. {bailiff.original_nazwisko}")
            print(f"      Znormalizowane: {bailiff.normalized_fullname}")
            print(f"      Miasto: {bailiff.original_miasto}")
        
        print(f"\n📝 Przykłady z listy do mapowania:")
        raw_names = session.query(RawNames).limit(3).all()
        for i, raw in enumerate(raw_names, 1):
            print(f"   {i}. {raw.raw_text}")
            print(f"      Znormalizowane: {raw.normalized_text}")
            print(f"      Miasto: {raw.source_city}")
        
    finally:
        session.close()

def main():
    """Main import process."""
    print("🚀 Import danych z dostarczonych plików")
    print("=" * 50)
    
    try:
        # Setup database
        engine, session_class = setup_database()
        
        # Import target dictionary
        dict_count = import_target_dictionary(session_class)
        
        # Import source names
        raw_count = import_source_names(session_class)
        
        # Show summary
        show_import_summary(session_class)
        
        print(f"\n🎉 Import zakończony pomyślnie!")
        print(f"   Zaimportowano łącznie: {dict_count + raw_count} rekordów")
        print(f"   Baza danych: bailiffs_matching.db")
        print(f"\nNastępne kroki:")
        print("1. Uruchom algorytm dopasowywania")
        print("2. Przejrzyj sugerowane dopasowania w aplikacji Streamlit")
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
