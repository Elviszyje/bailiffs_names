"""
Moduł rozpoznawania polskich imion i nazwisk
Wykorzystuje kompletne dane z rejestru PESEL
"""

import pickle
import os
import pandas as pd

def load_polish_names():
    """Load cached Polish names"""
    try:
        with open('polish_first_names_full.pkl', 'rb') as f:
            first_names = pickle.load(f)
        with open('polish_surnames_full.pkl', 'rb') as f:
            surnames = pickle.load(f)
        return first_names, surnames
    except FileNotFoundError:
        print("BŁĄD: Brak plików cache z imionami. Uruchom najpierw load_comprehensive_polish_names.py")
        return set(), set()

def is_polish_first_name(name):
    """Check if name is a Polish first name"""
    first_names, _ = load_polish_names()
    return name.title() in first_names

def is_polish_surname(name):
    """Check if name is a Polish surname"""
    _, surnames = load_polish_names()
    return name.title() in surnames

def extract_names_from_bailiff_text_enhanced(text):
    """
    Ulepszona funkcja ekstrakcji imion i nazwisk z tekstu komornika
    Wykorzystuje kompletną bazę polskich imion i nazwisk z rejestru PESEL
    """
    if not text or pd.isna(text):
        return "", ""
    
    first_names, surnames = load_polish_names()
    
    # Clean and split text
    words = str(text).replace(',', ' ').replace('.', ' ').split()
    words = [word.strip() for word in words if word.strip()]
    
    # Common institutional words to ignore
    institutional_words = {
        'komornik', 'sądowy', 'sąd', 'rejonowy', 'okręgowy', 'kancelaria', 'mgr', 'dr', 'prof',
        'adwokat', 'radca', 'prawny', 'licencjat', 'magister', 'doktor', 'profesor',
        'w', 'we', 'z', 'ze', 'i', 'oraz', 'przy', 'dla', 'do', 'od', 'na', 'po',
        'ul', 'ulica', 'al', 'aleja', 'pl', 'plac', 'os', 'osiedle', 'nr', 'numer'
    }
    
    # First pass - identify potential names
    potential_names = []
    for i, word in enumerate(words):
        clean_word = word.strip('.,()[]{}";:')
        
        # Skip institutional words
        if clean_word.lower() in institutional_words:
            continue
            
        # Skip short words (less than 2 characters)
        if len(clean_word) < 2:
            continue
            
        # Check if it's a potential name (either first name or surname)
        is_first_name = clean_word.title() in first_names
        is_surname = clean_word.title() in surnames
        
        if is_first_name or is_surname:
            potential_names.append({
                'word': clean_word.title(),
                'position': i,
                'is_first_name': is_first_name,
                'is_surname': is_surname
            })
    
    # Second pass - smart assignment
    found_first_names = []
    found_surnames = []
    used_positions = set()
    
    # Strategy 1: Look for clear first name + surname patterns
    for i, name in enumerate(potential_names):
        if name['position'] in used_positions:
            continue
            
        # If this is clearly a first name and not commonly a surname
        if name['is_first_name'] and not name['is_surname']:
            found_first_names.append(name['word'])
            used_positions.add(name['position'])
            
            # Look for surname immediately after
            if i + 1 < len(potential_names):
                next_name = potential_names[i + 1]
                if (next_name['position'] == name['position'] + 1 and 
                    next_name['is_surname'] and 
                    next_name['position'] not in used_positions):
                    found_surnames.append(next_name['word'])
                    used_positions.add(next_name['position'])
    
    # Strategy 2: Look for surnames that are clearly not first names
    for name in potential_names:
        if (name['position'] not in used_positions and 
            name['is_surname'] and 
            not name['is_first_name']):
            found_surnames.append(name['word'])
            used_positions.add(name['position'])
    
    # Strategy 3: Handle ambiguous names (both first name and surname)
    for name in potential_names:
        if name['position'] not in used_positions:
            if name['is_first_name'] and name['is_surname']:
                # Prefer as first name if we don't have one yet
                if not found_first_names:
                    found_first_names.append(name['word'])
                elif not found_surnames:
                    found_surnames.append(name['word'])
            elif name['is_first_name']:
                found_first_names.append(name['word'])
            elif name['is_surname']:
                found_surnames.append(name['word'])
    
    # Join found names (limit to reasonable number)
    first_name = ' '.join(found_first_names[:2])  # Max 2 first names
    last_name = ' '.join(found_surnames[:2])      # Max 2 surnames
    
    return first_name, last_name

# For backward compatibility
polish_first_names = None
polish_surnames = None

def initialize_names():
    """Initialize global name sets"""
    global polish_first_names, polish_surnames
    if polish_first_names is None or polish_surnames is None:
        polish_first_names, polish_surnames = load_polish_names()

# Load on import
initialize_names()
