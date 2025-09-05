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

from scripts.add_session_support import AnalysisSession, Base
from scripts.run_matching import RawNames, BailiffDict, MatchSuggestions

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
    engine = create_engine('sqlite:///bailiffs_matching.db', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        # Update session status
        analysis_session = db_session.query(AnalysisSession).get(session_id)
        if not analysis_session:
            return False, "Session not found"
        
        analysis_session.status = 'processing'
        db_session.commit()
        
        # Read file based on extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
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
            return False, f"Unsupported file format: {file_ext}"
        
        # Update file stats
        analysis_session.file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        analysis_session.total_records = len(df)
        db_session.commit()
        
        # Import records
        imported_count = 0
        
        for row_num, (index, row) in enumerate(df.iterrows(), start=2):  # Start from row 2 (after header)
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
                
                # Commit in batches
                if imported_count % 100 == 0:
                    db_session.commit()
        
        # Final commit
        db_session.commit()
        
        # Update session stats
        analysis_session.processed_records = imported_count
        analysis_session.status = 'imported'
        db_session.commit()
        
        return True, f"Successfully imported {imported_count} records"
        
    except Exception as e:
        db_session.rollback()
        # Update session status to error
        try:
            if 'analysis_session' in locals():
                analysis_session.status = 'error'
                db_session.commit()
        except:
            pass
        return False, f"Error processing file: {e}"
    finally:
        db_session.close()

def get_sessions_list():
    """Get list of all analysis sessions."""
    engine = create_engine('sqlite:///bailiffs_matching.db', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        sessions = db_session.query(AnalysisSession).order_by(AnalysisSession.created_at.desc()).all()
        
        sessions_data = []
        for session in sessions:
            # Get matching stats
            total_suggestions = db_session.query(MatchSuggestions).filter(MatchSuggestions.session_id == session.id).count()
            
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

if __name__ == "__main__":
    # Test the functionality
    sessions = get_sessions_list()
    print(f"Found {len(sessions)} sessions:")
    for session in sessions:
        print(f"- {session['session_name']}: {session['total_records']} records, status: {session['status']}")
