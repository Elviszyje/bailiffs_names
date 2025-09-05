#!/usr/bin/env python3
"""
Simple analysis script for provided files without database dependencies.
"""

import pandas as pd
import re

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

def analyze_target_dictionary():
    """Analyze komornicy.xlsx file structure and content."""
    print("🔍 Analizuję plik komornicy.xlsx (słownik docelowy)...")
    
    df = pd.read_excel('files/komornicy.xlsx')
    
    print(f"📊 Statystyki podstawowe:")
    print(f"   Liczba rekordów: {len(df)}")
    print(f"   Kolumny: {list(df.columns)}")
    
    # Analyze nazwa_komornika column
    if 'nazwa_komornika' in df.columns:
        print(f"\n📝 Analiza kolumny 'nazwa_komornika':")
        name_col = df['nazwa_komornika'].dropna()
        print(f"   Rekordów z nazwami: {len(name_col)}")
        print(f"   Unikalne nazwy: {name_col.nunique()}")
        
        # Sample names
        print(f"\n   Przykładowe nazwy:")
        for i, name in enumerate(name_col.head(5), 1):
            normalized = normalize_name_simple(name)
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
            normalized = normalize_name_simple(name)
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

def find_potential_matches():
    """Find potential matches between the two files."""
    print("\n🔍 Szukanie potencjalnych dopasowań...")
    
    # Load files
    df_dict = pd.read_excel('files/komornicy.xlsx')
    df_source = pd.read_csv('files/kom.csv')
    
    # Normalize names from both files
    dict_names = df_dict['nazwa_komornika'].dropna().apply(normalize_name_simple)
    source_names = df_source['name'].dropna().apply(normalize_name_simple)
    
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
    
    # Show potential fuzzy matches
    print(f"\n🔍 Analiza podobieństw...")
    
    # Sample some names for similarity checking
    sample_dict = dict_names.head(10).tolist()
    sample_source = source_names.head(10).tolist()
    
    print(f"   Porównanie przykładowych nazw:")
    for i, dict_name in enumerate(sample_dict[:3], 1):
        best_matches = []
        for source_name in sample_source:
            if dict_name and source_name:
                # Simple similarity check - common words
                dict_words = set(dict_name.split())
                source_words = set(source_name.split())
                if dict_words & source_words:  # Has common words
                    common = len(dict_words & source_words)
                    total = len(dict_words | source_words)
                    similarity = common / total if total > 0 else 0
                    if similarity > 0.3:  # Threshold for similarity
                        best_matches.append((source_name, similarity))
        
        if best_matches:
            best_matches.sort(key=lambda x: x[1], reverse=True)
            print(f"      {i}. '{dict_name}' -> '{best_matches[0][0]}' (sim: {best_matches[0][1]:.2f})")

def main():
    """Main analysis process."""
    print("🔍 Analiza dostarczonych plików")
    print("=" * 50)
    
    try:
        # Analyze both files
        df_dict = analyze_target_dictionary()
        df_source = analyze_source_list()
        
        # Find potential matches
        find_potential_matches()
        
        print("\n📊 Podsumowanie analizy:")
        print(f"   Słownik docelowy: {len(df_dict)} rekordów")
        print(f"   Lista do mapowania: {len(df_source)} rekordów")
        
        print("\n💡 Rekomendacje:")
        print("   1. Oba pliki zawierają szczegółowe nazwy komorników z tytułami")
        print("   2. Normalizacja powinna usuwać tytuły i nazwy sądów")
        print("   3. Dane geograficzne (miasta) mogą pomóc w dopasowywaniu")
        print("   4. Niektóre nazwy mogą wymagać dopasowania rozmytego (fuzzy matching)")
        
        print("\n🎉 Analiza zakończona!")
        print("\nNastępne kroki:")
        print("1. Skonfiguruj bazę danych")
        print("2. Zaimportuj dane z obu plików")
        print("3. Uruchom algorytm dopasowywania")
        
    except Exception as e:
        print(f"\n❌ Błąd podczas analizy: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
