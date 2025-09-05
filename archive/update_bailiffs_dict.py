#!/usr/bin/env python3
"""
Skrypt do aktualizacji normalized_firstname i normalized_lastname 
w słowniku komorników (bailiffs_dict)
"""

import sqlite3
import sys

def extract_names_from_bailiff_text(name_text):
    """Extract first and last names from bailiff text - same as in update_name_extraction.py"""
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

def normalize_name_simple(name):
    """Simple name normalization - same as in file_upload.py"""
    import re
    import unicodedata
    
    # Remove accents/diacritics
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    
    # Remove non-letter characters except spaces and hyphens
    name = re.sub(r'[^a-zA-Z\s\-]', ' ', name)
    
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name.strip())
    
    # Convert to lowercase
    name = name.lower()
    
    return name

def update_bailiffs_dict():
    """Update normalized names for all bailiff dictionary entries"""
    conn = sqlite3.connect('bailiffs_matching.db')
    conn.row_factory = sqlite3.Row
    
    # Get all bailiffs_dict records
    cursor = conn.execute("SELECT id, original_nazwisko FROM bailiffs_dict")
    records = cursor.fetchall()
    
    print(f"Znaleziono {len(records)} komorników do aktualizacji...\n")
    
    updated_count = 0
    for record in records:
        firstname, lastname = extract_names_from_bailiff_text(record["original_nazwisko"])
        
        # Normalize the extracted names
        normalized_firstname = normalize_name_simple(firstname) if firstname else ""
        normalized_lastname = normalize_name_simple(lastname) if lastname else ""
        
        # Update record
        conn.execute("""
            UPDATE bailiffs_dict 
            SET normalized_firstname = ?, normalized_lastname = ? 
            WHERE id = ?
        """, (normalized_firstname, normalized_lastname, record["id"]))
        
        updated_count += 1
        if updated_count % 100 == 0:
            print(f"Zaktualizowano {updated_count}/{len(records)} komorników...")
    
    conn.commit()
    print(f"\n✅ Zaktualizowano wszystkich {updated_count} komorników!")
    
    # Show some examples
    print("\n=== PRZYKŁADY ZAKTUALIZOWANYCH KOMORNIKÓW ===")
    cursor = conn.execute("""
        SELECT original_nazwisko, normalized_firstname, normalized_lastname 
        FROM bailiffs_dict 
        WHERE original_nazwisko LIKE '%Komornik%' AND normalized_firstname != ''
        LIMIT 5
    """)
    
    examples = cursor.fetchall()
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['original_nazwisko'][:60]}...")
        print(f"   Firstname: '{example['normalized_firstname']}'")
        print(f"   Lastname: '{example['normalized_lastname']}'")
    
    conn.close()

if __name__ == "__main__":
    update_bailiffs_dict()
