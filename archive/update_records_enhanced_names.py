#!/usr/bin/env python3
"""
Aktualizacja istniejących rekordów z ulepszonym algorytmem rozpoznawania imion
"""

import sqlite3
import pandas as pd
from polish_names_recognition import extract_names_from_bailiff_text_enhanced
import sys

def update_all_records_with_enhanced_names():
    """Update all records with enhanced name extraction"""
    
    print("=== AKTUALIZACJA REKORDÓW Z ULEPSZONYM ALGORYTMEM ===")
    
    # Connect to database
    conn = sqlite3.connect('bailiffs_matching.db')
    cursor = conn.cursor()
    
    # Update raw_names table
    print("Aktualizacja tabeli raw_names...")
    cursor.execute("SELECT COUNT(*) FROM raw_names")
    total_raw = cursor.fetchone()[0]
    print(f"Znaleziono {total_raw} rekordów w raw_names")
    
    cursor.execute("SELECT id, raw_text FROM raw_names")
    raw_records = cursor.fetchall()
    
    updated_raw = 0
    for record_id, bailiff_text in raw_records:
        if bailiff_text:
            first_name, last_name = extract_names_from_bailiff_text_enhanced(bailiff_text)
            cursor.execute("""
                UPDATE raw_names 
                SET extracted_firstname = ?, extracted_lastname = ?
                WHERE id = ?
            """, (first_name, last_name, record_id))
            updated_raw += 1
            
            if updated_raw % 1000 == 0:
                print(f"  Zaktualizowano {updated_raw}/{total_raw} rekordów raw_names")
    
    print(f"✅ Zaktualizowano {updated_raw} rekordów w raw_names")
    
    # Update bailiffs_dict table
    print("\nAktualizacja tabeli bailiffs_dict...")
    cursor.execute("SELECT COUNT(*) FROM bailiffs_dict")
    total_bailiffs = cursor.fetchone()[0]
    print(f"Znaleziono {total_bailiffs} rekordów w bailiffs_dict")
    
    # For bailiffs_dict, we'll reconstruct full name from original_nazwisko and original_imie
    cursor.execute("SELECT id, original_nazwisko, original_imie FROM bailiffs_dict")
    bailiff_records = cursor.fetchall()
    
    updated_bailiffs = 0
    for record_id, nazwisko, imie in bailiff_records:
        # Reconstruct full name text for extraction
        full_text = f"{imie or ''} {nazwisko or ''}".strip()
        if full_text:
            first_name, last_name = extract_names_from_bailiff_text_enhanced(full_text)
            cursor.execute("""
                UPDATE bailiffs_dict 
                SET normalized_firstname = ?, normalized_lastname = ?
                WHERE id = ?
            """, (first_name, last_name, record_id))
            updated_bailiffs += 1
            
            if updated_bailiffs % 500 == 0:
                print(f"  Zaktualizowano {updated_bailiffs}/{total_bailiffs} rekordów bailiffs_dict")
    
    print(f"✅ Zaktualizowano {updated_bailiffs} rekordów w bailiffs_dict")
    
    # Commit changes
    conn.commit()
    print(f"\n💾 Zapisano zmiany do bazy danych")
    
    # Test specific problematic records
    print(f"\n=== TEST PROBLEMATYCZNYCH REKORDÓW ===")
    
    # Test record 9726
    cursor.execute("""
        SELECT id, raw_text, extracted_firstname, extracted_lastname 
        FROM raw_names 
        WHERE id = 9726
    """)
    record = cursor.fetchone()
    
    if record:
        print(f"Rekord 9726:")
        print(f"  Tekst komornika: {record[1]}")
        print(f"  Wyodrębnione imię: '{record[2]}'")
        print(f"  Wyodrębnione nazwisko: '{record[3]}'")
    
    # Test some other records with "Maciej"
    cursor.execute("""
        SELECT id, raw_text, extracted_firstname, extracted_lastname 
        FROM raw_names 
        WHERE raw_text LIKE '%Maciej%'
        LIMIT 5
    """)
    maciej_records = cursor.fetchall()
    
    print(f"\nRekordy z 'Maciej':")
    for record in maciej_records:
        print(f"  ID {record[0]}: '{record[1]}' -> imię: '{record[2]}', nazwisko: '{record[3]}'")
    
    # Statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN extracted_firstname != '' AND extracted_firstname IS NOT NULL THEN 1 END) as with_first_name,
            COUNT(CASE WHEN extracted_lastname != '' AND extracted_lastname IS NOT NULL THEN 1 END) as with_last_name
        FROM raw_names
    """)
    stats = cursor.fetchone()
    
    print(f"\n=== STATYSTYKI KOŃCOWE ===")
    print(f"Łączna liczba rekordów: {stats[0]}")
    print(f"Rekordy z wyodrębnionym imieniem: {stats[1]} ({100*stats[1]/stats[0]:.1f}%)")
    print(f"Rekordy z wyodrębnionym nazwiskiem: {stats[2]} ({100*stats[2]/stats[0]:.1f}%)")
    
    conn.close()
    print(f"\n✅ AKTUALIZACJA ZAKOŃCZONA POMYŚLNIE!")

if __name__ == "__main__":
    update_all_records_with_enhanced_names()
