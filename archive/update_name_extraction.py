#!/usr/bin/env python3
"""
Skrypt do aktualizacji extracted_lastname i extracted_firstname 
dla istniejących rekordów w bazie danych
"""

import sqlite3
import sys

def extract_names_from_bailiff_text(name_text):
    """Extract first and last names from bailiff text"""
    lastname = ""
    firstname = ""
    
    # Look for actual person names in bailiff text
    if "Komornik" in name_text and "Sądowy" in name_text:
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
            'Marcin', 'Jakub', 'Dawid', 'Łukasz', 'Mateusz', 'Kamil', 'Rafał', 'Robert',
            'Zbigniew', 'Stanisław', 'Dariusz', 'Marek', 'Grzegorz', 'Jerzy', 'Tadeusz',
            'Iwona', 'Danuta', 'Halina', 'Teresa', 'Elżbieta', 'Zofia', 'Krystyna',
            'Jolanta', 'Bożena', 'Urszula', 'Dorota', 'Grażyna', 'Renata', 'Marianna'
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
    
    return firstname, lastname

def update_existing_records():
    """Update extracted names for all existing records"""
    conn = sqlite3.connect('bailiffs_matching.db')
    conn.row_factory = sqlite3.Row
    
    # Get all raw_names records
    cursor = conn.execute("SELECT id, raw_text FROM raw_names")
    records = cursor.fetchall()
    
    print(f"Znaleziono {len(records)} rekordów do aktualizacji...\n")
    
    updated_count = 0
    for record in records:
        firstname, lastname = extract_names_from_bailiff_text(record["raw_text"])
        
        # Update record
        conn.execute("""
            UPDATE raw_names 
            SET extracted_firstname = ?, extracted_lastname = ? 
            WHERE id = ?
        """, (firstname, lastname, record["id"]))
        
        updated_count += 1
        if updated_count % 100 == 0:
            print(f"Zaktualizowano {updated_count}/{len(records)} rekordów...")
    
    conn.commit()
    print(f"\n✅ Zaktualizowano wszystkie {updated_count} rekordów!")
    
    # Show some examples
    print("\n=== PRZYKŁADY ZAKTUALIZOWANYCH REKORDÓW ===")
    cursor = conn.execute("""
        SELECT raw_text, extracted_firstname, extracted_lastname 
        FROM raw_names 
        WHERE raw_text LIKE '%Komornik%' AND extracted_firstname != ''
        LIMIT 5
    """)
    
    examples = cursor.fetchall()
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['raw_text'][:60]}...")
        print(f"   Firstname: '{example['extracted_firstname']}'")
        print(f"   Lastname: '{example['extracted_lastname']}'")
    
    conn.close()

if __name__ == "__main__":
    update_existing_records()
