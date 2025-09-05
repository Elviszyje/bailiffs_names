"""
File upload and processing functionality for multi-session support.
"""

import pandas as pd
import os
import re
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
sys.path.append('.')
sys.path.append('scripts')

# Import database models from app.py structure
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class AnalysisSession(Base):
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

class RawNames(Base):
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

class BailiffDict(Base):
    __tablename__ = 'bailiffs_dict'
    id = Column(Integer, primary_key=True)
    original_nazwisko = Column(Text, nullable=False)
    original_imie = Column(String(100), nullable=True)
    original_miasto = Column(String(100), nullable=True)
    original_sad = Column(Text, nullable=True)
    adres = Column(Text, nullable=True)
    kod_pocztowy = Column(String(20), nullable=True)
    telefon = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    normalized_lastname = Column(String(100), nullable=True)
    normalized_firstname = Column(String(100), nullable=True)
    normalized_city = Column(String(100), nullable=True)
    bank = Column(String(200), nullable=True)
    numer_konta = Column(String(100), nullable=True)
    normalized_fullname = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

class MatchSuggestions(Base):
    __tablename__ = 'match_suggestions'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('analysis_sessions.id'), nullable=True)
    raw_id = Column(Integer, ForeignKey('raw_names.id'), nullable=False)
    bailiff_id = Column(Integer, ForeignKey('bailiffs_dict.id'), nullable=False)
    fullname_score = Column(Float, nullable=False)
    lastname_score = Column(Float, nullable=True)
    firstname_score = Column(Float, nullable=True)
    city_score = Column(Float, nullable=True)
    combined_score = Column(Float, nullable=False)
    algorithm_used = Column(String(50), nullable=False)
    confidence_level = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    raw_name = relationship("RawNames", backref="suggestions")
    bailiff = relationship("BailiffDict", backref="suggestions")

class NameMappings(Base):
    __tablename__ = 'name_mappings'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('analysis_sessions.id'), nullable=True)
    raw_id = Column(Integer, ForeignKey('raw_names.id'), nullable=False)
    bailiff_id = Column(Integer, ForeignKey('bailiffs_dict.id'), nullable=True)
    mapping_type = Column(String(20), nullable=False)  # 'accepted', 'rejected', 'manual_new'
    confidence_level = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, default=func.now(), nullable=False)

