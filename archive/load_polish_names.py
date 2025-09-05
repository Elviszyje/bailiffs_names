#!/usr/bin/env python3
"""
Skrypt do wczytania polskich imion i nazwisk z plików XLSX
i aktualizacji algorytmu ekstrakcji
"""

import pandas as pd
import os

def load_polish_names():
    """Load Polish names from XLSX files"""
    files_dir = "/Users/bartoszkolek/Desktop/cloud/Projekty/bailiffs_names/files"
    
    # Load male first names
    male_names_file = os.path.join(files_dir, "10_-_Wykaz_imion_męskich_osób_żyjących_wg_pola_imię_drugie_występujących_w_rejestrze_PESEL_bez_zgonów.xlsx")
    
    # Load female first names  
    female_names_file = os.path.join(files_dir, "10_-_Wykaz_imion_żeńskich_osób_żyjących_wg_pola_imię_drugie_występujących_w_rejestrze_PESEL_bez_zgonów.xlsx")
    
    # Load male surnames
    male_surnames_file = os.path.join(files_dir, "nazwiska_męskie-z_uwzględnieniem_osób_zmarłych.xlsx")
    
    # Load female surnames
    female_surnames_file = os.path.join(files_dir, "nazwiska_żeńskie-z_uwzględnieniem_osób_zmarłych.xlsx")
    
    all_first_names = set()
    all_surnames = set()
    
    print("Wczytywanie imion męskich...")
    try:
        df_male_names = pd.read_excel(male_names_file)
        print(f"Kolumny w pliku imion męskich: {list(df_male_names.columns)}")
        print(f"Pierwsze 5 wierszy:")
        print(df_male_names.head())
        
        # Znajdź kolumnę z imionami (prawdopodobnie pierwsza kolumna z tekstem)
        for col in df_male_names.columns:
            if df_male_names[col].dtype == 'object':  # string column
                names = df_male_names[col].dropna().astype(str)
                names = [name.strip().title() for name in names if name.strip()]
                all_first_names.update(names[:100])  # Take first 100 to check
                print(f"Przykładowe imiona męskie z kolumny '{col}': {list(names[:10])}")
                break
    except Exception as e:
        print(f"Błąd podczas wczytywania imion męskich: {e}")
    
    print("\nWczytywanie imion żeńskich...")
    try:
        df_female_names = pd.read_excel(female_names_file)
        print(f"Kolumny w pliku imion żeńskich: {list(df_female_names.columns)}")
        print(f"Pierwsze 5 wierszy:")
        print(df_female_names.head())
        
        # Znajdź kolumnę z imionami
        for col in df_female_names.columns:
            if df_female_names[col].dtype == 'object':  # string column
                names = df_female_names[col].dropna().astype(str)
                names = [name.strip().title() for name in names if name.strip()]
                all_first_names.update(names[:100])  # Take first 100 to check
                print(f"Przykładowe imiona żeńskie z kolumny '{col}': {list(names[:10])}")
                break
    except Exception as e:
        print(f"Błąd podczas wczytywania imion żeńskich: {e}")
    
    print("\nWczytywanie nazwisk męskich...")
    try:
        df_male_surnames = pd.read_excel(male_surnames_file)
        print(f"Kolumny w pliku nazwisk męskich: {list(df_male_surnames.columns)}")
        print(f"Pierwsze 5 wierszy:")
        print(df_male_surnames.head())
        
        # Znajdź kolumnę z nazwiskami
        for col in df_male_surnames.columns:
            if df_male_surnames[col].dtype == 'object':  # string column
                surnames = df_male_surnames[col].dropna().astype(str)
                surnames = [surname.strip().title() for surname in surnames if surname.strip()]
                all_surnames.update(surnames[:100])  # Take first 100 to check
                print(f"Przykładowe nazwiska męskie z kolumny '{col}': {list(surnames[:10])}")
                break
    except Exception as e:
        print(f"Błąd podczas wczytywania nazwisk męskich: {e}")
    
    print("\nWczytywanie nazwisk żeńskich...")
    try:
        df_female_surnames = pd.read_excel(female_surnames_file)
        print(f"Kolumny w pliku nazwisk żeńskich: {list(df_female_surnames.columns)}")
        print(f"Pierwsze 5 wierszy:")
        print(df_female_surnames.head())
        
        # Znajdź kolumnę z nazwiskami
        for col in df_female_surnames.columns:
            if df_female_surnames[col].dtype == 'object':  # string column
                surnames = df_female_surnames[col].dropna().astype(str)
                surnames = [surname.strip().title() for surname in surnames if surname.strip()]
                all_surnames.update(surnames[:100])  # Take first 100 to check
                print(f"Przykładowe nazwiska żeńskie z kolumny '{col}': {list(surnames[:10])}")
                break
    except Exception as e:
        print(f"Błąd podczas wczytywania nazwisk żeńskich: {e}")
    
    print(f"\n=== PODSUMOWANIE ===")
    print(f"Wczytano imion: {len(all_first_names)}")
    print(f"Wczytano nazwisk: {len(all_surnames)}")
    
    # Sprawdź czy mamy problematyczne imiona
    test_names = ['Maciej', 'Pucko', 'Ryszard', 'Michałek', 'Ada', 'Czapla-Lisowska']
    print(f"\nTest problematycznych imion/nazwisk:")
    for name in test_names:
        in_first = name in all_first_names
        in_surnames = name in all_surnames
        print(f"  {name}: w imionach={in_first}, w nazwiskach={in_surnames}")
    
    return all_first_names, all_surnames

if __name__ == "__main__":
    first_names, surnames = load_polish_names()
