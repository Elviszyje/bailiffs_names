#!/usr/bin/env python3
"""
Skrypt do debugowania problemu z obliczaniem wyników
"""

import sqlite3

def debug_scoring():
    conn = sqlite3.connect('bailiffs_matching.db')
    conn.row_factory = sqlite3.Row  # Enables column access by name
    
    # Find examples with fullname_score=100, city_score=100 but low combined_score
    query = """
    SELECT 
        ms.fullname_score, ms.lastname_score, ms.firstname_score, ms.city_score, ms.combined_score,
        rn.raw_text, rn.extracted_lastname, rn.extracted_firstname,
        bd.original_nazwisko, bd.normalized_lastname, bd.normalized_firstname
    FROM match_suggestions ms
    JOIN raw_names rn ON ms.raw_id = rn.id
    JOIN bailiffs_dict bd ON ms.bailiff_id = bd.id
    WHERE ms.fullname_score = 100.0 
      AND ms.city_score = 100.0 
      AND ms.combined_score < 90.0
    LIMIT 3
    """
    
    cursor = conn.execute(query)
    suggestions = cursor.fetchall()
    
    print(f'Znaleziono {len(suggestions)} przykładów z pełnym dopasowaniem nazwy i miasta, ale niskim wynikiem ogólnym:\n')

    for i, row in enumerate(suggestions, 1):
        print(f'=== PRZYKŁAD {i} ===')
        print(f'Raw name: {row["raw_text"]}')
        print(f'Bailiff: {row["original_nazwisko"]}')
        print(f'Wyniki:')
        print(f'  - fullname_score: {row["fullname_score"]:.1f}%')
        print(f'  - lastname_score: {row["lastname_score"]:.1f}%')
        print(f'  - firstname_score: {row["firstname_score"]:.1f}%')
        print(f'  - city_score: {row["city_score"]:.1f}%')
        print(f'  - combined_score: {row["combined_score"]:.1f}%')
        print()
        
        # Obliczmy ręcznie
        manual_score = (row["fullname_score"] * 0.6 + 
                       row["lastname_score"] * 0.2 + 
                       row["firstname_score"] * 0.1)
        
        # City bonus
        city_bonus = min(10, row["city_score"] / 10) if row["city_score"] > 80 else 0
        manual_total = manual_score + city_bonus
        
        print(f'Ręczne obliczenie:')
        print(f'  - Base score: {manual_score:.1f}% ({row["fullname_score"]:.1f}*0.6 + {row["lastname_score"]:.1f}*0.2 + {row["firstname_score"]:.1f}*0.1)')
        print(f'  - City bonus: {city_bonus:.1f}')
        print(f'  - Total manual: {manual_total:.1f}%')
        print(f'  - Recorded: {row["combined_score"]:.1f}%')
        print(f'  - Różnica: {abs(manual_total - row["combined_score"]):.1f}%')
        print()
        
        print(f'Dane szczegółowe:')
        print(f'  - raw extracted_lastname: "{row["extracted_lastname"]}"')
        print(f'  - raw extracted_firstname: "{row["extracted_firstname"]}"')
        print(f'  - bailiff normalized_lastname: "{row["normalized_lastname"]}"')
        print(f'  - bailiff normalized_firstname: "{row["normalized_firstname"]}"')
        print('=' * 50)
        print()

    conn.close()

if __name__ == "__main__":
    debug_scoring()

if __name__ == "__main__":
    debug_scoring()
