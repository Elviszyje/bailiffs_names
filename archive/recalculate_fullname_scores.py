#!/usr/bin/env python3
"""
Przeprzeliczenie wszystkich fullname_score z aktualnymi znormalizowanymi tekstami
"""

import sqlite3
import sys
sys.path.append('.')
from rapidfuzz import fuzz
from fix_problematic_records import enhanced_city_score

def recalculate_all_fullname_scores():
    """Recalculate all fullname_score values using current normalized texts"""
    
    print("=== PRZEPRZELICZENIE WSZYSTKICH FULLNAME_SCORE ===")
    
    # Connect to database
    conn = sqlite3.connect('bailiffs_matching.db')
    cursor = conn.cursor()
    
    # Get all match suggestions with texts
    cursor.execute("""
        SELECT ms.id, ms.raw_id, ms.bailiff_id,
               ms.fullname_score, ms.lastname_score, ms.firstname_score, ms.city_score,
               rn.normalized_text, rn.source_city,
               bd.normalized_fullname, bd.original_miasto, bd.original_sad
        FROM match_suggestions ms
        JOIN raw_names rn ON ms.raw_id = rn.id
        JOIN bailiffs_dict bd ON ms.bailiff_id = bd.id
    """)
    
    suggestions = cursor.fetchall()
    print(f"Znaleziono {len(suggestions)} sugestii do przeprzeliczenia")
    
    updated_count = 0
    perfect_matches = 0
    
    for i, suggestion in enumerate(suggestions):
        (ms_id, raw_id, bailiff_id, old_fullname_score, lastname_score, firstname_score, 
         old_city_score, raw_normalized, raw_city, bailiff_normalized, bailiff_city, bailiff_court) = suggestion
        
        # Calculate new fullname score
        if raw_normalized and bailiff_normalized:
            new_fullname_score = fuzz.ratio(str(raw_normalized), str(bailiff_normalized))
        else:
            new_fullname_score = 0.0
        
        # Recalculate city score with enhanced algorithm
        new_city_score = enhanced_city_score(raw_city, bailiff_city, bailiff_court)
        
        # Recalculate combined score
        if lastname_score == 100.0 and firstname_score == 100.0:
            # Enhanced weights for perfect name matches
            new_combined_score = (
                new_fullname_score * 0.3 +    # 30% for full name
                lastname_score * 0.4 +        # 40% for lastname
                firstname_score * 0.3         # 30% for firstname
            )
        else:
            # Standard weights
            new_combined_score = (
                new_fullname_score * 0.4 +    # 40% for full name
                lastname_score * 0.35 +       # 35% for lastname
                firstname_score * 0.25        # 25% for firstname
            )
        
        # City bonus
        if new_city_score > 70:
            city_bonus = min(10, new_city_score / 10)
            new_combined_score += city_bonus
        
        # Ensure combined score doesn't exceed 100
        new_combined_score = min(100.0, new_combined_score)
        
        # Determine confidence level
        if new_combined_score >= 90:
            confidence = 'high'
        elif new_combined_score >= 70:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        # Update the suggestion
        cursor.execute("""
            UPDATE match_suggestions 
            SET fullname_score = ?, city_score = ?, combined_score = ?, confidence_level = ?
            WHERE id = ?
        """, (new_fullname_score, new_city_score, new_combined_score, confidence, ms_id))
        
        updated_count += 1
        
        # Track perfect matches
        if new_fullname_score == 100.0:
            perfect_matches += 1
        
        # Progress reporting
        if updated_count % 5000 == 0:
            print(f"  Przeprzeliczono {updated_count}/{len(suggestions)} sugestii")
            
        # Show significant improvements
        if new_combined_score > 90 and (new_combined_score - (old_fullname_score * 0.4 + lastname_score * 0.35 + firstname_score * 0.25)) > 10:
            print(f"    Znacząca poprawa - Rekord {raw_id}: "
                  f"fullname {old_fullname_score:.1f}%→{new_fullname_score:.1f}%, "
                  f"combined: →{new_combined_score:.1f}%")
    
    # Commit changes
    conn.commit()
    print(f"✅ Przeprzeliczono {updated_count} sugestii")
    print(f"   Znaleziono {perfect_matches} idealnych dopasowań pełnej nazwy (100%)")
    
    # Test specific records
    print(f"\n=== TEST KLUCZOWYCH REKORDÓW ===")
    
    test_records = [9726, 9859]
    for record_id in test_records:
        cursor.execute("""
            SELECT ms.fullname_score, ms.lastname_score, ms.firstname_score, 
                   ms.city_score, ms.combined_score, ms.confidence_level,
                   rn.raw_text, rn.extracted_firstname, rn.extracted_lastname, rn.source_city,
                   bd.normalized_fullname, bd.normalized_firstname, bd.normalized_lastname,
                   bd.original_miasto
            FROM match_suggestions ms
            JOIN raw_names rn ON ms.raw_id = rn.id
            JOIN bailiffs_dict bd ON ms.bailiff_id = bd.id
            WHERE rn.id = ?
            ORDER BY ms.combined_score DESC
            LIMIT 1
        """, (record_id,))
        
        record = cursor.fetchone()
        if record:
            print(f"\nRekord {record_id}:")
            print(f"  Raw: '{record[7]} {record[8]}' z {record[9]}")
            print(f"  Bailiff: '{record[11]} {record[12]}' z {record[13]}")
            print(f"  Scores: fullname={record[0]:.1f}%, lastname={record[1]:.1f}%, "
                  f"firstname={record[2]:.1f}%, city={record[3]:.1f}%")
            print(f"  Combined: {record[4]:.1f}% ({record[5]})")
    
    # Final statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN combined_score >= 90 THEN 1 END) as high_confidence,
            COUNT(CASE WHEN combined_score >= 70 AND combined_score < 90 THEN 1 END) as medium_confidence,
            COUNT(CASE WHEN combined_score < 70 THEN 1 END) as low_confidence,
            COUNT(CASE WHEN fullname_score = 100.0 THEN 1 END) as perfect_fullname,
            AVG(combined_score) as avg_score,
            AVG(fullname_score) as avg_fullname_score
        FROM match_suggestions
    """)
    
    stats = cursor.fetchone()
    print(f"\n=== STATYSTYKI KOŃCOWE ===")
    print(f"Łączna liczba sugestii: {stats[0]}")
    print(f"Wysokie zaufanie (≥90%): {stats[1]} ({100*stats[1]/stats[0]:.1f}%)")
    print(f"Średnie zaufanie (70-89%): {stats[2]} ({100*stats[2]/stats[0]:.1f}%)")
    print(f"Niskie zaufanie (<70%): {stats[3]} ({100*stats[3]/stats[0]:.1f}%)")
    print(f"Idealne dopasowania pełnej nazwy: {stats[4]} ({100*stats[4]/stats[0]:.1f}%)")
    print(f"Średni wynik łączny: {stats[5]:.1f}%")
    print(f"Średni wynik pełnej nazwy: {stats[6]:.1f}%")
    
    conn.close()
    print(f"\n🎉 PRZEPRZELICZENIE ZAKOŃCZONE POMYŚLNIE!")

if __name__ == "__main__":
    recalculate_all_fullname_scores()
