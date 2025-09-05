#!/usr/bin/env python3
"""
Script to analyze provided files and configure the matching system accordingly.
"""

import pandas as pd
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from matching.normalizer import normalizer
from database.models import db_manager, BailiffDict, RawNames
from config import config

def analyze_target_dictionary():
    """Analyze komornicy.xlsx file structure and content."""
    print("🔍 Analizuję plik komornicy.xlsx (słownik docelowy)...")
    
    df = pd.read_excel('files/komornicy.xlsx')
    
    print(f"📊 Statystyki podstawowe:")
    print(f"   Liczba rekordów: {len(df)}")
    print(f"   Kolumny: {list(df.columns)}")
    
    # Analyze nama_komornika column
    if 'nazwa_komornika' in df.columns:
        print(f"\n📝 Analiza kolumny 'nazwa_komornika':")
        name_col = df['nazwa_komornika'].dropna()
        print(f"   Rekordów z nazwami: {len(name_col)}")
        print(f"   Unikalne nazwy: {name_col.nunique()}")
        
        # Sample names
        print(f"\n   Przykładowe nazwy:")
        for i, name in enumerate(name_col.head(5), 1):
            normalized = normalizer.normalize_for_matching(name)
            print(f"   {i}. Oryginał: '{name}'")
            print(f"      Znormalizowane: '{normalized}'")
        
        # Check for patterns
        print(f"\n   Wykryte wzorce:")
        patterns = {
            'Z tytułami': name_col.str.contains(r'(?i)(komornik|sądowy|przy)', na=False).sum(),
            'Z numerami kancelarii': name_col.str.contains(r'nr [IVX]+', na=False).sum(),
            'Ze skrótami sądów': name_col.str.contains(r'(?i)(sąd|rejonowy|okręgowy)', na=False).sum(),
            'Z miastami': name_col.str.contains(r'(?i)(w [A-ZĄĆĘŁŃÓŚŹŻ])', na=False).sum()
        }
        
        for pattern, count in patterns.items():
            percentage = (count / len(name_col)) * 100
            print(f"      {pattern}: {count} ({percentage:.1f}%)")
    
    return df

def analyze_source_list():
    """Analyze kom.csv file structure and content."""
    print("\n🔍 Analizuję plik kom.csv (lista do mapowania)...")
    
    df = pd.read_csv('files/kom.csv')
    
    print(f"📊 Statystyki podstawowe:")
    print(f"   Liczba rekordów: {len(df)}")
    print(f"   Kolumny: {list(df.columns)}")
    
    # Analyze name column
    if 'name' in df.columns:
        print(f"\n📝 Analiza kolumny 'name':")
        name_col = df['name'].dropna()
        print(f"   Rekordów z nazwami: {len(name_col)}")
        print(f"   Unikalne nazwy: {name_col.nunique()}")
        
        # Sample names
        print(f"\n   Przykładowe nazwy:")
        for i, name in enumerate(name_col.head(5), 1):
            normalized = normalizer.normalize_for_matching(name)
            print(f"   {i}. Oryginał: '{name}'")
            print(f"      Znormalizowane: '{normalized}'")
        
        # Check for patterns
        print(f"\n   Wykryte wzorce:")
        patterns = {
            'Z tytułami': name_col.str.contains(r'(?i)(komornik|sądowy|przy)', na=False).sum(),
            'Z numerami kancelarii': name_col.str.contains(r'nr [IVX]+', na=False).sum(),
            'Ze skrótami sądów': name_col.str.contains(r'(?i)(sąd|rejonowy|okręgowy)', na=False).sum(),
            'Z miastami': name_col.str.contains(r'(?i)(w [A-ZĄĆĘŁŃÓŚŹŻ])', na=False).sum()
        }
        
        for pattern, count in patterns.items():
            percentage = (count / len(name_col)) * 100
            print(f"      {pattern}: {count} ({percentage:.1f}%)")
    
    return df

def test_normalization_samples():
    """Test normalization on sample data from both files."""
    print("\n🧪 Testowanie normalizacji na przykładowych danych...")
    
    # Load files
    df_dict = pd.read_excel('files/komornicy.xlsx')
    df_source = pd.read_csv('files/kom.csv')
    
    # Test samples from target dictionary
    print("\n📖 Próbki ze słownika docelowego (komornicy.xlsx):")
    dict_samples = df_dict['nazwa_komornika'].dropna().head(3)
    for i, name in enumerate(dict_samples, 1):
        normalized = normalizer.normalize_for_matching(name)
        first_name, last_name = normalizer.extract_name_parts(normalized)
        print(f"   {i}. Oryginał: '{name}'")
        print(f"      Znormalizowane: '{normalized}'")
        print(f"      Imię: '{first_name}', Nazwisko: '{last_name}'")
    
    # Test samples from source list
    print("\n📝 Próbki z listy do mapowania (kom.csv):")
    source_samples = df_source['name'].dropna().head(3)
    for i, name in enumerate(source_samples, 1):
        normalized = normalizer.normalize_for_matching(name)
        first_name, last_name = normalizer.extract_name_parts(normalized)
        print(f"   {i}. Oryginał: '{name}'")
        print(f"      Znormalizowane: '{normalized}'")
        print(f"      Imię: '{first_name}', Nazwisko: '{last_name}'")