def normalize_name_simple(text):
    """Simple normalization function."""
    if not text or pd.isna(text):
        return ""
    
    # Convert to string and basic cleanup
    text = str(text).strip()
    
    # Remove common titles and formulas
    patterns_to_remove = [
        r'komornik\s+sądowy\s+przy\s+sądzie',
        r'kancelaria\s+komornicza\s+nr\s+[ivx]+',
        r'dr\s+hab\.?',
        r'prof\.?\s+dr\s+hab\.?',
        r'mgr\.?',
        r'przy\s+sądzie\s+\w+',
        r'w\s+[A-ZĄĆĘŁŃÓŚŹŻ]\w+',
        r'nr\s+[ivx]+',
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

def create_analysis_session(session_name, filename, description=""):
    """Create a new analysis session."""
    engine = create_engine('sqlite:///bailiffs_matching.db', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        # Check if session name already exists
        existing = db_session.query(AnalysisSession).filter(AnalysisSession.session_name == session_name).first()
        if existing:
            return None, f"Session '{session_name}' already exists"
        
        # Create new session
        new_session = AnalysisSession(
            session_name=session_name,
            description=description,
            original_filename=filename,
            status='uploaded'
        )
        
        db_session.add(new_session)
        db_session.commit()
        
        return new_session.id, "Session created successfully"
        
    except Exception as e:
        db_session.rollback()
        return None, f"Error creating session: {e}"
    finally:
        db_session.close()

def process_uploaded_file(file_path, session_id, sheet_name=None):
    """Process uploaded file and import to specific session."""
    print(f"🔍 DEBUG file_upload: Rozpoczynanie przetwarzania pliku: {file_path}")
    print(f"🔍 DEBUG file_upload: Session ID: {session_id}, Sheet: {sheet_name}")
    
    engine = create_engine('sqlite:///bailiffs_matching.db', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        # Update session status
        print(f"🔍 DEBUG file_upload: Szukanie sesji o ID {session_id}...")
        analysis_session = db_session.query(AnalysisSession).get(session_id)
        if not analysis_session:
            print(f"❌ DEBUG file_upload: Nie znaleziono sesji o ID {session_id}")
            return False, "Session not found"
        print(f"✅ DEBUG file_upload: Znaleziono sesję: {analysis_session.session_name}")
        
        analysis_session.status = 'processing'
        db_session.commit()
        print("✅ DEBUG file_upload: Status sesji zmieniony na 'processing'")
        
        # Read file based on extension
        file_ext = os.path.splitext(file_path)[1].lower()
        print(f"🔍 DEBUG file_upload: Rozszerzenie pliku: {file_ext}")
        
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                # Get first sheet
                excel_file = pd.ExcelFile(file_path)
                sheet_name = excel_file.sheet_names[0]
                df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            print(f"❌ DEBUG file_upload: Nieobsługiwane rozszerzenie: {file_ext}")
            return False, f"Unsupported file format: {file_ext}"
        
        print(f"✅ DEBUG file_upload: Wczytano DataFrame z {len(df)} wierszami i {len(df.columns)} kolumnami")
        print(f"🔍 DEBUG file_upload: Kolumny: {list(df.columns)}")
        
        # Update file stats
        analysis_session.file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        analysis_session.total_records = len(df)
        db_session.commit()
        print(f"✅ DEBUG file_upload: Zaktualizowano statystyki sesji - rozmiar: {analysis_session.file_size}, rekordy: {analysis_session.total_records}")
        
        # Import records
        imported_count = 0
        print("🔍 DEBUG file_upload: Rozpoczynanie importu rekordów...")
        
        for row_num, (index, row) in enumerate(df.iterrows(), start=2):  # Start from row 2 (after header)
            if row_num <= 5:  # Debug first 5 rows
                print(f"🔍 DEBUG file_upload: Przetwarzanie wiersza {row_num}: {dict(row)}")
            
            # Try to find name-like columns
            name_text = ""
            city_text = ""
            email_text = ""
            phone_text = ""
            address_text = ""
            
            # Look for common column names
            for col in df.columns:
                col_lower = str(col).lower()
                value = str(row[col]) if pd.notna(row[col]) else ""
                
                if any(name_keyword in col_lower for name_keyword in ['nazwa', 'name', 'komornik', 'bailiff', 'nazwisko']):
                    if not name_text and value:
                        name_text = value
                elif any(city_keyword in col_lower for city_keyword in ['miasto', 'city', 'miejscowosc']):
                    if not city_text and value:
                        city_text = value
                elif any(email_keyword in col_lower for email_keyword in ['email', 'e-mail', 'mail']):
                    if not email_text and value:
                        email_text = value
                elif any(phone_keyword in col_lower for phone_keyword in ['telefon', 'phone', 'tel']):
                    if not phone_text and value:
                        phone_text = value
                elif any(addr_keyword in col_lower for addr_keyword in ['adres', 'address', 'ulica']):
                    if not address_text and value:
                        address_text = value
            
            # If no specific name column found, use first non-empty column
            if not name_text:
                for col in df.columns:
                    value = str(row[col]) if pd.notna(row[col]) else ""
                    if value and value != 'nan':
                        name_text = value
                        break
            
            if name_text and name_text != 'nan':
                # Normalize name
                normalized = normalize_name_simple(name_text)
                
                # Extract potential first/last names
                lastname = ""
                firstname = ""
                
                # Look for actual person names in bailiff text
                if "Komornik" in name_text and "Sądowy" in name_text:
                    # Extract names using improved pattern matching
                    import re
                    
                    # Skip common institutional words and city indicators
                    institutional_words = {
                        'Komornik', 'Sądowy', 'przy', 'Sądzie', 'Rejonowym', 'dla', 'w', 'nr', 
                        'Kancelaria', 'Komornicza', 'Okręgowym', 'Gospodarczym', 'Pracy',
                        'Wojewódzkim', 'Apelacyjnym', 'Najwyższym', 'Grójcu', 'Łodzi', 'Krakowie',
                        'Warszawie', 'Poznaniu', 'Wrocławiu', 'Gdańsku', 'Katowicach'
                    }
                    
                    words = name_text.split()
                    potential_names = []
                    
                    # Look for Polish first names (common patterns)
                    polish_first_names = {
                        'Ada', 'Anna', 'Katarzyna', 'Maria', 'Agnieszka', 'Małgorzata', 'Joanna', 'Barbara',
                        'Jan', 'Piotr', 'Krzysztof', 'Andrzej', 'Tomasz', 'Paweł', 'Michał', 'Adam',
                        'Dominika', 'Kinga', 'Monika', 'Beata', 'Ewa', 'Magdalena', 'Aleksandra',
                        'Marcin', 'Jakub', 'Dawid', 'Łukasz', 'Mateusz', 'Kamil', 'Rafał'
                    }
                    
                    i = 0
                    while i < len(words):
                        word = words[i].strip('.,')
                        # Check if this looks like a Polish first name
                        if word in polish_first_names:
                            # Collect the name sequence starting from this first name
                            name_sequence = [word]
                            j = i + 1
                            
                            # Collect following capitalized words that could be surnames
                            while (j < len(words) and j < i + 4):
                                next_word = words[j].strip('.,')
                                if (next_word and 
                                    next_word[0].isupper() and
                                    next_word not in institutional_words and
                                    not next_word.isdigit() and
                                    len(next_word) > 1):
                                    name_sequence.append(next_word)
                                    j += 1
                                else:
                                    break
                            
                            if len(name_sequence) >= 2:  # At least first + last name
                                potential_names.append(name_sequence)
                            i = j
                        else:
                            i += 1
                    
                    # Take the most likely name sequence (longest one with 2-3 words)
                    best_name = None
                    for seq in potential_names:
                        if 2 <= len(seq) <= 3:  # Typical Polish name length
                            if not best_name or len(seq) > len(best_name):
                                best_name = seq
                    
                    if best_name:
                        firstname = best_name[0]
                        if len(best_name) == 2:
                            lastname = best_name[1]
                        else:  # 3 words - assume middle name or hyphenated surname
                            lastname = " ".join(best_name[1:])
                    
                else:
                    # Simple first/last name extraction for non-bailiff text
                    name_parts = name_text.split()
                    if len(name_parts) >= 2:
                        firstname = name_parts[0]
                        lastname = name_parts[-1]
                
                # Create RawNames record
                if imported_count < 3:  # Debug first 3 records
                    print(f"🔍 DEBUG file_upload: Tworzenie RawNames #{imported_count+1} z session_id={session_id}")
                    print(f"🔍 DEBUG file_upload: name_text='{name_text}', normalized='{normalized}'")
                    print(f"🔍 DEBUG file_upload: lastname='{lastname}', firstname='{firstname}'")
                
                raw_record = RawNames(
                    session_id=session_id,
                    source_file=os.path.basename(file_path),
                    source_sheet=sheet_name,
                    source_row=row_num,  # Use row_num instead of index
                    source_column="auto-detected",
                    raw_text=name_text,
                    normalized_text=normalized,
                    extracted_lastname=lastname,
                    extracted_firstname=firstname,
                    source_city=city_text if city_text else None,
                    source_email=email_text if email_text else None,
                    source_phone=phone_text if phone_text else None,
                    source_address=address_text if address_text else None,
                    is_processed=False
                )
                
                db_session.add(raw_record)
                imported_count += 1
                
                if imported_count < 3:  # Debug first 3 records
                    print(f"✅ DEBUG file_upload: Dodano rekord #{imported_count} do sesji bazy danych")
                
                # Commit in batches
                if imported_count % 100 == 0:
                    print(f"🔍 DEBUG file_upload: Commit batch - {imported_count} rekordów")
                    db_session.commit()
        
        # Final commit
        print(f"🔍 DEBUG file_upload: Końcowy commit dla {imported_count} rekordów...")
        db_session.commit()
        print("✅ DEBUG file_upload: Commit zakończony pomyślnie")
        
        # Update session stats
        analysis_session.processed_records = imported_count
        analysis_session.status = 'imported'
        db_session.commit()
        print(f"✅ DEBUG file_upload: Zaktualizowano sesję - processed_records: {imported_count}, status: 'imported'")
        
        # Verify records were saved
        saved_count = db_session.query(RawNames).filter(RawNames.session_id == session_id).count()
        print(f"🔍 DEBUG file_upload: Weryfikacja: w bazie znajduje się {saved_count} rekordów dla sesji {session_id}")
        
        return True, f"Przetworzono {imported_count} rekordów z {len(df)} wierszy"
        
    except Exception as e:
        print(f"❌ DEBUG file_upload: Błąd podczas przetwarzania: {e}")
        print(f"❌ DEBUG file_upload: Typ błędu: {type(e).__name__}")
        import traceback
        print(f"❌ DEBUG file_upload: Traceback: {traceback.format_exc()}")
        
        db_session.rollback()
        # Update session status to error
        try:
            if 'analysis_session' in locals():
                analysis_session.status = 'error'
                db_session.commit()
                print("✅ DEBUG file_upload: Status sesji zmieniony na 'error'")
        except Exception as status_error:
            print(f"❌ DEBUG file_upload: Błąd podczas zmiany statusu: {status_error}")
        
        return False, f"Error processing file: {e}"
    finally:
        print("🔍 DEBUG file_upload: Zamykanie sesji bazy danych...")
        db_session.close()
        print("✅ DEBUG file_upload: Sesja zamknięta")

def get_sessions_list():
    """Get list of all analysis sessions."""
    engine = create_engine('sqlite:///bailiffs_matching.db', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        sessions = db_session.query(AnalysisSession).order_by(AnalysisSession.created_at.desc()).all()
        
        sessions_data = []
        for session in sessions:
            # Note: MatchSuggestions is imported from run_matching.py which is not available here
            # For now, set total_suggestions to 0 
            total_suggestions = 0
            
            sessions_data.append({
                'id': session.id,
                'session_name': session.session_name,
                'description': session.description,
                'filename': session.original_filename,
                'total_records': session.total_records,
                'processed_records': session.processed_records,
                'matched_records': session.matched_records,
                'total_suggestions': total_suggestions,
                'status': session.status,
                'created_at': session.created_at,
                'updated_at': session.updated_at
            })
        
        return sessions_data
        
    finally:
        db_session.close()


def delete_session(session_id):
    """Delete a complete analysis session and all related data."""
    engine = create_engine('sqlite:///bailiffs_matching.db', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        # First get session info for logging
        session = db_session.query(AnalysisSession).filter_by(id=session_id).first()
        if not session:
            return False, f"Sesja o ID {session_id} nie została znaleziona"
        
        session_name = session.session_name
        print(f"🗑️ Usuwanie sesji: {session_name} (ID: {session_id})")
        
        # Delete related data in proper order (to handle foreign key constraints)
        
        # 1. Delete name mappings
        mappings_deleted = db_session.query(NameMappings).filter_by(session_id=session_id).count()
        db_session.query(NameMappings).filter_by(session_id=session_id).delete()
        print(f"   ✅ Usunięto {mappings_deleted} mapowań nazw")
        
        # 2. Delete match suggestions  
        suggestions_deleted = db_session.query(MatchSuggestions).filter_by(session_id=session_id).count()
        db_session.query(MatchSuggestions).filter_by(session_id=session_id).delete()
        print(f"   ✅ Usunięto {suggestions_deleted} sugestii dopasowań")
        
        # 3. Delete raw names
        raw_names_deleted = db_session.query(RawNames).filter_by(session_id=session_id).count()
        db_session.query(RawNames).filter_by(session_id=session_id).delete()
        print(f"   ✅ Usunięto {raw_names_deleted} surowych nazw")
        
        # 4. Finally delete the session itself
        db_session.query(AnalysisSession).filter_by(id=session_id).delete()
        print(f"   ✅ Usunięto sesję analizy")
        
        db_session.commit()
        print(f"🎉 Sesja '{session_name}' została całkowicie usunięta")
        
        return True, f"Sesja '{session_name}' została pomyślnie usunięta"
        
    except Exception as e:
        db_session.rollback()
        error_msg = f"Błąd podczas usuwania sesji: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
        
    finally:
        db_session.close()


def delete_all_sessions():
    """Delete all analysis sessions and related data (complete cleanup)."""
    engine = create_engine('sqlite:///bailiffs_matching.db', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        # Get count of all sessions first
        total_sessions = db_session.query(AnalysisSession).count()
        if total_sessions == 0:
            return True, "Brak sesji do usunięcia"
            
        print(f"🗑️ Usuwanie wszystkich {total_sessions} sesji...")
        
        # Delete all related data
        mappings_deleted = db_session.query(NameMappings).count()
        db_session.query(NameMappings).delete()
        print(f"   ✅ Usunięto {mappings_deleted} mapowań nazw")
        
        suggestions_deleted = db_session.query(MatchSuggestions).count()
        db_session.query(MatchSuggestions).delete()
        print(f"   ✅ Usunięto {suggestions_deleted} sugestii dopasowań")
        
        raw_names_deleted = db_session.query(RawNames).count()
        db_session.query(RawNames).delete()
        print(f"   ✅ Usunięto {raw_names_deleted} surowych nazw")
        
        # Delete all sessions
        db_session.query(AnalysisSession).delete()
        print(f"   ✅ Usunięto {total_sessions} sesji analizy")
        
        db_session.commit()
        print(f"🎉 Wszystkie sesje zostały całkowicie usunięte")
        
        return True, f"Wszystkie {total_sessions} sesji zostały pomyślnie usunięte"
        
    except Exception as e:
        db_session.rollback()
        error_msg = f"Błąd podczas usuwania wszystkich sesji: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
        
    finally:
        db_session.close()


if __name__ == "__main__":
    # Test the functionality
    sessions = get_sessions_list()
    print(f"Found {len(sessions)} sessions:")
    for session in sessions:
        print(f"- {session['session_name']}: {session['total_records']} records, status: {session['status']}")
