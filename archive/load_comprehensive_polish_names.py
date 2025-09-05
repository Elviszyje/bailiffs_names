#!/usr/bin/env python3
"""
Pełny skrypt do wczytania polskich imion i nazwisk z plików XLSX
i aktualizacji algorytmu ekstrakcji
"""

import pandas as pd
import os
import pickle

def load_comprehensive_polish_names():
    """Load all Polish names from XLSX files"""
    files_dir = "/Users/bartoszkolek/Desktop/cloud/Projekty/bailiffs_names/files"
    
    # File paths
    male_names_file = os.path.join(files_dir, "10_-_Wykaz_imion_męskich_osób_żyjących_wg_pola_imię_drugie_występujących_w_rejestrze_PESEL_bez_zgonów.xlsx")
    female_names_file = os.path.join(files_dir, "10_-_Wykaz_imion_żeńskich_osób_żyjących_wg_pola_imię_drugie_występujących_w_rejestrze_PESEL_bez_zgonów.xlsx")
    male_surnames_file = os.path.join(files_dir, "nazwiska_męskie-z_uwzględnieniem_osób_zmarłych.xlsx")
    female_surnames_file = os.path.join(files_dir, "nazwiska_żeńskie-z_uwzględnieniem_osób_zmarłych.xlsx")
    
    all_first_names = set()
    all_surnames = set()
    
    print("=== WCZYTYWANIE KOMPLETNYCH DANYCH Z REJESTRU PESEL ===")
    
    # Load male first names
    print("Wczytywanie wszystkich imion męskich...")
    try:
        df_male_names = pd.read_excel(male_names_file)
        names = df_male_names['IMIĘ_DRUGIE'].dropna().astype(str)
        names = [name.strip().title() for name in names if name.strip()]
        all_first_names.update(names)
        print(f"  Wczytano {len(names)} imion męskich")
    except Exception as e:
        print(f"  BŁĄD: {e}")
    
    # Load female first names
    print("Wczytywanie wszystkich imion żeńskich...")
    try:
        df_female_names = pd.read_excel(female_names_file)
        names = df_female_names['IMIĘ_DRUGIE'].dropna().astype(str)
        names = [name.strip().title() for name in names if name.strip()]
        all_first_names.update(names)
        print(f"  Wczytano {len(names)} imion żeńskich")
    except Exception as e:
        print(f"  BŁĄD: {e}")
    
    # Load male surnames
    print("Wczytywanie wszystkich nazwisk męskich...")
    try:
        df_male_surnames = pd.read_excel(male_surnames_file)
        surnames = df_male_surnames['Nawisko aktualne'].dropna().astype(str)
        surnames = [surname.strip().title() for surname in surnames if surname.strip()]
        all_surnames.update(surnames)
        print(f"  Wczytano {len(surnames)} nazwisk męskich")
    except Exception as e:
        print(f"  BŁĄD: {e}")
    
    # Load female surnames
    print("Wczytywanie wszystkich nazwisk żeńskich...")
    try:
        df_female_surnames = pd.read_excel(female_surnames_file)
        surnames = df_female_surnames['Nawisko aktualne'].dropna().astype(str)
        surnames = [surname.strip().title() for surname in surnames if surname.strip()]
        all_surnames.update(surnames)
        print(f"  Wczytano {len(surnames)} nazwisk żeńskich")
    except Exception as e:
        print(f"  BŁĄD: {e}")
    
    # Add some common diminutives and variations
    print("Dodawanie powszechnych zdrobnień i wariantów...")
    common_variations = {
        'Jan': ['Janek', 'Jasiek', 'Jaś'],
        'Anna': ['Ania', 'Anka'],
        'Katarzyna': ['Kasia', 'Kaska'],
        'Magdalena': ['Magda'],
        'Małgorzata': ['Gosia', 'Gośka'],
        'Stanisław': ['Stasiek', 'Stas'],
        'Paweł': ['Pawelek'],
        'Piotr': ['Piotrek'],
        'Adam': ['Adaś'],
        'Tomasz': ['Tomek'],
        'Marek': ['Mareczek'],
        'Krzysztof': ['Krzysiek'],
        'Michał': ['Michałek', 'Misiek'],
        'Maciej': ['Maciek'],
        'Agnieszka': ['Aga'],
        'Barbara': ['Basia', 'Baska'],
        'Teresa': ['Tereska'],
        'Elżbieta': ['Ela', 'Elka'],
        'Ewa': ['Ewka']
    }
    
    for base_name, variations in common_variations.items():
        if base_name in all_first_names:
            all_first_names.update(variations)
    
    print(f"\n=== PODSUMOWANIE KOŃCOWE ===")
    print(f"Łączna liczba imion: {len(all_first_names)}")
    print(f"Łączna liczba nazwisk: {len(all_surnames)}")
    
    # Test problematycznych przypadków
    test_cases = ['Maciej', 'Pucko', 'Ryszard', 'Michałek', 'Ada', 'Czapla-Lisowska', 'Kowalski', 'Nowak']
    print(f"\nTest kluczowych przypadków:")
    for case in test_cases:
        in_first = case in all_first_names
        in_surnames = case in all_surnames
        print(f"  {case}: imię={in_first}, nazwisko={in_surnames}")
    
    # Save to pickle files for fast loading
    print(f"\nZapis do plików cache...")
    with open('polish_first_names_full.pkl', 'wb') as f:
        pickle.dump(all_first_names, f)
    with open('polish_surnames_full.pkl', 'wb') as f:
        pickle.dump(all_surnames, f)
    
    print(f"Zapisano pliki cache: polish_first_names_full.pkl, polish_surnames_full.pkl")
    
    return all_first_names, all_surnames

def create_name_recognition_module():
    """Create a module for name recognition"""
    
    module_content = '''"""
Moduł rozpoznawania polskich imion i nazwisk
Wykorzystuje kompletne dane z rejestru PESEL
"""

import pickle
import os

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
        'ul', 'ulica', 'al', 'aleja', 'pl', 'plac', 'os', 'osiedle'
    }
    
    found_first_names = []
    found_surnames = []
    
    for word in words:
        clean_word = word.strip('.,()[]{}";:')
        
        # Skip institutional words
        if clean_word.lower() in institutional_words:
            continue
            
        # Skip short words (less than 2 characters)
        if len(clean_word) < 2:
            continue
            
        # Check if it's a first name
        if clean_word.title() in first_names:
            found_first_names.append(clean_word.title())
            
        # Check if it's a surname
        if clean_word.title() in surnames:
            found_surnames.append(clean_word.title())
    
    # Join found names
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
'''
    
    with open('polish_names_recognition.py', 'w', encoding='utf-8') as f:
        f.write(module_content)
    
    print("Utworzono moduł: polish_names_recognition.py")

if __name__ == "__main__":
    # Load comprehensive data
    first_names, surnames = load_comprehensive_polish_names()
    
    # Create recognition module
    create_name_recognition_module()
    
    print(f"\n✅ GOTOWE! Wczytano {len(first_names)} imion i {len(surnames)} nazwisk z rejestru PESEL")