def find_potential_matches():
    """Find potential matches between the two files."""
    print("\n🔍 Szukanie potencjalnych dopasowań...")
    
    # Load files
    df_dict = pd.read_excel('files/komornicy.xlsx')
    df_source = pd.read_csv('files/kom.csv')
    
    # Normalize names from both files
    dict_names = df_dict['nazwa_komornika'].dropna().apply(normalizer.normalize_for_matching)
    source_names = df_source['name'].dropna().apply(normalizer.normalize_for_matching)
    
    print(f"   Znormalizowane nazwy ze słownika: {len(dict_names)}")
    print(f"   Znormalizowane nazwy z listy: {len(source_names)}")
    
    # Find exact matches
    exact_matches = set(dict_names) & set(source_names)
    print(f"   Dokładne dopasowania po normalizacji: {len(exact_matches)}")
    
    if exact_matches:
        print(f"   Przykłady dokładnych dopasowań:")
        for i, match in enumerate(list(exact_matches)[:5], 1):
            print(f"      {i}. '{match}'")
    
    # Find similar city names
    if 'miasto' in df_dict.columns and 'address_city' in df_source.columns:
        dict_cities = set(df_dict['miasto'].dropna().str.lower())
        source_cities = set(df_source['address_city'].dropna().str.lower())
        common_cities = dict_cities & source_cities
        print(f"   Wspólne miasta: {len(common_cities)}")
        
        if common_cities:
            print(f"   Przykłady wspólnych miast: {list(common_cities)[:10]}")

