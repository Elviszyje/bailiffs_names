#!/usr/bin/env python3
"""
Aktualizacja algorytmu scoringu z nowym systemem rozpoznawania imion
"""

import sqlite3
import sys
sys.path.append('.')
from polish_names_recognition import extract_names_from_bailiff_text_enhanced
from rapidfuzz import fuzz

def update_match_suggestions_with_enhanced_scoring():
    """Update all match suggestions with enhanced scoring algorithm"""
    
    print("=== AKTUALIZACJA ALGORYTMU SCORINGU ===")
    
    # Connect to database
    conn = sqlite3.connect('bailiffs_matching.db')
    cursor = conn.cursor()
    
    # Get all match suggestions
    cursor.execute("""
        SELECT ms.id, ms.raw_id, ms.bailiff_id, 
               rn.raw_text, rn.extracted_firstname, rn.extracted_lastname, rn.source_city,
               bd.normalized_fullname, bd.normalized_firstname, bd.normalized_lastname, bd.original_miasto
        FROM match_suggestions ms
        JOIN raw_names rn ON ms.raw_id = rn.id
        JOIN bailiffs_dict bd ON ms.bailiff_id = bd.id
    """)
    
    suggestions = cursor.fetchall()
    print(f"Znaleziono {len(suggestions)} sugestii dopasowań do zaktualizowania")
    
    updated_count = 0
    
    for suggestion in suggestions:
        (ms_id, raw_id, bailiff_id, raw_text, raw_first, raw_last, raw_city,
         bailiff_fullname, bailiff_first, bailiff_last, bailiff_city) = suggestion
        
        # Calculate fullname score (using normalized fullname)
        if raw_text and bailiff_fullname:
            fullname_score = fuzz.ratio(str(raw_text).lower(), str(bailiff_fullname).lower())
        else:
            fullname_score = 0.0
        
        # Calculate lastname score using extracted names
        if raw_last and bailiff_last:
            lastname_score = fuzz.ratio(str(raw_last).lower(), str(bailiff_last).lower())
        else:
            lastname_score = 0.0
        
        # Calculate firstname score using extracted names
        if raw_first and bailiff_first:
            firstname_score = fuzz.ratio(str(raw_first).lower(), str(bailiff_first).lower())
        else:
            firstname_score = 0.0
        
        # Calculate city score
        if raw_city and bailiff_city:
            city_score = fuzz.ratio(str(raw_city).lower(), str(bailiff_city).lower())
        else:
            city_score = 0.0
        
        # Calculate combined score with proper weights
        # If we have extracted names, use them with higher weight
        if raw_first and raw_last and bailiff_first and bailiff_last:
            # Use individual name scores when available
            combined_score = (
                fullname_score * 0.4 +    # 40% for full name match
                lastname_score * 0.35 +   # 35% for lastname match
                firstname_score * 0.25    # 25% for firstname match
            )
        else:
            # Fall back to full name scoring
            combined_score = fullname_score
        
        # City bonus (add up to 10 points for good city match)
        if city_score > 70:
            combined_score += min(10, city_score / 10)
        
        # Ensure combined score doesn't exceed 100
        combined_score = min(100.0, combined_score)
        
        # Determine confidence level
        if combined_score >= 90:
            confidence = 'high'
        elif combined_score >= 70:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        # Update the suggestion
        cursor.execute("""
            UPDATE match_suggestions 
            SET fullname_score = ?, lastname_score = ?, firstname_score = ?, 
                city_score = ?, combined_score = ?, confidence_level = ?
            WHERE id = ?
        """, (fullname_score, lastname_score, firstname_score, city_score, combined_score, confidence, ms_id))
        
        updated_count += 1
        
        if updated_count % 1000 == 0:
            print(f"  Zaktualizowano {updated_count}/{len(suggestions)} sugestii")
    
    # Commit changes
    conn.commit()
    print(f"✅ Zaktualizowano {updated_count} sugestii dopasowań")
    
    # Test specific problematic record
    print(f"\n=== TEST REKORDU 9726 ===")
    cursor.execute("""
        SELECT ms.fullname_score, ms.lastname_score, ms.firstname_score, 
               ms.city_score, ms.combined_score, ms.confidence_level,
               rn.raw_text, rn.extracted_firstname, rn.extracted_lastname,
               bd.normalized_fullname, bd.normalized_firstname, bd.normalized_lastname
        FROM match_suggestions ms
        JOIN raw_names rn ON ms.raw_id = rn.id
        JOIN bailiffs_dict bd ON ms.bailiff_id = bd.id
        WHERE rn.id = 9726
        ORDER BY ms.combined_score DESC
        LIMIT 1
    """)
    
    record = cursor.fetchone()
    if record:
        print(f"Najlepsze dopasowanie dla rekordu 9726:")
        print(f"  Raw text: {record[6]}")
        print(f"  Extracted: '{record[7]}' '{record[8]}'")
        print(f"  Bailiff: '{record[10]}' '{record[11]}' (full: {record[9]})")
        print(f"  Scores: fullname={record[0]:.1f}%, lastname={record[1]:.1f}%, firstname={record[2]:.1f}%, city={record[3]:.1f}%")
        print(f"  Combined score: {record[4]:.1f}% ({record[5]})")
    
    # Statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN combined_score >= 90 THEN 1 END) as high_confidence,
            COUNT(CASE WHEN combined_score >= 70 AND combined_score < 90 THEN 1 END) as medium_confidence,
            COUNT(CASE WHEN combined_score < 70 THEN 1 END) as low_confidence,
            AVG(combined_score) as avg_score
        FROM match_suggestions
    """)
    
    stats = cursor.fetchone()
    print(f"\n=== STATYSTYKI KOŃCOWE ===")
    print(f"Łączna liczba sugestii: {stats[0]}")
    print(f"Wysokie zaufanie (≥90%): {stats[1]} ({100*stats[1]/stats[0]:.1f}%)")
    print(f"Średnie zaufanie (70-89%): {stats[2]} ({100*stats[2]/stats[0]:.1f}%)")
    print(f"Niskie zaufanie (<70%): {stats[3]} ({100*stats[3]/stats[0]:.1f}%)")
    print(f"Średni wynik: {stats[4]:.1f}%")
    
    conn.close()
    print(f"\n✅ AKTUALIZACJA ALGORYTMU SCORINGU ZAKOŃCZONA!")

if __name__ == "__main__":
    update_match_suggestions_with_enhanced_scoring()
