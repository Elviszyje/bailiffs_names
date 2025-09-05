#!/usr/bin/env python3
"""
Test nowej funkcji ekstrakcji nazwisk
"""

def extract_names_from_bailiff_text(name_text):
    """Extract first and last names from bailiff text"""
    lastname = ""
    firstname = ""
    
    # Look for actual person names in bailiff text
    if "Komornik" in name_text and "Sądowy" in name_text:
        # Extract names using improved pattern matching
        import re
        
        # Pattern to find Polish names (capitalized words that are likely names)
        # Look for sequences of 2-4 capitalized words that could be names
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
    
    return firstname, lastname

# Test cases
test_cases = [
    "Komornik Sądowy przy Sądzie Rejonowym w Grójcu Ada Czapla-Lisowska Kancelaria Komornicza nr XII w Warce",
    "Komornik Sądowy przy Sądzie Rejonowym dla Łodzi-Widzewa w Łodzi Dominika Polańska-Pasturczak",
    "Komornik Sądowy przy Sądzie Rejonowym dla Krakowa-Śródmieścia w Krakowie Kinga Czech Kancelaria Komornicza nr XI w Krakowie",
    "Jan Kowalski",
    "Anna Maria Nowak-Wiśniewska"
]

print("=== TEST EKSTRAKCJI NAZWISK ===\n")

for i, text in enumerate(test_cases, 1):
    firstname, lastname = extract_names_from_bailiff_text(text)
    print(f"TEST {i}:")
    print(f"  Input: {text}")
    print(f"  Firstname: '{firstname}'")
    print(f"  Lastname: '{lastname}'")
    print()