def create_import_script():
    """Create script to import both files into database."""
    print("\n📝 Tworzenie skryptu importu danych...")
    
    script_content = '''#!/usr/bin/env python3
"""
Import script for bailiff data from provided files.
Imports komornicy.xlsx as target dictionary and kom.csv as source names.
"""

import pandas as pd
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.models import db_manager, BailiffDict, RawNames
from matching.normalizer import normalizer
from config import config

def import_target_dictionary():
    """Import komornicy.xlsx as target bailiff dictionary."""
    print("📖 Importuję słownik docelowy (komornicy.xlsx)...")
    
    df = pd.read_excel('files/komornicy.xlsx')
    session = db_manager.get_session()
    
    imported = 0
    batch_size = 100
    
    try:
        for index, row in df.iterrows():
            if pd.notna(row.get('nazwa_komornika')):
                # Extract name components
                full_name = str(row['nazwa_komornika']).strip()
                normalized_data = normalizer.normalize_bailiff_record({
                    'nazwisko': full_name,
                    'imie': '',
                    'miasto': row.get('miasto', '')
                })
                
                # Create database record
                bailiff_record = BailiffDict(
                    original_nazwisko=full_name,
                    original_imie='',
                    original_miasto=str(row.get('miasto', '')).strip() if pd.notna(row.get('miasto')) else '',
                    original_sad=str(row.get('sad', '')).strip() if pd.notna(row.get('sad')) else '',
                    adres=str(row.get('adres', '')).strip() if pd.notna(row.get('adres')) else '',
                    kod_pocztowy=str(row.get('kod_pocztowy', '')).strip() if pd.notna(row.get('kod_pocztowy')) else '',
                    telefon=str(row.get('telefon', '')).strip() if pd.notna(row.get('telefon')) else '',
                    email=str(row.get('email', '')).strip() if pd.notna(row.get('email')) else '',
                    bank=str(row.get('bank', '')).strip() if pd.notna(row.get('bank')) else '',
                    numer_konta=str(row.get('numer_konta', '')).strip() if pd.notna(row.get('numer_konta')) else '',
                    normalized_lastname=normalized_data.get('normalized_lastname', ''),
                    normalized_firstname=normalized_data.get('normalized_firstname', ''),
                    normalized_fullname=normalized_data.get('normalized_fullname', ''),
                    normalized_city=normalized_data.get('normalized_city', '')
                )
                
                session.add(bailiff_record)
                imported += 1
                
                if imported % batch_size == 0:
                    session.commit()
                    print(f"   Zaimportowano: {imported}/{len(df)}")
        
        session.commit()
        print(f"✅ Zaimportowano słownik docelowy: {imported} rekordów")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Błąd podczas importu słownika: {e}")
        raise
    finally:
        session.close()

def import_source_names():
    """Import kom.csv as raw names to be matched."""
    print("📝 Importuję listę do mapowania (kom.csv)...")
    
    df = pd.read_csv('files/kom.csv')
    session = db_manager.get_session()
    
    imported = 0
    batch_size = 100
    
    try:
        for index, row in df.iterrows():
            if pd.notna(row.get('name')):
                # Normalize the raw text
                raw_text = str(row['name']).strip()
                normalized_data = normalizer.normalize_raw_text(raw_text)
                
                # Create database record
                raw_record = RawNames(
                    source_file='files/kom.csv',
                    source_sheet='default',
                    source_row=index + 2,  # +2 for header and 0-based index
                    source_column='name',
                    raw_text=raw_text,
                    normalized_text=normalized_data.get('normalized_text', ''),
                    extracted_lastname=normalized_data.get('extracted_lastname'),
                    extracted_firstname=normalized_data.get('extracted_firstname'),
                    processing_notes=normalized_data.get('processing_notes'),
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
                    print(f"   Zaimportowano: {imported}/{len(df)}")
        
        session.commit()
        print(f"✅ Zaimportowano listę do mapowania: {imported} rekordów")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Błąd podczas importu listy: {e}")
        raise
    finally:
        session.close()

def main():
    """Main import process."""
    print("🚀 Import danych z dostarczonych plików")
    print("=" * 50)
    
    try:
        # Initialize database
        print("🔧 Inicjalizacja bazy danych...")
        db_manager.create_tables()
        
        # Import target dictionary
        import_target_dictionary()
        
        # Import source names
        import_source_names()
        
        # Show summary
        session = db_manager.get_session()
        bailiff_count = session.query(BailiffDict).count()
        raw_count = session.query(RawNames).count()
        session.close()
        
        print(f"\\n📊 Podsumowanie importu:")
        print(f"   Słownik docelowy: {bailiff_count} komorników")
        print(f"   Lista do mapowania: {raw_count} nazw")
        print(f"\\n🎉 Import zakończony pomyślnie!")
        
    except Exception as e:
        print(f"\\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
'''
    
    with open('scripts/import_provided_files.py', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("✅ Utworzono skrypt: scripts/import_provided_files.py")

def update_database_models():
    """Update database models to include additional fields from CSV."""
    print("\n🔧 Aktualizacja modeli bazy danych...")
    
    # Read current models file
    models_file = Path('src/database/models.py')
    
    if not models_file.exists():
        print("❌ Plik models.py nie istnieje")
        return
    
    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if additional fields are already present
    if 'source_city' in content:
        print("ℹ️  Modele już zawierają dodatkowe pola")
        return
    
    # Add additional fields to RawNames model
    additional_fields = '''
    # Additional fields from kom.csv
    source_city = Column(String(200), nullable=True, comment="City from source file")
    source_email = Column(String(200), nullable=True, comment="Email from source file")
    source_phone = Column(String(50), nullable=True, comment="Phone from source file") 
    source_address = Column(String(500), nullable=True, comment="Address from source file")'''
    
    # Find the RawNames class and add fields before the last line
    import re
    
    # Find the RawNames class
    raw_names_pattern = r'(class RawNames\(Base\):.*?)(    # Indexes.*?(?=\n\n|class|\Z))'
    
    def add_fields(match):
        class_content = match.group(1)
        indexes_content = match.group(2)
        return class_content + additional_fields + '\n\n' + indexes_content
    
    updated_content = re.sub(raw_names_pattern, add_fields, content, flags=re.DOTALL)
    
    if updated_content != content:
        with open(models_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print("✅ Zaktualizowano modele bazy danych")
    else:
        print("⚠️  Nie udało się automatycznie zaktualizować modeli")

def main():
    """Main analysis process."""
    print("🔍 Analiza dostarczonych plików")
    print("=" * 50)
    
    try:
        # Analyze both files
        df_dict = analyze_target_dictionary()
        df_source = analyze_source_list()
        
        # Test normalization
        test_normalization_samples()
        
        # Find potential matches
        find_potential_matches()
        
        # Create import script
        create_import_script()
        
        # Update database models
        update_database_models()
        
        print("\n🎉 Analiza zakończona!")
        print("\nNastępne kroki:")
        print("1. Uruchom: python scripts/import_provided_files.py")
        print("2. Sprawdź czy import się powiódł")
        print("3. Uruchom aplikację Streamlit do testowania dopasowań")
        
    except Exception as e:
        print(f"\n❌ Błąd podczas analizy: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
